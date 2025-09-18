import sys, os
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QDate, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMessageBox, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
# Load cached data 
from attendance_snapshot import attendance_by_school, attendance_by_grade


from data201 import db_connection


# Simulated data fetch functions
def get_average_exam_score(school_name, grade_level, exam_type):
    import os
    from data201 import db_connection

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(current_dir, "sheql2.ini")

    conn = db_connection(config_file=ini_path)
    cursor = conn.cursor()

    try:
        school_id = get_school_id_by_name(cursor, school_name)
        if not school_id:
            raise ValueError(f"No school ID found for school: {school_name}")

        cursor.callproc('get_avg_score', [school_id, grade_level, exam_type.lower()])
        
        # Fetch result
        avg_score = 0.0
        for result in cursor.stored_results():
            row = result.fetchone()
            if row and row[0] is not None:
                avg_score = row[0]
            break  # only expecting one result set

        return avg_score

    except Exception as e:
        print(f"Error in get_average_exam_score: {e}")
        return 0.0

    finally:
        cursor.close()
        conn.close()


def get_attendance_rate(school_name, grade_level, date_str):
    import os
    from data201 import db_connection

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(current_dir, "sheql2.ini")

    conn = db_connection(config_file=ini_path)
    cursor = conn.cursor()

    try:
        school_id = get_school_id_by_name(cursor, school_name)
        print(f"Resolved school_id: {school_id} for school_name: {school_name}")
        if not school_id:
            raise ValueError(f"No school ID found for school: {school_name}")

        print(f"Calling procedure with: school_id={school_id} ({type(school_id)}), grade_level={grade_level} ({type(grade_level)}), date={date_str} ({type(date_str)})")
        cursor.callproc('get_attendance_rate', [school_id, grade_level, date_str])

        for result in cursor.stored_results():
            rows = result.fetchall()
            print("Procedure returned rows:", rows)
            if rows and rows[0][0] is not None:
                return rows[0][0]

        return 0.0

    except Exception as e:
        print(f"Error in get_attendance_rate: {e}")
        return 0.0

    finally:
        cursor.close()
        conn.close()



# Helper to enforce widget presence
def require_widget(parent, widget_type, name):
    widget = parent.findChild(widget_type, name)
    if widget is None:
        raise RuntimeError(f"Missing widget: {name}")
    return widget

def get_school_id_by_name(cursor, school_name):
    cursor.execute("SELECT school_id FROM school_dim WHERE name = %s", (school_name,))
    result = cursor.fetchone()
    return result[0] if result else None


class DistrictEmployeeDashboard(QtWidgets.QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Load UI
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ui_path = os.path.join(current_dir, "tabbed_district_dashboard_structured2.ui")

            uic.loadUi(ui_path, self)
            self.show()
            self.sunnydale_header_png.setPixmap(QtGui.QPixmap('sunnydale_header.png'))
            print("UI loaded!")

        except Exception as e:
            print(f"Failed to load UI: {e}")
            return

        # Required widgets (Main Dashboard Tab)
        self.comboSchool = require_widget(self, QtWidgets.QComboBox, "comboSchool")
        self.comboGrade = require_widget(self, QtWidgets.QComboBox, "comboGrade")
        self.comboExamType = require_widget(self, QtWidgets.QComboBox, "comboExamType")
        self.dateAttendance = require_widget(self, QtWidgets.QDateEdit, "dateAttendance")
        self.btnFetchExamStats = require_widget(self, QtWidgets.QPushButton, "btnFetchExamStats")
        self.btnFetchAttendance = require_widget(self, QtWidgets.QPushButton, "btnFetchAttendance")
        self.lblExamResult = require_widget(self, QtWidgets.QLabel, "lblExamResult")
        self.lblAttendanceResult = require_widget(self, QtWidgets.QLabel, "lblAttendanceResult")
        self.logout_button = require_widget(self, QtWidgets.QPushButton, "logout_button")

        # Executive Dashboard Tab Widgets
        self.schoolBarChartWidget = require_widget(self, QtWidgets.QWidget, "schoolBarChart")
        self.gradeBarChartWidget = require_widget(self, QtWidgets.QWidget, "gradeBarChart")
        self.comboSchoolChart = require_widget(self, QtWidgets.QComboBox, "comboSchoolChart")

        # Create and attach chart canvases
        self.schoolChart, self.schoolAx = self.create_chart_canvas()
        self.gradeChart, self.gradeAx = self.create_chart_canvas()

        self.schoolBarChartWidget.setLayout(QVBoxLayout())
        self.schoolBarChartWidget.layout().addWidget(self.schoolChart)

        self.gradeBarChartWidget.setLayout(QVBoxLayout())
        self.gradeBarChartWidget.layout().addWidget(self.gradeChart)

        # Connect UI interactions
        self.comboSchool.activated[str].connect(self.on_school_selected)
        self.btnFetchExamStats.clicked.connect(self.fetch_exam_score)
        self.btnFetchAttendance.clicked.connect(self.fetch_attendance_rate)
        self.logout_button.clicked.connect(self._logout)
        


        # Populate school dropdown
        try:
            school_names = self.fetch_school_names()
            print("Fetched school names:", school_names)
            self.comboSchool.addItems(school_names or ["No schools found"])
        except Exception as e:
            self.show_error(f"Failed to load schools:\n{e}")
            self.comboSchool.addItems(["DB Error - fallback"])

        # Set default date
        self.dateAttendance.setDate(QDate.currentDate())

        # Populate dropdown
        self.school_map = {}
        for entry in attendance_by_school:
            school_id = entry[0]
            school_name = entry[1]
            self.comboSchoolChart.addItem(school_name, school_id)
            self.school_map[school_id] = school_name

        self.comboSchoolChart.currentTextChanged.connect(self.update_grade_chart)


         # Initial draw
        self.draw_school_chart()
        self.update_grade_chart()

        # hangle logout back to login screen
        self.logout_button.clicked.connect(self._logout)

    def _logout(self):
        self.logout_signal.emit()
        self.close()

    def fetch_school_names(self):
        # use below for python script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(current_dir, "sheql2.ini")

        conn = db_connection(config_file=ini_path)
        #use below for python notebook
        #conn = db_connection(config_file='sheql2.ini')
        cursor = conn.cursor()

        try:
            cursor.callproc('get_all_schools')
            found_results = False
            schools = []

            for result in cursor.stored_results():
                print("Found stored result set")
                schools = [row[1] for row in result.fetchall()]
                found_results = True
                break 
            
            if not found_results:
                print(" No stored result set found")
                raise RuntimeError("No result set returned from stored procedure.")

            print(f"Fetched schools {schools}")  # Debug statement
            return schools
        
        finally:
            cursor.close()
            conn.close()

    # Handler method to get grade levels 
    def on_school_selected(self, school_name):
        if school_name and "No schools" not in school_name and "Error" not in school_name:
            self.fetch_grade_levels(school_name)
        
    def fetch_grade_levels(self, school_name):
        self.comboGrade.clear()
        self.comboGrade.addItem("Loading grades...")
        QApplication.processEvents()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(current_dir, "sheql2.ini")

        conn = db_connection(config_file=ini_path)
        #conn = db_connection(config_file='sheql2.ini')
        cursor = conn.cursor()

        try:
            school_id = get_school_id_by_name(cursor, school_name)
            if school_id is None:
                raise ValueError("No school ID found for '{school name}'")
            
            cursor.callproc('get_grade_levels', [school_id])
            grades = []

            for result in cursor.stored_results():
                grades = [row[0] for row in result.fetchall()]
            
            self.comboGrade.clear()
            self.comboGrade.addItems(grades if grades else ["No grades found"])

        except Exception as e:
            self.show_error(f"Failed to load grades:\n{e}")
            self.comboGrade.clear()
            self.comboGrade.addItems(['error'])
        
        finally:
            cursor.close()
            conn.close()


    def fetch_exam_score(self):
        school = self.comboSchool.currentText()
        grade = self.comboGrade.currentText()
        exam_type = self.comboExamType.currentText()
        avg = get_average_exam_score(school, grade, exam_type)
        self.lblExamResult.setText(f"Avg: {avg:.2f}")

    def fetch_attendance_rate(self):
        school = self.comboSchool.currentText()
        grade = self.comboGrade.currentText()
        date = self.dateAttendance.date().toString("yyyy-MM-dd")
        rate = get_attendance_rate(school, grade, date)
        self.lblAttendanceResult.setText(f"Avg: {rate:.2f}%")

    def create_chart_canvas(self):
        fig = Figure(figsize=(10, 4))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        return canvas, ax

    def draw_school_chart(self):
        ax = self.schoolAx
        ax.clear()
        names = [entry[1] for entry in attendance_by_school]
        rates = [entry[2] for entry in attendance_by_school]
        ax.barh(names, rates)
        ax.set_xlim(90, 100)
        ax.set_title("Attendance Rate by School")
        ax.tick_params(axis='y', labelsize=9)
        self.schoolChart.figure.subplots_adjust(left=0.35)
        self.schoolChart.draw()

    def update_grade_chart(self):
        selected_id = self.comboSchoolChart.currentData()
        print("Selected ID from comboSchoolChart:", selected_id, type(selected_id))
        print("Available keys in school_map:", list(self.school_map.keys()))

        if selected_id is None:
            print("No School Selected.")
            return
        
        ax = self.gradeAx
        ax.clear()

        filtered = [entry for entry in attendance_by_grade if int(entry["school_id"]) == selected_id]
        # Create a sorting system so we don't lose data in the plot
        def grade_sort_key(g):
            return 0 if g == "K" else int(g)

        filtered_sorted = sorted(filtered, key=lambda e: grade_sort_key(e["grade_level"]))

        grades = [entry["grade_level"] for entry in filtered_sorted]
        rates = [entry["attendance_rate"] for entry in filtered_sorted]

        positions = list(range(len(grades)))

        print("Filtered grades + rates:")
        for entry in filtered_sorted:
            print(entry)
        
        if "10" in grades:
            print("Grade 10 found! Index:", grades.index("10"), "Rate:", rates[grades.index("10")])
        else:
            print("Grade 10 missing from sorted list!")


        #school_name = self.school_map.get(selected_id, f"ID {selected_id}")
        ax.bar(positions, rates, color='tab:blue')
        ax.set_xticks(positions)
        ax.set_xticklabels(grades)
        #ax.bar(grades, rates)
        ax.set_ylim(80, 100)
        ax.set_title(f"Grade-Level Attendance - {self.school_map[selected_id]}")
        ax.tick_params(axis='x', labelsize=9)
        self.gradeChart.draw()


    def show_error(self, msg):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(msg)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DistrictEmployeeDashboard()
    window.setWindowTitle("District Attendance Executive Board")
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec_())
