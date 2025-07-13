"""
Main entry point for the LC-Inspector application.

This module initializes the application, sets up logging, and creates the MVC components.
"""

import os
import yaml
import logging.config
import multiprocessing
import threading

# Protective guards for binary building 
if os.sys.stdout is None:
    os.sys.stdout = open(os.devnull, "w")
if os.sys.stderr is None:
    os.sys.stderr = open(os.devnull, "w")
multiprocessing.freeze_support()

# Set up logging
with open(os.path.join(os.path.dirname(__file__), "debug.yaml"), "r+") as f:
    config = yaml.safe_load(f)
    config["handlers"]["file"]["filename"] = os.path.join(os.path.dirname(__file__), "app.log")
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)
logger.info(f"-------------------------------------\nStarting LC-Inspector at {os.getcwd()}...")

# Import PyQt and application components
from PyQt6.QtWidgets import QApplication
from model.lc_inspector_model import LCInspectorModel
from ui.view import View
from ui.controller_refactored import Controller

if __name__ == "__main__":
    # Create the application
    app = QApplication([])
    
    # Create the MVC components
    model = LCInspectorModel()
    view = View()
    controller = Controller(model, view)
    
    # Show the view
    view.show()

    # Log application start
    logger.info("Main executed, Qt application started.")
    logger.info(f"Current thread: {threading.current_thread().name}")
    logger.info(f"Current process: {os.getpid()}")
    
    # Run the application
    exit_code = app.exec()
    logger.info(f"Exiting with exit code {exit_code}.")
    os.sys.exit(exit_code)
