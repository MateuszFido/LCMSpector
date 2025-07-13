"""
Main entry point for the LC-Inspector application with performance optimizations.

This module provides the main entry point for the LC-Inspector application.
It sets up logging, creates the application, model, view, and controller instances,
and handles application startup.
"""

import sys
import logging
import os
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon

from model.model import Model
from ui.view import View
from ui.controller import Controller

def configure_logging():
    """Configure logging for the application."""
    log_dir = Path(tempfile.gettempdir()) / "lc_inspector_logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = log_dir / "lc_inspector.log"
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
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
    logger.info("Starting LCMSpector...")
    
    # Create the application
    app = QApplication(sys.argv)
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
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
