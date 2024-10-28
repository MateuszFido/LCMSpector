from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from ui.model import Model
from ui.view import View
from ui.controller import Controller
import sys
import settings

if __name__ == "__main__":
    app = QApplication([])
    model = Model()
    view = View()
    controller = Controller(model, view)

    view.show()
    sys.exit(app.exec())
