from PyQt5 import uic, QtGui
from PyQt5.QtGui import QWindow
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QHBoxLayout, QWidget
from PyQt5.QtCore import QDate, Qt, pyqtSignal

from data201 import db_connection
import datetime

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qt5agg import FigureCanvas 
from pandas import DataFrame

class TeacherHomepageWindow(QMainWindow):
    """
    The teacher page of the application
    """
    # gets signal for logout
    logout_signal = pyqtSignal()

    
    def __init__(self, teacher_id):
        """
        Load the UI and initialize its components.
        """
        super().__init__()
        self.teacher_id = teacher_id

        uic.loadUi('teacher.ui', self)
        self.teacher_id_label.setText(f"Teacher ID: {self.teacher_id}")
        self.show()

        # set up the header
        self.sunnydale_header_png.setPixmap(QtGui.QPixmap('sunnydale_header.png'))
        
        ### ------ DASHBOARD TAB FUNCTIONALITY -------------
        # open the application on the Dashboard tab
        self.tabWidget.setCurrentIndex(0)

        # set today's date on the calendar
        self.teacher_calendar.setSelectedDate(QDate.currentDate())

        # initialize the teacher's course table
        self._initialize_courses_table()

        # load the teacher's information
        self.get_teacher()

        # load the teacher's course table
        self.load_courses()

        # connect the "Go to Grade Management" button to Grade Management tab
        self.teacher_grade_button.clicked.connect(self._switch_grade_tab)

        # connect the "Mark Attendance" button to Attendance tab
        self.teacher_attendance_button.clicked.connect(self._switch_attendance_tab)

        # hangle logout back to login screen
        self.logout_button.clicked.connect(self._logout)

        ### ------ GRADE MANAGEMENT TAB FUNCTIONALITY -------------
        # initialize the student's grade table
        self._initialize_grades_table()

        # change the students list in the Student dropdown menu in the Grade Management tab 
        self.grade_course_selector.currentIndexChanged.connect(self._show_students_from_selected_course)

        # change the grades list shown in the Grade Management tab when selecting a student
        self.grade_student_selector.currentIndexChanged.connect(self._show_student_grades_from_selected_course)

        # save a student's updated to the database when the "Edit" button is clicked on the Grade Management Tab
        self.grade_edit_button.clicked.connect(self._edit_student_grades)

        # delete one assignment's grade when the "Delete Selected Grade" button is clicked on the Grade Management Tab
        self.grade_delete_button.clicked.connect(self._delete_student_grade)

        # add a new grade to the student's tablewhen the "Add Grade" button is clicked on the Grade Management Tab
        self.grade_add_button.clicked.connect(self._add_student_grade)

        ### ------ ATTENDANCE TAB FUNCTIONALITY -------------
        # initialize the student's grade table
        self._initialize_attendance_table()
        
        # either take/record attendance depending on attendance screen user is on
        self.attendance_button.clicked.connect(self._switch_attendance_button)

        # change the date list shown in the Attendance tab when selecting a course
        # self._show_attendance_dates_from_selected_course()
        self.attendance_course_selector.currentIndexChanged.connect(self._show_attendance_dates_from_selected_course)

        # change the attendance list shown in the Attendance tab when selecting a date
        # self._show_attendance_from_selected_date()
        self.attendance_date_selector.currentIndexChanged.connect(self._show_attendance_from_selected_date)

        # get the attendance chart for the day selected
        # self._draw_attendance_bar_chart()
        self.attendance_date_selector.currentIndexChanged.connect(self._draw_attendance_bar_chart)

        ### ------ COMMUNICATION TAB FUNCTIONALITY -------------
        # initialize the student's grade table
        self._initialize_communication_table()

        # get students to show in the dropdown menu
        self._show_students_by_teacher()

        # change the guardian list when a student is selected in the Communication tab
        self._show_guardians_of_student()
        self.communication_student_selector.currentIndexChanged.connect(self._show_guardians_of_student)

        ### ------ ANALYTICS TAB FUNCTIONALITY -------------
        # initialize the analytics table
        self._initialize_analytics_table()

        # change to a course's grade report using dropdown menu
        self._show_course_grade_report()
        self.analytics_course_selector.currentIndexChanged.connect(self._show_course_grade_report)

        # show the chart of grade counts
        self._draw_grades_bar_chart()
        self.analytics_course_selector.currentIndexChanged.connect(self._draw_grades_bar_chart)

    ### ------ DASHBOARD TAB  ----------
    def load_courses(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        cursor.callproc('teacher_course_schedule', (self.teacher_id,))
        courses = []
        for result in cursor.stored_results():
            courses = result.fetchall()

        self.teacher_classes_table.setRowCount(len(courses))
    
        for row_index, row in enumerate(courses):
            for column_index, data in enumerate(row):
                item = QTableWidgetItem(str(data))
                self.teacher_classes_table.setItem(row_index, column_index, item)
    
        self.teacher_classes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
        cursor.close()
        conn.close()

        # get the course names to populate the course dropdown in the Grade Management tab
        course_listings = []
        for course in courses:
            course_listings.append([course[1], course[0], course[2]])
        self._list_courses_dropdown(course_listings)
        
    def _logout(self):
        """
        Logs out the teacher
        """
        self.logout_signal.emit()
        self.close()
        
    def get_teacher(self):
        """
        Get the logged in teacher's information
        """
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        cursor.callproc('teacher_information', (self.teacher_id,))

        teacher_info = []
        for result in cursor.stored_results():
            teacher_info = result.fetchall()

        self.teacher_name_label.setText(f'Welcome, {teacher_info[0][1]}!')

        cursor.close()
        conn.close()

    ### ------ GRADE MANAGEMENT TAB  ----------
    def _initialize_courses_table(self):
        """
        Initialize/clear the teacher's courses table 
        """
        self.teacher_classes_table.clearContents()
        self.teacher_classes_table.setColumnCount(5)
        self.teacher_classes_table.setHorizontalHeaderLabels(['Course ID', 'Course Name', 'Grade Level', 'Class Times', 'Days'])
        self.student_grade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def _initialize_grades_table(self):
        """
        Initialize/clear the student's grades table
        """
        self.student_grade_table.clearContents()
        self.student_grade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
         
    def _switch_grade_tab(self):
        """
        Switch to the grade tab when hitting 'Go to Grade Management' button
        """
        self.tabWidget.setCurrentIndex(1)

    def _list_courses_dropdown(self, courses):
        """
        List the teacher's courses in the dropdown box on the Grade Management tab
        """
        self.grade_course_selector.clear()
        self.grade_add_type_edit.clear()
        self.grade_add_score_edit.clear()
        self.grade_add_weight_edit.clear()
        self.grade_letter_label.clear()
        self.grade_weighted_label.clear()

        # list the course name and pass in the course id as a hidden value (to call in another function)
        self.grade_course_selector.addItem('Select Course', None)
        self.attendance_course_selector.addItem('Select Course', None)
        # self.analytics_course_selector.addItem('Select Course', None)
        for course in courses:
            course_name = course[0]
            course_id = course[1]
            grade = course[2]
            self.grade_course_selector.addItem(f'{course_id} - {course_name} ({grade})', userData = (course_name, course_id, grade))
            self.attendance_course_selector.addItem(f'{course_id} - {course_name} ({grade})', userData = (course_name, course_id,))
            self.analytics_course_selector.addItem(f'{course_id} - {course_name} ({grade})', userData = (course_name, course_id, grade))
            
    def _show_students_from_selected_course(self):
        """
        List the students in the selected course in the dropdown box on the Grade Management tab
        """
        self.grade_student_selector.clear()
        course_data = self.grade_course_selector.currentData()
        if course_data:
            course_name, course_id, grade = course_data
            QMessageBox.information(self, 'Course Selection', f'{course_name} ({grade}) selected. Student list has been updated.')

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('teacher_one_class_all_students', (self.teacher_id, course_id, grade))

        students = []
        for result in cursor.stored_results():
            students = result.fetchall()

        self.grade_student_selector.addItem('Select Student', None)
        for student in students:
            student_id = str(student[1])
            student_name = str(student[4])
            self.grade_student_selector.addItem(f'{student_id} - {student_name}', userData = student_id)
        
        cursor.close()
        conn.close()

    def _show_student_grades_from_selected_course(self):
        """
        List the student's grades in the selected course in the table on the Grade Management tab
        """
        self.student_grade_table.clearContents()
        self.grade_add_type_edit.clear()
        self.grade_add_score_edit.clear()
        self.grade_add_weight_edit.clear()
        self.grade_letter_label.clear()
        self.grade_weighted_label.clear()
        
        course_data = self.grade_course_selector.currentData()
        if course_data:
            course_name, course_id, grade = course_data
        else:
            return
        student_id = self.grade_student_selector.currentData()
        if student_id:
            self.statusBar().showMessage(f'Selected student ID {student_id}', 3000) 

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('teacher_one_student_one_class_grades', (self.teacher_id, student_id, course_id,))

        grades = []
        for result in cursor.stored_results():
            grades = result.fetchall()

        # print(grades)

        self.student_grade_table.setRowCount(len(grades))
    
        for row_index, row in enumerate(grades):
            for column_index, data in enumerate(row):
                item = QTableWidgetItem(str(data))
                self.student_grade_table.setItem(row_index, column_index, item)
    
        self.student_grade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # populate the student's letter grade and weighted grade
        if student_id is not None:
            cursor.callproc('teacher_one_student_weighted_grade', (self.teacher_id, student_id, course_id,))
    
            grade_info = []
            for result in cursor.stored_results():
                grade_info = result.fetchall()
            print(grade_info)

            self.grade_letter_label.setText(grade_info[0][1])
            self.grade_weighted_label.setText(f'{str(grade_info[0][0])}%')
    
        cursor.close()
        conn.close()

    def _edit_student_grades(self):
        """
        Save edits to a student's grade table in the Grade Management tab
        """
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        course_data = self.grade_course_selector.currentData()
        course_name, course_id, grade = course_data
        student_id = self.grade_student_selector.currentData()
        
        grade_count = self.student_grade_table.rowCount()

        try:
            for grade in range(grade_count):
                grade_type = self.student_grade_table.item(grade, 0).text()
                score = self.student_grade_table.item(grade, 1).text()
                # print(course_id, student_id, grade_type, score)

                try:
                    score = int(score)
                except: 
                    QMessageBox.information(self, 'Grade Change', 'You must enter a valid number!')
                    
                if score < 0 or score > 100:
                    QMessageBox.information(self, 'Grade Change', 'You must enter a valid score between 0 or 100!')
                    return
                
                cursor.callproc('teacher_update_grade', (student_id, course_id, grade_type, score,))
                
            QMessageBox.information(self, 'Grade Change', 'All edited grades (if any) have been updated!')
            conn.commit()
            self._show_student_grades_from_selected_course()
            
        except:
            QMessageBox.information(self, 'Grade Change', 'Error changing grade. Please try again.')

        cursor.close()
        conn.close()

    def _delete_student_grade(self):
        """
        Delete the selected grade from the student's grade table in the Grade Management tab 
        """
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        course_data = self.grade_course_selector.currentData()
        course_name, course_id, grade = course_data
        student_id = self.grade_student_selector.currentData()
        selected_grade = self.student_grade_table.currentRow()
        grade_type = self.student_grade_table.item(selected_grade, 0).text()
        # print(course_id, student_id, grade_type)
        
        confirmation = QMessageBox.question(self, 'Delete Grade?', f'Proceed with the deletion of {grade_type}?', QMessageBox.Yes | QMessageBox.No)

        if confirmation == QMessageBox.Yes:
            try:
                cursor.callproc('teacher_delete_grade', (student_id, course_id, grade_type,))
                
                QMessageBox.information(self, 'Grade Deletion', f'{grade_type.capitalize()} has been deleted!')
                conn.commit()
                self._show_student_grades_from_selected_course()
                    
            except:
                QMessageBox.information(self, 'Grade Deletion', 'Error deleting grade. Please try again.')

        cursor.close()
        conn.close()

    def _add_student_grade(self):
        """
        Add a grade to the student's grade table in the Grade Management tab 
        """
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        
        course_data = self.grade_course_selector.currentData()
        course_name, course_id, grade = course_data
        student_id = self.grade_student_selector.currentData()
        grade_type = self.grade_add_type_edit.text().strip()
        score = self.grade_add_score_edit.text().strip()
        weight = self.grade_add_weight_edit.text().strip()
        print(course_id, student_id, grade_type, score, weight)

        if grade_type != '':
            try:
                weight_float = float(weight)
            except:
                QMessageBox.information(self, 'Grade Addition', 'Please enter a float value for weight.')
            if weight_float and score.isdigit():
                if 0 < int(score) < 100  and 0 < weight_float < .50:
                    try:
                        cursor.callproc('teacher_add_grade', (student_id, course_id, grade_type, score, weight_float,))
                        
                        QMessageBox.information(self, 'Grade Addition', f'{grade_type.capitalize()} has been added!')
                        
                        conn.commit()
                        self._show_student_grades_from_selected_course()
                            
                    except:
                        QMessageBox.information(self, 'Grade Addition', 'Error adding grade. Please check if inputs are valid and the assignment does not already exist.')
            else:
                QMessageBox.information(self, 'Grade Addition', 'Invalid score/weight. Please try again.')
        else:
            QMessageBox.information(self, 'Grade Addition', 'You must enter an assignment name. Please try again.')
        
        cursor.close()
        conn.close()

    ### ------ ATTENDANCE TAB  ----------
    def _switch_attendance_tab(self):
        """
        Switch to the attendance tab when hitting 'Mark Attendance' button
        """
        self.tabWidget.setCurrentIndex(2)

    def _initialize_attendance_table(self):
        """
        Initialize/clear analytics table
        """
        self.attendance_student_table.clearContents()
        self.teacher_classes_table.setColumnCount(5)
        self.attendance_student_table.setHorizontalHeaderLabels(['Student ID', 'Last Name', 'First Name', 'Status', 'Notes'])
        self.attendance_student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.attendance_button.setEnabled(False)

    def _switch_attendance_button(self):
        """
        Switch the functionality of the attendance button depending on what attendance screen is visible
        """
        if self.attendance_button.objectName() == 'attendance_button':
            self._take_attendance()
        elif self.attendance_button.objectName() == 'save_attendance_button':
            self._record_attendance()
        
    def _show_attendance_dates_from_selected_course(self):
        """
        List dates where attendance was recorded in the selected course in the dropdown box on the Grade Management tab
        """
        self._clear_graph()
        self.attendance_student_table.setColumnCount(5)
        self.attendance_student_table.setHorizontalHeaderLabels(['Student ID', 'Last Name', 'First Name', 'Status', 'Notes'])
        
        self.attendance_date_selector.clear()
        course_data = self.attendance_course_selector.currentData()
        if course_data:
            course_name, course_id = course_data
            QMessageBox.information(self, 'Course Selection', f'{course_name} selected. Date list has been updated.')

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        if course_id:
            cursor.callproc('teacher_class_attendance_dates', (self.teacher_id, course_id,))

        dates = []
        converted_dates = []
        for result in cursor.stored_results():
            dates = result.fetchall()
            dates = dates[::-1]

        self.attendance_date_selector.addItem('Select Date', None)
        for date in dates:
            date = date[0]
            converted_date = date.strftime('%Y-%m-%d')
            converted_dates.append(converted_date)
            self.attendance_date_selector.addItem(converted_date, userData = converted_date)

        today_date = QDate.currentDate().toString('yyyy-MM-dd')
        # today_date = '2025-05-17'
        if today_date not in converted_dates:
            self.attendance_button.setEnabled(True)
        else:
            self.attendance_button.setText("Take Today's Attendance")
            self.attendance_button.setEnabled(False)
        
        cursor.close()
        conn.close()

    def _show_attendance_from_selected_date(self):
        """
        List the attendance on the selected date in the table on the Attendance tab
        """
        self.attendance_student_table.setColumnCount(5)
        self.attendance_student_table.setHorizontalHeaderLabels(['Student ID', 'Last Name', 'First Name', 'Status', 'Notes'])
        self.attendance_student_table.clearContents()
        self.attendance_button.setObjectName('attendance_button')

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        course_data = self.attendance_course_selector.currentData()
        course_name, course_id = course_data

        cursor.callproc('teacher_class_attendance_dates', (self.teacher_id, course_id,))
        
        dates = []
        converted_dates = []
        for result in cursor.stored_results():
            dates = result.fetchall()

        for date in dates:
            date = date[0]
            converted_date = date.strftime('%Y-%m-%d')
            converted_dates.append(converted_date)
            
        today_date = QDate.currentDate().toString('yyyy-MM-dd')
        # today_date = '2025-05-17'
        if today_date not in converted_dates:
            self.attendance_button.setEnabled(True)
        else:
            self.attendance_button.setText("Take Today's Attendance")
            self.attendance_button.setEnabled(False)
            
        date = self.attendance_date_selector.currentData()
        
        cursor.callproc('teacher_class_attendance_by_date', (self.teacher_id, date,))
        
        records = []
        for result in cursor.stored_results():
            records = result.fetchall()
            
        self.attendance_student_table.setRowCount(len(records))
        
        for row_index, row in enumerate(records):
            for column_index, data in enumerate(row):
                if column_index == 4 and data is None:
                    data = ''
                item = QTableWidgetItem(str(data))
                self.attendance_student_table.setItem(row_index, column_index, item)
        
        self.attendance_student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        if date:
            self.statusBar().showMessage(f'Selected {date}', 3000) 
        
        cursor.close()
        conn.close()

    def _take_attendance(self):
        """
        Bring up the take attendance table for today
        """
        self.attendance_student_table.clearContents()

        # get current date
        today_date = QDate.currentDate().toString('yyyy-MM-dd')
        # today_date = '2025-05-17'
        self.attendance_date_selector.addItem(today_date)
        self.attendance_date_selector.setCurrentText(today_date)

        # change button text and object name
        self.attendance_button.setObjectName('save_attendance_button')

        if today_date:
            self.statusBar().showMessage(f'Selected {today_date}', 3000) 
        
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        # get class attendance roster (just using previous date)
        cursor.callproc('teacher_class_attendance_by_date', (self.teacher_id, '2025-03-17',)) # DONT CHANGE THIS DATE
        
        records = []
        for result in cursor.stored_results():
            records = result.fetchall()

        # resize the table to account for extra columns for attendance status
        self.attendance_student_table.setColumnCount(6)
        self.attendance_student_table.setHorizontalHeaderLabels(['Student ID', 'Last Name', 'First Name', 'Absent', 'Late', 'Notes'])

        self.attendance_student_table.setRowCount(len(records))
        
        for row_index, row in enumerate(records):
            for column_index, data in enumerate(row[:3]):
                item = QTableWidgetItem(str(data))
                self.attendance_student_table.setItem(row_index, column_index, item)

            # create checkboxes in absent column and format
            absent_checkbox = QCheckBox()
            absent_container = QWidget()
            absent_layout = QHBoxLayout(absent_container)
            absent_layout.addWidget(absent_checkbox)
            absent_layout.setAlignment(absent_checkbox, Qt.AlignCenter)
            self.attendance_student_table.setCellWidget(row_index, 3, absent_container)

            # create checkboxes in the late column and format
            late_checkbox = QCheckBox()
            late_container = QWidget()
            late_layout = QHBoxLayout(late_container)
            late_layout.addWidget(late_checkbox)
            late_layout.setAlignment(late_checkbox, Qt.AlignCenter)
            self.attendance_student_table.setCellWidget(row_index, 4, late_container)
        
        self.attendance_student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
        cursor.close()
        conn.close()

    def _record_attendance(self):
        """
        Record attendance for the given day
        """
        # get values from the attendance table to save attendance for each student
        attendance = self.attendance_student_table.rowCount()
        print(attendance)
        
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        date = QDate.currentDate().toString('yyyy-MM-dd')
        # date = '2025-05-17'

        try:
            for record in range(attendance):
                student_id = self.attendance_student_table.item(record, 0).text()
                last_name = self.attendance_student_table.item(record, 1).text()
                first_name = self.attendance_student_table.item(record, 2).text()
                check_absent = self.attendance_student_table.cellWidget(record, 3)
                absent = check_absent.findChild(QCheckBox).isChecked()
                check_late = self.attendance_student_table.cellWidget(record, 4)
                late = check_late.findChild(QCheckBox).isChecked()
                notes_check = self.attendance_student_table.item(record, 5)
                
                if notes_check:
                    notes = notes_check.text()
                else:
                    notes = ''
    
                # print(student_id, date, self.teacher_id, notes)
                    
                try:
                    status = None
                    if absent and late:
                        QMessageBox.information(self, 'Attendance', f'Attendance for {first_name} {last_name} marked as both absent and late. Please select only one.')
                        conn.rollback()
                        return
                    if not absent and not late:
                        status = 'present'
                    elif absent and not late:
                        status = 'absent'
                    elif late and not absent:
                        status = 'late'
                    if status is None:
                        raise ValueError('Absent and late both checked!')
        
                    cursor.callproc('teacher_add_attendance', (student_id, date, status, self.teacher_id, notes,))
                    
                except Exception as e:
                    conn.rollback()
                    QMessageBox.information(self, 'Attendance', 'Error recording attendance for one or more students. Please try again.')
                    print(e)
    
            conn.commit()
            QMessageBox.information(self, 'Attendance', f'Attendance for {date} has successfully been recorded.')
            self.attendance_button.setEnabled(False)
            self.attendance_date_selector.insertItem(0, date, userData = date)
            self.attendance_date_selector.setCurrentText(date)
            self._show_attendance_from_selected_date()

            cursor.close()
            conn.close()
        
        except:
            conn.rollback()
            QMessageBox.information(self, 'Attendance', 'Error recording attendance. Please try again.')

    def _draw_attendance_bar_chart(self):
        """
        Draw a bar chart showcasing attendance counts each day
        """
        self._clear_graph()
        
        date = self.attendance_date_selector.currentData()
        
        if date: 
            conn = db_connection(config_file='sheql.ini')
            cursor = conn.cursor()

            # get class attendance counts by date
            cursor.callproc('teacher_attendance_counts_by_date', (self.teacher_id, date,)) 
    
            counts = []
            for result in cursor.stored_results():
                counts = result.fetchall()
    
            cursor.close()
            conn.close()
                
            df = DataFrame(counts, columns = ['Attendance Type', 'Number of Students'])
            
            sns.set(style='whitegrid')
            ax = sns.barplot(x='Attendance Type', y='Number of Students', hue ='Attendance Type',
                             data=df,  errorbar=None, 
                             palette=['#5acaf2', '#ff5959', '#fff07a', '#4de378'])
    
            ax.set_title(f'Attendance for {date}')
            self.attendance_chart_layout.addWidget(FigureCanvas(ax.figure))
    
            plt.close()

    def _clear_graph(self):
        """
        Remove all the bars from the graph.
        """
        children = []
        
        # Gather children which are the bars in the layout.
        for i in range(self.attendance_chart_layout.count()):
            child = self.attendance_chart_layout.itemAt(i).widget()
            if child:
                children.append(child)
                
        # Delete the bars.
        for child in children:
            child.deleteLater()

    ### ------ COMMUNICATION TAB  ----------
    def _initialize_communication_table(self):
        """
        Initialize/clear the guardian table
        """
        self.communication_guardian_table.clearContents()
        self.communication_guardian_table.setColumnCount(4)
        self.communication_guardian_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


    def _show_students_by_teacher(self):
        """
        List all students that a teacher teaches
        """
        self.communication_student_selector.clear()

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('teacher_all_students', (self.teacher_id, ))

        students = []
        for result in cursor.stored_results():
            students = result.fetchall()

        self.grade_student_selector.addItem('Select Student', None)
        for student in students:
            student_id = str(student[1])
            student_name = str(student[4])
            self.communication_student_selector.addItem(f'{student_id} - {student_name}', userData = student_id)
        
        cursor.close()
        conn.close()

    def _show_guardians_of_student(self):
        """
        List the student's guardians
        """      
        student_id = self.communication_student_selector.currentData()
        if student_id:
            self.statusBar().showMessage(f'Selected student ID {student_id}', 3000) 

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('teacher_one_student_all_guardians', (self.teacher_id, student_id,))

        guardians = []
        for result in cursor.stored_results():
            guardians = result.fetchall()

        self.communication_guardian_table.setRowCount(len(guardians))
    
        for row_index, row in enumerate(guardians):
            for column_index, data in enumerate(row):
                item = QTableWidgetItem(str(data))
                self.communication_guardian_table.setItem(row_index, column_index, item)

        cursor.close()
        conn.close()


    ### ------ ANALYTICS TAB  ----------
    def _initialize_analytics_table(self):
        """
        Initialize/clear the analytics table
        """
        self.analytics_student_grade_counts_table.clearContents()
        self.analytics_student_grade_counts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _show_course_grade_report(self):
        """
        Populate table with the number of each grade for a course
        """
        course_data = self.analytics_course_selector.currentData()
        if course_data:
            course_name, course_id, grade = course_data

        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('teacher_one_class_student_count', (self.teacher_id, course_id, grade,))

        student_count = []
        for result in cursor.stored_results():
            student_count = result.fetchall()

        self.analytics_count_total_label.setText(str(student_count[0][0]))

        cursor.callproc('teacher_one_class_grade_counts', (self.teacher_id, course_id, grade))
        
        grade_counts = []
        for result in cursor.stored_results():
            grade_counts = result.fetchall()
        print(grade_counts)
        
        self.analytics_student_grade_counts_table.setRowCount(len(grade_counts))
        
        for row_index, row in enumerate(grade_counts):
            for column_index, data in enumerate(row):
                item = QTableWidgetItem(str(data))
                self.analytics_student_grade_counts_table.setItem(row_index, column_index, item)
        
        self.analytics_student_grade_counts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        cursor.close()
        conn.close()

    def _draw_grades_bar_chart(self):
        """
        Draw a bar chart showcasing grade counts 
        """
        self._clear_grades_graph()
        
        course_data = self.analytics_course_selector.currentData()
        if course_data:
            course_name, course_id, grade = course_data
        
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        # get grade counts per class
        cursor.callproc('teacher_one_class_grade_counts', (self.teacher_id, course_id, grade)) 

        counts = []
        for result in cursor.stored_results():
            counts = result.fetchall()

        cursor.close()
        conn.close()
            
        df = DataFrame(counts, columns = ['Letter Grade', 'Number of Students'])
        
        sns.set(style='whitegrid')
        ax = sns.barplot(x='Letter Grade', y='Number of Students', hue ='Letter Grade',
                         data=df,  errorbar=None, 
                         palette=['#27f562', '#88f06e', '#f0f06e', '#f0ad6e', '#f24b4b'])

        ax.set_title(f'Grade Report for {course_name}')
        self.chart_layout.addWidget(FigureCanvas(ax.figure))

        plt.close()

    def _clear_grades_graph(self):
        """
        Remove all the bars from the graph.
        """
        children = []
        
        # Gather children which are the bars in the layout.
        for i in range(self.chart_layout.count()):
            child = self.chart_layout.itemAt(i).widget()
            if child:
                children.append(child)
                
        # Delete the bars.
        for child in children:
            child.deleteLater()