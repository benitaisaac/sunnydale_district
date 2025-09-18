import sys
from PyQt5.QtWidgets import QApplication
from student_homepage_window import StudentHomepageWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StudentHomepageWindow()
    sys.exit(app.exec_())