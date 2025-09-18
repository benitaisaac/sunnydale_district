import sys, os
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QDate, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

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
    # gets signal for logout
    logout_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()

        # Load UI file
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ui_path = os.path.join(current_dir, "districtAdmin.ui")
            print(f"Loading UI file from: {ui_path}")
            uic.loadUi(ui_path, self)
            self.show()
            # set up the header
            self.sunnydale_header_png.setPixmap(QtGui.QPixmap('sunnydale_header.png'))
            print("UI loaded!")
        except Exception as e:
            print(f"Failed to load UI: {e}")
            return

        # Find required widgets
        self.comboSchool = require_widget(self, QtWidgets.QComboBox, "comboSchool")
        self.comboGrade = require_widget(self, QtWidgets.QComboBox, "comboGrade")
        self.comboExamType = require_widget(self, QtWidgets.QComboBox, "comboExamType")
        self.dateAttendance = require_widget(self, QtWidgets.QDateEdit, "dateAttendance")
        self.btnFetchExamStats = require_widget(self, QtWidgets.QPushButton, "btnFetchExamStats")
        self.btnFetchAttendance = require_widget(self, QtWidgets.QPushButton, "btnFetchAttendance")
        self.lblExamResult = require_widget(self, QtWidgets.QLabel, "lblExamResult")
        self.lblAttendanceResult = require_widget(self, QtWidgets.QLabel, "lblAttendanceResult")

        # Connect buttons to actions
        self.btnFetchExamStats.clicked.connect(self.fetch_exam_score)
        self.btnFetchAttendance.clicked.connect(self.fetch_attendance_rate)

        # Populate school combo box
        try:
            school_names = self.fetch_school_names()
            print("Fetched school names:", school_names)
            if not school_names:
                self.comboSchool.addItems(["No schools found"])
            else:
                self.comboSchool.addItems(school_names)
        except Exception as e:
            self.show_error(f"Failed to load schools:\n{e}")
            self.comboSchool.addItems(["DB Error - fallback"])

        # Connect selected school to grade loading function 
        self.comboSchool.currentTextChanged.connect(self.on_school_selected)

        # Set default date
        self.dateAttendance.setDate(QDate.currentDate())

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
        # use below for python script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(current_dir, "sheql2.ini")

        conn = db_connection(config_file=ini_path)
        #use below for python notebook
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

    def show_error(self, msg):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(msg)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

