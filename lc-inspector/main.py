"""
Main entry point for the LCMSpector application with performance optimizations.

This module provides the main entry point for the LCMSpector application.
It sets up logging, creates the application, model, view, and controller instances,
and handles application startup.
"""

import os
import yaml
import logging.config
import multiprocessing
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from ui.model import Model
from ui.view import View
from ui.controller import Controller

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
logger.info(f"-------------------------------------\nStarting LCMSpector at {os.getcwd()}...")

def main():
    """Main entry point for the application."""
    # Create the application
    app = QApplication(os.sys.argv)
    app.setApplicationName("LCMSpector")
    app.setApplicationVersion("1.0.0")

    # Set the application icon
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.icns")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create model, view, and controller instances
    model = Model()
    view = View()
    controller = Controller(model, view)
    
    # Set the application style
    app.setStyle("Fusion")
    
    # Show the main window
    view.show()

    # Start the event loop
    logger.info("Application initialized, starting event loop")
    os.sys.exit(app.exec())

if __name__ == "__main__":
    main()