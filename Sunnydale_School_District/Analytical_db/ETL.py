from sqlalchemy import create_engine, MetaData, Table, select, text, func, inspect
from sqlalchemy.engine import URL
from sqlalchemy.sql import exists
import pandas as pd
import datetime
from typing import Optional, Dict, Union
from configparser import ConfigParser

def load_config(path: str, section: str = 'database') -> dict:
    parser = ConfigParser()
    parser.read(path)
    if not parser.has_section(section):
        raise ValueError(f"Section '{section}' not found in config file")
    config = parser[section]
    return {
        'user': config['user'],
        'password': config['password'],
        'host': config['host'],
        'database': config['database']
    }

db_config_path = '/Users/louisas/Documents/Data 201 - Database/Homework/Assignment11/db_config.ini'
wh_config_path = '/Users/louisas/Documents/Data 201 - Database/Homework/Assignment11/wh_config.ini'

db_config = load_config(db_config_path)
wh_config = load_config(wh_config_path)


class ETLProcessor:
    def __init__(self, db_config: Dict, wh_config: Dict):
        """Initialize database connections"""
        self.db_engine = self._create_engine(db_config)
        self.wh_engine = self._create_engine(wh_config)
        self.metadata = MetaData()
        
    def _create_engine(self, config: Dict):
        """Create SQLAlchemy engine"""
        url = URL.create(
            drivername="mysql+pymysql",
            username=config['user'],
            password=config['password'],
            host=config['host'],
            database=config['database'],
            query={'charset': 'utf8mb4'}
        )
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)

    # ========== ETL Control Methods ==========
    def initialize_etl(self) -> bool:
        """Verify control table exists in warehouse"""
        with self.wh_engine.connect() as conn:
            inspector = inspect(self.wh_engine)
            if not inspector.has_table('etl_control'):
                return False
                
            etl_control = Table(
                'etl_control', 
                self.metadata, 
                autoload_with=self.wh_engine
            )
            result = conn.execute(
                select(exists().where(etl_control.c.process_name == 'student_warehouse'))
            )
            return result.scalar()

    def get_last_etl_run(self) -> datetime.datetime:
        """Get timestamp of last successful run"""
        with self.wh_engine.connect() as conn:
            inspector = inspect(self.wh_engine)
            if not inspector.has_table('etl_control'):
                return datetime.datetime(1970, 1, 1)
                
            query = text("""
                SELECT last_run FROM etl_control 
                WHERE process_name = 'student_warehouse'
                AND status = 'success'
                ORDER BY last_run DESC 
                LIMIT 1
            """)
            result = conn.execute(query).fetchone()
            return result[0] if result else datetime.datetime(1970, 1, 1)

    def update_etl_status(
        self, 
        status: str, 
        rows_processed: int = 0, 
        error_msg: Optional[str] = None, 
        duration: float = 0
    ):
        """Update control table with current run details"""
        with self.wh_engine.begin() as conn:
            inspector = inspect(self.wh_engine)
            if not inspector.has_table('etl_control'):
                conn.execute(text("""
                    CREATE TABLE etl_control (
                        process_name VARCHAR(100) NOT NULL,
                        last_run TIMESTAMP NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        rows_processed INT DEFAULT 0,
                        error_message TEXT,
                        duration_seconds FLOAT,
                        PRIMARY KEY (process_name, last_run)
                    )
                """))
            
            conn.execute(text("""
                INSERT INTO etl_control 
                    (process_name, last_run, status, rows_processed, error_message, duration_seconds)
                VALUES 
                    (:process, NOW(), :status, :rows, :error, :duration)
                ON DUPLICATE KEY UPDATE 
                    last_run = NOW(),
                    status = VALUES(status),
                    rows_processed = VALUES(rows_processed),
                    error_message = VALUES(error_message),
                    duration_seconds = VALUES(duration_seconds)
            """).bindparams(
                process='student_warehouse',
                status=status,
                rows=rows_processed,
                error=error_msg,
                duration=duration
            ))

    # ========== Dimension Loading ==========
    def load_dimension_table(
        self, 
        source_table: str, 
        target_table: str, 
        columns: list,
        where_clause: Optional[str] = None,
        params: Optional[dict] = None
    ):
        """Generic dimension table loader"""
        columns_str = ', '.join(columns)
        query = f"SELECT {columns_str} FROM {source_table}"

        if where_clause:
            query += f" WHERE {where_clause}"

        #query += " LIMIT 1000"  # dev only

        # Create text object and bind parameters
        sql_text = text(query)
        if params:
            sql_text = sql_text.bindparams(**params)

        df = pd.read_sql(sql_text, self.db_engine)

        if target_table == 'school_dim' and 'state' in df.columns:
            df['state'] = df['state'].str[:2]

        with self.wh_engine.begin() as conn:
            inspector = inspect(self.wh_engine)
            pk_column = inspector.get_pk_constraint(target_table)['constrained_columns'][0]
            
            if not df.empty and pk_column in df.columns:
                ids = tuple(df[pk_column].tolist())
                if ids:
                    conn.execute(
                        text(f"DELETE FROM {target_table} WHERE {pk_column} IN :ids").bindparams(ids=ids)
                    )

            df.to_sql(
                target_table,
                conn,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=1000
            )

        return len(df)

    # ========== Fact Table Loading ==========
    def load_fact_table(self, query: Union[str, text], target_table: str, params: Optional[dict] = None):
        """Generic fact table loader that handles both raw SQL and text() clauses"""
        if isinstance(query, str):
            sql_text = text(query)
            if params:
                sql_text = sql_text.bindparams(**params)
        else:
            sql_text = query  # Assume it's already a text() object

        df = pd.read_sql(sql_text, self.db_engine)
        
        with self.wh_engine.begin() as conn:
            df.to_sql(
                target_table,
                conn,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=1000
            )
        
        return len(df)

    # ========== Main ETL Process ==========
    # Add this method to handle truncation
    def truncate_tables(self, conn):
        """Truncate all necessary tables in the star schema to avoid foreign key issues."""
        # List of all tables you want to truncate (fact tables first, then dimension tables)
        tables_to_truncate = [
            'student_attendance_fact',  # Fact tables
            'student_performance_fact',  # More fact tables if needed
            'student_dim',  # Dimension tables
            'teacher_dim',  # Dimension tables
            'course_dim',  # Dimension tables
            'school_dim',  # Dimension tables
            'date_dim'  # Dimension tables
        ]

        for table in tables_to_truncate:
            query = text(f"TRUNCATE TABLE {table}")
            conn.execute(query)


    # Modify your run_full_etl method to use truncate_tables
    def run_full_etl(self):
        """Execute complete ETL pipeline"""
        start_time = datetime.datetime.now()
        stats = {}
        
        try:
            # Initialize - ensure control table exists
            if not self.initialize_etl():
                print("ETL control table not found, creating...")
                self.update_etl_status(status='initialized')

            # Disable FK checks for initial load
            with self.wh_engine.begin() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                print("Foreign key checks temporarily disabled for initial load")

                # Truncate tables before starting the load
                print("Truncating tables...")
                self.truncate_tables(conn)
                print("Tables truncated successfully.")

            # Proceed with normal ETL process
            last_run = self.get_last_etl_run()
            print(f"Starting ETL from last run: {last_run}")
            
            # Load all dimensions first
            stats['teachers'] = self.load_dimension_table(
                source_table='teacher',
                target_table='teacher_dim',
                columns=['teacher_id', 'first_name', 'last_name', 'employment_type']
            )
            
            stats['students'] = self.load_dimension_table(
                source_table='student',
                target_table='student_dim',
                columns=['student_id', 'first_name', 'last_name', 'date_of_birth', 'grade_level']
            )
            
            stats['courses'] = self.load_dimension_table(
                source_table='course',
                target_table='course_dim',
                columns=['course_id', 'name']
            )
            
            stats['schools'] = self.load_dimension_table(
                source_table='school',
                target_table='school_dim',
                columns=['school_id', 'name', 'school_type', 'address', 'city', 'state', 'zip']
            )
            
            # Date dimension and performance fact loading
            date_query = text("""
                SELECT DISTINCT
                    TO_DAYS(date) AS date_id,
                    DAY(date) AS day,
                    MONTH(date) AS month,
                    CASE WHEN MONTH(date) BETWEEN 8 AND 12 THEN 1 ELSE 2 END AS semester,
                    YEAR(date) AS year,
                    DAYNAME(date) AS weekday
                FROM attendance
                WHERE date > :last_run
            """).bindparams(last_run=last_run)

            # First delete any existing dates we're about to insert
            with self.wh_engine.begin() as conn:
                dates_to_process = pd.read_sql(date_query, self.db_engine)
                if not dates_to_process.empty:
                    conn.execute(
                        text("DELETE FROM date_dim WHERE date_id IN :ids"),
                        {'ids': tuple(dates_to_process['date_id'].tolist())}
                    )

            stats['dates'] = self.load_fact_table(
                query=date_query,
                target_table='date_dim'
            )
            
            # Performance fact
            #add LIMIT 1000 for dev
            stats['performance'] = self.load_fact_table(
                query="""
                SELECT 
                    gd.grade_type, 
                    gd.score, 
                    gd.weight, 
                    (gd.score * gd.weight) AS weighted_score,
                    gd.student_id,
                    gd.course_id,
                    t.teacher_id,
                    s.school_id
                FROM grade_details gd
                JOIN student s ON gd.student_id = s.student_id
                JOIN takes tk ON gd.student_id = tk.student_id AND gd.course_id = tk.course_id
                JOIN teaches t ON tk.course_id = t.course_id AND tk.day = t.day AND tk.start_time = t.start_time
                """,
                target_table='student_performance_fact'
            )
            
            # Attendance fact with proper parameter binding
            #add LIMIT 1000 for dev
            attendance_query = text("""
                SELECT 
                    a.status, 
                    COALESCE(a.notes, '') AS notes,
                    a.student_id,
                    tk.course_id,
                    t.teacher_id,
                    s.school_id,
                    TO_DAYS(a.date) AS date_id
                FROM attendance a
                JOIN student s ON a.student_id = s.student_id
                JOIN takes tk ON a.student_id = tk.student_id
                JOIN teaches t ON tk.course_id = t.course_id AND tk.day = t.day AND tk.start_time = t.start_time
                WHERE a.date > :last_run
            """).bindparams(last_run=last_run)
            stats['attendance'] = self.load_fact_table(
                query=attendance_query,
                target_table='student_attendance_fact'
            )
            
            # Update status
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.update_etl_status(
                status='success',
                rows_processed=sum(stats.values()),
                duration=duration
            )
            
            print(f"ETL completed successfully. Processed {sum(stats.values())} records in {duration:.2f} seconds")
            print("Breakdown:", stats)
            
        except Exception as e:
            # Error handling
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.update_etl_status(
                status='failed',
                error_msg=str(e),
                duration=duration
            )
            print(f"ETL failed: {str(e)}")
            raise

        finally:
            # Always re-enable FK checks
            with self.wh_engine.begin() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                print("Foreign key checks re-enabled")
                
                # Basic integrity verification
                result = conn.execute(text("""
                    SELECT 'student_performance_fact' AS table_name,
                        COUNT(*) AS bad_records
                    FROM student_performance_fact f
                    LEFT JOIN teacher_dim t ON f.teacher_id = t.teacher_id
                    WHERE t.teacher_id IS NULL
                    UNION ALL
                    SELECT 'student_attendance_fact' AS table_name,
                        COUNT(*) AS bad_records
                    FROM student_attendance_fact f
                    LEFT JOIN student_dim s ON f.student_id = s.student_id
                    WHERE s.student_id IS NULL
                """)).fetchall()
                
                for table, bad_records in result:
                    if bad_records > 0:
                        print(f"WARNING: {bad_records} orphaned records in {table}")

            # Success reporting
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self.update_etl_status(
                status='success',
                rows_processed=sum(stats.values()),
                duration=duration
            )
            print(f"ETL completed successfully. Processed {sum(stats.values())} records")


# Run ETL
if __name__ == "__main__":
    try:
        etl = ETLProcessor(db_config, wh_config)
        etl.run_full_etl()
    except Exception as e:
        print(f"Fatal error in ETL process: {str(e)}")