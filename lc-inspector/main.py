import os, settings, logging.config, yaml
with open(os.path.join(os.path.dirname(__file__), "config.yaml"), "r") as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)
    
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from ui.model import Model
from ui.view import View
from ui.controller import Controller

if __name__ == "__main__":
    app = QApplication([])
    model = Model()
    view = View()
    controller = Controller(model, view)

    view.show()
    os.sys.exit(app.exec())
    
