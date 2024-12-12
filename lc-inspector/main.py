import os, secrets
import logging.config
import yaml

if os.sys.stdout is None:
    os.sys.stdout = open(os.devnull, "w")
if os.sys.stderr is None:
    os.sys.stderr = open(os.devnull, "w")

with open(os.path.join(os.path.dirname(__file__), "debug.yaml"), "r+") as f:
    config = yaml.safe_load(f)
    config["handlers"]["file"]["filename"] = os.path.join(os.path.dirname(__file__), "app.log")
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)
logger.info(f"-------------------------------------\nStarting LC-Inspector at {os.getcwd()}...")

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
    app.exec()
    
