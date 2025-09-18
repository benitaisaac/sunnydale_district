import mysql.connector
from data201 import db_connection

#connect to warehouse
conn_wh = db_connection(config_file = '/Users/louisas/Documents/Data 201 - Database/Homework/Assignment11/sheql_wh.ini')
cursor = conn_wh.cursor()


# SQL to create all tables
create_tables_sql = """
CREATE TABLE teacher_dim (
  teacher_id INT NOT NULL,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  employment_type VARCHAR(15) NOT NULL,
  PRIMARY KEY (teacher_id)
);

CREATE TABLE student_dim (
  student_id INT NOT NULL,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  date_of_birth DATE NOT NULL,
  grade_level VARCHAR(4) NOT NULL,
  PRIMARY KEY (student_id)
);

CREATE TABLE course_dim (
  course_id INT NOT NULL,
  name VARCHAR(10) NOT NULL,
  PRIMARY KEY (course_id)
);

CREATE TABLE school_dim (
  school_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  school_type VARCHAR(50) NOT NULL,
  address VARCHAR(255) NOT NULL,
  city VARCHAR(50) NOT NULL,
  state VARCHAR(2) NOT NULL,
  zip VARCHAR(10) NOT NULL,
  PRIMARY KEY (school_id)
);

CREATE TABLE student_performance_fact (
  grade_type VARCHAR(20) NOT NULL,
  score INT NOT NULL,
  weight FLOAT NOT NULL,
  weighted_score FLOAT NOT NULL,
  student_id INT NOT NULL,
  course_id INT NOT NULL,
  teacher_id INT NOT NULL,
  school_id INT NOT NULL,
  FOREIGN KEY (student_id) REFERENCES student_dim(student_id),
  FOREIGN KEY (course_id) REFERENCES course_dim(course_id),
  FOREIGN KEY (teacher_id) REFERENCES teacher_dim(teacher_id),
  FOREIGN KEY (school_id) REFERENCES school_dim(school_id)
);

CREATE TABLE date_dim (
  date_id INT NOT NULL,
  day INT NOT NULL,
  month INT NOT NULL,
  semester INT NOT NULL,
  year INT NOT NULL,
  weekday VARCHAR(15) NOT NULL,
  PRIMARY KEY (date_id)
);

CREATE TABLE student_attendance_fact (
  status VARCHAR(25) NOT NULL,
  notes TEXT NOT NULL,
  student_id INT NOT NULL,
  course_id INT NOT NULL,
  teacher_id INT NOT NULL,
  school_id INT NOT NULL,
  date_id INT NOT NULL,
  FOREIGN KEY (student_id) REFERENCES student_dim(student_id),
  FOREIGN KEY (course_id) REFERENCES course_dim(course_id),
  FOREIGN KEY (teacher_id) REFERENCES teacher_dim(teacher_id),
  FOREIGN KEY (school_id) REFERENCES school_dim(school_id),
  FOREIGN KEY (date_id) REFERENCES date_dim(date_id)
);

CREATE TABLE IF NOT EXISTS etl_control (
  process_name VARCHAR(50) PRIMARY KEY,
  last_run DATETIME NOT NULL,
  rows_processed INT,
  status VARCHAR(20),
  error_message TEXT,
  duration_seconds INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# Split by semicolon and execute each statement
for stmt in create_tables_sql.strip().split(';'):
    stmt = stmt.strip()
    if stmt:
        try:
            cursor.execute(stmt + ';')
            print(f"Executed: {stmt[:40]}...")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            print(f"Failed SQL: {stmt}")

# Commit changes and clean up
conn_wh.commit()
cursor.close()
conn_wh.close()
