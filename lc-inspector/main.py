import os, yaml, logging.config, multiprocessing, threading

# Protective guards for binary building 
if os.sys.stdout is None:
    os.sys.stdout = open(os.devnull, "w")
if os.sys.stderr is None:
    os.sys.stderr = open(os.devnull, "w")
multiprocessing.freeze_support()

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

    logger.info("Main executed, Qt application started.")
    logger.info(f"Current thread: {threading.current_thread().name}")
    logger.info(f"Current process: {os.getpid()}")
    exit_code = app.exec()
    logger.info(f"Exiting with exit code {exit_code}.")
    os.sys.exit(exit_code)

