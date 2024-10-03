from PyQt6.QtWidgets import QApplication
from view import FileView
from controller import FileController

if __name__ == "__main__":
    app = QApplication([])
    view = FileView()
    view.setWindowTitle("UPLC Code")  # Set the window title
    controller = FileController(view)
    view.show()
    app.exec()
