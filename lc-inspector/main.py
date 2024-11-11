from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from ui.model import Model
from ui.view import View
from ui.controller import Controller
import os, settings, logging.config, yaml

if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), "logger.yaml"), "rt") as f:
        settings = yaml.safe_load(f.read())
    
    logging.config.dictConfig(settings)
    
    app = QApplication([])
    model = Model()
    view = View()
    controller = Controller(model, view)

    view.show()
    os.sys.exit(app.exec())
    
