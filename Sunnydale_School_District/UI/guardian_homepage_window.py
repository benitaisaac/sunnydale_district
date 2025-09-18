from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtCore import QStringListModel, Qt, QDate, pyqtSignal
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui import QTextCharFormat, QColor
from data201 import db_connection

class GuardianHomepageWindow(QMainWindow):
    # gets signal for logout
    logout_signal = pyqtSignal()
    
    def __init__(self, guardian_username):
        """
        Load the UI and initialize its components.
        """
        super().__init__()
        self.guardian_username = guardian_username
        
        uic.loadUi('guardian.ui', self) 
        self.show()

        # set up the header
        self.sunnydale_header_png.setPixmap(QtGui.QPixmap('sunnydale_header.png'))
        self.sunnydale_logo_png.setPixmap(QtGui.QPixmap('sunnydale_crest.png'))

        self.students = {}
        self.selected_student = None
        self.attendance_records = []

        self.tabWidget.setCurrentIndex(0)
        # disable tabs until a student is selected
        self.tabWidget.setTabEnabled(1, False)
        self.tabWidget.setTabEnabled(2, False)
        self.tabWidget.setTabEnabled(3, False)
        
        self._load_guardian_and_students()

        # hangle logout back to login screen
        self.logout_button.clicked.connect(self._logout)

    def _logout(self):
        self.logout_signal.emit()
        self.close()

    def _load_guardian_and_students(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('get_guardian_info', (self.guardian_username,))
        for result in cursor.stored_results():
            rows = result.fetchall()
            break

        cursor.close()
        conn.close()

        if not rows:
            self.labelGuardianName.setText("Welcome, Guardian")
            return

        self.labelGuardianName.setText(f"Welcome, {rows[0][0]}")
        student_names = []
        for row in rows:
            student_id = row[1]
            full_name = f"{row[2]} {row[3]}"
            student_names.append(full_name)
            self.students[full_name] = student_id

        model = QStringListModel()
        model.setStringList(student_names)
        self.listViewStudents.setModel(model)
        self.listViewStudents.clicked.connect(self._on_student_selected)

        self.calendarWidget.selectionChanged.connect(self._on_calendar_date_changed)

    def _on_calendar_date_changed(self):
        if not self.selected_student:
            return

        selected_date = self.calendarWidget.selectedDate().toPyDate()

        # Filter existing attendance data for this student and date
        filtered = [
            row for row in self.attendance_records
            if f"{row[0]} {row[1]}" == self.selected_student["name"] and row[2] == selected_date
        ]

        self.tableWidget.setRowCount(len(filtered))
        for row_idx, row in enumerate(filtered):
            _, _, date, status, notes = row[:5]
            self.tableWidget.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(date)))
            self.tableWidget.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(status))
            self.tableWidget.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(notes or ""))



    def _on_student_selected(self, index):
        student_name = self.listViewStudents.model().data(index, Qt.DisplayRole)
        student_id = self.students[student_name]
        self.selected_student = {"name": student_name, "id": student_id}

        self.labelSelectedStudent.setText(f"Selected Student: {student_name}")
        self._load_student_grades()
        self._load_student_attendance()
        self._load_teacher_info()

        self.tabWidget.setCurrentIndex(1)  # 0 = Dashboard, 1 = Student Grades, 2 = Attendance, etc.
        self.tabWidget.setTabEnabled(1, True)
        self.tabWidget.setTabEnabled(2, True)
        self.tabWidget.setTabEnabled(3, True)


    def _load_student_grades(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('get_guardian_student_grades', (self.guardian_username,))
        for result in cursor.stored_results():
            all_grades = result.fetchall()
            break
        cursor.close()
        conn.close()

        self._on_calendar_date_changed()  # Trigger initial display for selected date


        # Filter for selected student
        grades = [row for row in all_grades if f"{row[0]} {row[1]}" == self.selected_student["name"]]

        self.tableWidget_2.setRowCount(len(grades))
        for row_idx, row in enumerate(grades):
            course, weighted_score, letter = row[2], row[3], row[4]
            self.tableWidget_2.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(course))
            self.tableWidget_2.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(weighted_score)))
            self.tableWidget_2.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(letter))

        self.tableWidget_2.resizeColumnsToContents()
        self.tableWidget_2.resizeRowsToContents()

    def _load_student_attendance(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('get_guardian_student_attendance', (self.guardian_username,))
        for result in cursor.stored_results():
            self.attendance_records = result.fetchall()
            break
        cursor.close()
        conn.close()

        self._on_calendar_date_changed() 
        self._update_attendance_snapshot()

    def _update_attendance_snapshot(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()
        cursor.callproc('get_student_attendance_snapshot', (self.guardian_username, self.selected_student["id"]))
        for result in cursor.stored_results():
            snapshot = result.fetchone()
            break

        if snapshot:
            self.labelPresentCount.setText(f"Present: {snapshot[2]}")
            self.labelAbsentCount.setText(f"Absent: {snapshot[3]}")
            self.labelLateCount.setText(f"Late: {snapshot[4]}")
            self.labelExcusedCount.setText(f"Excused: {snapshot[5]}")

        cursor.callproc('get_guardian_student_attendance_dates', (self.guardian_username, ))
        attendance = []
        for result in cursor.stored_results():
            attendance = result.fetchall()
            
        attendance_info = []
        for entry in attendance:
            attendance_info.append([entry[0], entry[1]])

        # get dates of different attendance types
        present_dates = []
        absent_dates = []
        late_dates = []
        excused_dates = []
        for entry in attendance_info:
            date = entry[0]
            date = QDate(entry[0].year, entry[0].month, entry[0].day)
            if entry[1] == 'present':
                present_dates.append(date)
            elif entry[1] == 'absent':
                absent_dates.append(date)
            elif entry[1] == 'late':
                late_dates.append(date)         
            elif entry[1] == 'excused':
                excused_dates.append(date)  

        # prepare calendar formatting
        present_format = QTextCharFormat()
        present_format.setBackground(QColor('#9bffa3'))
        for date in present_dates:
            self.calendarWidget.setDateTextFormat(date, present_format)
            
        absent_format = QTextCharFormat()
        absent_format.setBackground(QColor('#ff9292'))
        for date in absent_dates:
            self.calendarWidget.setDateTextFormat(date, absent_format)
            
        late_format = QTextCharFormat()
        late_format.setBackground(QColor('#ffff95'))
        for date in late_dates:
            self.calendarWidget.setDateTextFormat(date, late_format)

        excused_format = QTextCharFormat()
        excused_format.setBackground(QColor('#ffd47d'))
        for date in excused_dates:
            self.calendarWidget.setDateTextFormat(date, excused_format)
        
    def _load_teacher_info(self):
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        cursor.callproc('get_guardian_student_teacher', (self.guardian_username, self.selected_student["id"]))
        for result in cursor.stored_results():
            rows = result.fetchall()
            break
        cursor.close()
        conn.close()

        self.comboBoxTeacherSelect.clear()
        for row in rows:
            teacher_name = f"{row[0]} {row[1]}"
            email = row[2]
            self.comboBoxTeacherSelect.addItem(f"{teacher_name} ({email})")
