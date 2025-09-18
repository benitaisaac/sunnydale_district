import sys
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.uic import loadUi
from PyQt5.QtCore  import Qt

from data201 import db_connection

from teacher_homepage_window import TeacherHomepageWindow
from student_homepage_window import StudentHomepageWindow
from guardian_homepage_window import GuardianHomepageWindow
from merged_district_dashboard import DistrictEmployeeDashboard

class Main(QDialog):
    def __init__(self):
        """
        Initialize the program
        """
        super(Main, self).__init__()
        
        self.ui = uic.loadUi("login.ui", self)
        
        self.show()
        
        self.ui.sunnydale_logo_png.setPixmap(QtGui.QPixmap('sunnydale_crest.png'))
        
        self.ui.login_button.clicked.connect(self._login_button_clicked)
        self.ui.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        
    def _show_login_dialog(self):
        """
        Show login screen after a user logs out
        """
        self.ui.username_edit.clear()
        self.ui.password_edit.clear()
        self.ui.login_message.clear()
        self.ui.show()

    def _login_button_clicked(self):
        """
        Get login variables
        """
        username = self.ui.username_edit.text().strip()
        password = self.ui.password_edit.text().strip()
        self._login(username, password)

    def _login(self, username, password):
        """ 
        Use the login variables to check for user
        """
        conn = db_connection(config_file='sheql.ini')
        cursor = conn.cursor()

        # get role of the user, if login details are correct
        sql = """ 
            SELECT u.username,
                u.password,
                u.role
            FROM users u
            WHERE u.username = (%s) 
            AND u.plain_password = (%s)
            """

        cursor.execute(sql, (username, password))
        result = cursor.fetchall()
        print(result)

        if len(result) == 0:
            self.ui.login_message.setText("Invalid username or password!")
            return
        else:
            # if the user logging in is a student, they will be shown the student page
            if result[0][2] == 'student':
                sql = """ 
                    SELECT s.student_id
                    FROM student s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE u.username = (%s) 
                    """
                cursor.execute(sql, (username,))
                student_result = cursor.fetchall()
                student_id = student_result[0][0]
                student_username = username
                self.ui.student_window = StudentHomepageWindow(student_username = student_username, student_id = student_id)
                self.ui.student_window.logout_signal.connect(self._show_login_dialog)
                self.ui.hide()
                self.ui.student_window.show()
            # if the user logging in is a teacher, they will be shown the teacher page
            elif result[0][2] == 'teacher':
                sql = """ 
                    SELECT t.teacher_id
                    FROM teacher t
                    JOIN users u ON t.user_id = u.user_id
                    WHERE u.username = (%s) 
                    """
                cursor.execute(sql, (username,))
                teacher_result = cursor.fetchall()
                teacher_id = teacher_result[0][0]
                self.ui.teacher_window = TeacherHomepageWindow(teacher_id=teacher_id)
                self.ui.teacher_window.logout_signal.connect(self._show_login_dialog)
                self.ui.hide()
                self.ui.teacher_window.show()
            # if the user logging in is a student guardian, they will be shown the guardian page
            elif result[0][2] == 'guardian':
                guardian_username = username
                self.ui.guardian_window = GuardianHomepageWindow(guardian_username = guardian_username)
                self.ui.guardian_window.logout_signal.connect(self._show_login_dialog)
                self.ui.hide()
                self.ui.guardian_window.show()
            # if the user logging in is an admin, they will be shown the admin page
            elif result[0][2] == 'district_admin':
                admin_username = username
                self.ui.admin_window = DistrictEmployeeDashboard()
                self.ui.admin_window.logout_signal.connect(self._show_login_dialog)
                self.ui.hide()
                self.ui.admin_window.show()
            else:
                # If the role is not defined, show the error message
                self.ui.login_message.setText("System Error, Please contact admin")
                return
            print(result)

        
