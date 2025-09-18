from PyQt5 import uic, QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QWindow
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QHeaderView, QDialogButtonBox, QDialog, QMainWindow
from data201 import db_connection

class StudentHomepageWindow(QMainWindow):  
    # gets signal for logout
    logout_signal = pyqtSignal()
    
    def __init__(self, student_username, student_id):
        """
        Load the UI and initialize its components.
        """
        super().__init__()
        self.student_username = student_username
        self.student_id = student_id
        
        uic.loadUi('student.ui', self)
        self.student_id_label.setText(f"Student ID: {self.student_id}")
        self.show()
        self._fix_tabs()

        # set up the header
        self.sunnydale_header_png.setPixmap(QtGui.QPixmap('sunnydale_header.png'))
        self.sunnydale_logo_png.setPixmap(QtGui.QPixmap('sunnydale_crest.png'))

        self.tabWidget.setCurrentIndex(0)
        self._display_student_name()
        self._display_guardian_info()
        self._display_teacher_info()
        self._display_student_grades()

        self.load_courses
        self._initialize_course_table()
        self._get_student_assignment_grades()

        # when course is changed the student's grades in the selected course populate the assignment table
        self.course_assignment_selector.currentIndexChanged.connect(self._get_student_assignment_grades)

        # hangle logout back to login screen
        self.logout_button.clicked.connect(self._logout)

    def _logout(self):
        self.logout_signal.emit()
        self.close()

    def _initialize_course_table(self):
        self.student_course_table.clearContents()
        self.student_course_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.load_courses()

    def load_courses(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        cursor.callproc('get_student_course_schedule', (self.student_username,))
        courses = []
        for result in cursor.stored_results():
            courses = result.fetchall()

        self.student_course_table.setRowCount(len(courses))
    
        for row_index, row in enumerate(courses):
            for column_index, data in enumerate(row):
                item = QTableWidgetItem(str(data))
                self.student_course_table.setItem(row_index, column_index, item)

        cursor.close()
        conn.close()

        course_listings = []
        for course in courses:
            course_listings.append([course[0], course[1]])
        self._list_courses_dropdown(course_listings)
        print(course_listings)

    def _list_courses_dropdown(self, courses):
        """
        List the students's courses in the dropdown box on the Grades tab
        """
        for course in courses:
            course_name = course[1]
            course_id = course[0]
            self.course_assignment_selector.addItem(f'{course_id} - {course_name}', userData = (course_name, course_id))

    def _get_student_assignment_grades(self):
        """
        List the student's assignment grades for a specific course
        """
        course_data = self.course_assignment_selector.currentData()
        if course_data:
            course_name, course_id = course_data
        else:
            return
        if course_id:
            self.statusBar().showMessage(f'Selected {course_name}', 3000) 

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('get_student_assignment_grades', (self.student_username, course_id,))

        grades = []
        for result in cursor.stored_results():
            grades = result.fetchall()

        # print(grades)

        self.course_assignment_table.setRowCount(len(grades))
    
        for row_index, row in enumerate(grades):
            for column_index, data in enumerate(row):
                item = QTableWidgetItem(str(data))
                self.course_assignment_table.setItem(row_index, column_index, item)
    
        self.course_assignment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _fix_tabs(self):
        tab_bar = self.tabWidget.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(QtCore.Qt.ElideNone)

    def _display_student_name(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        procedure_name = 'get_individual_student'
        cursor.callproc(procedure_name, (self.student_username,))

        for result in cursor.stored_results():
            rows = result.fetchall()
            if rows:
                student_name, dob, grade_level = rows[0]
                self.labelStudentName_2.setText(f"Welcome, {student_name}")
                self.labelStudentName_5.setText(f"{student_name}")
                self.labelStudentDOB_3.setText(f"DOB: {dob}")
                self.labelStudentGradeLevel_3.setText(f"Grade Level: {grade_level}")
    
        cursor.close()
        conn.close()

    def _display_guardian_info(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        procedure_name = 'get_student_guardian'
        cursor.callproc(procedure_name, (self.student_username,))

        guardian_names = []
        guardian_phones = []

        for result in cursor.stored_results():
            rows = result.fetchall()
            for guardian_name, guardian_phone in rows:
                guardian_names.append(guardian_name)
                guardian_phones.append(guardian_phone)

        if guardian_names:
            self.labelGuardianName_3.setText(" / ".join(guardian_names))
            self.labelGuardianPhone_3.setText(" / ".join(guardian_phones))


        cursor.close()
        conn.close()


    def _display_teacher_info(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        procedure_name = 'get_student_hometeacher'
        cursor.callproc(procedure_name, (self.student_username,))

        for result in cursor.stored_results():
            rows = result.fetchall()
            if rows:
                teacher_name, teacher_email = rows[0]
                self.labelTeacherName_3.setText(f"{teacher_name}")
                self.labelTeacherEmail_3.setText(f"{teacher_email}")
    
        cursor.close()
        conn.close()


    def _display_student_grades(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        procedure_name = 'get_student_grades'
        cursor.callproc(procedure_name, (self.student_username,))

        for result in cursor.stored_results():
            rows = result.fetchall()
            if rows:
                table = self.tableWidgetStudentGrades
                table.setRowCount(len(rows))
                for row_index, (course_name, weighted_average, letter_grade) in enumerate(rows):
                    table.setItem(row_index, 0, QTableWidgetItem(course_name))
                    table.setItem(row_index, 1, QTableWidgetItem(str(weighted_average)))
                    table.setItem(row_index, 2, QTableWidgetItem(letter_grade))
        
        self.tableWidgetStudentGrades.resizeColumnsToContents()
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidgetStudentGrades.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)



        cursor.close()
        conn.close()


    
