from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from view import Ui_MainWindow
import sys

class MainWindow(QMainWindow, Ui_MainWindow):
 def __init__(self):
     super().__init__()
     self.setupUi(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())