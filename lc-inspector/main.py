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
import tempfile
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from ui.model import Model
from ui.view import View
from ui.controller import Controller

# Guards for binary building 
if os.sys.stdout is None:
    os.sys.stdout = open(os.devnull, "w")
if os.sys.stderr is None:
    os.sys.stderr = open(os.devnull, "w")
multiprocessing.freeze_support()

def configure_logging():
    """Configure logging for the application."""
    log_dir = Path(tempfile.gettempdir()) / "lcmspector"
    os.makedirs(log_dir, exist_ok=True)

    log_file = log_dir / "lcmspector.log"
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w+'),
            logging.StreamHandler(os.sys.stdout)
        ]
    )
    
    # Set up package-specific loggers
    logger = logging.getLogger("lc_inspector")
    logger.setLevel(logging.INFO)
    
    # Reduce verbosity of third-party libraries
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    return logger

def main():
    """Main entry point for the application."""
    # Configure logging
    logger = configure_logging()
    logger.info("Starting LCMSpector with temp dir: " + tempfile.gettempdir() + "...")
    
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