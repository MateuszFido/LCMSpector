"""
Main entry point for the LCMSpector application.

This module provides the main entry point for the LCMSpector application.
It sets up logging, creates the application, model, view, and controller instances,
and handles application startup.
"""

import os
import yaml
import logging
import multiprocessing
import tempfile
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from ui.model import Model
from ui.view import View
from ui.controller import Controller
from ui import fonts
from utils.resources import ensure_ms2_library, DownloadWorker

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
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w+"),
            logging.StreamHandler(os.sys.stdout),
        ],
    )

    # Set up package-specific loggers
    logger = logging.getLogger("lc_inspector")
    logger.setLevel(logging.INFO)
    return logger


def _get_resources_dir() -> Path:
    """Find the resources directory in both source and Nuitka one-folder builds."""
    candidates = [
        Path(__file__).resolve().parent / "resources",
        Path(os.sys.argv[0]).resolve().parent / "resources",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


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
    resources_dir = _get_resources_dir()
    icon_path = resources_dir / "icon.icns"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Create model, view, and controller instances
    model = Model()
    view = View()
    Controller(model, view)

    # Set the application style
    main_font = fonts.get_main_font(11)
    app.setStyle("Fusion")
    app.setFont(main_font)

    # Show the main window
    view.show()

    # Start the event loop
    logger.info("Application initialized, starting event loop")

    # Ensure MS2 library exists locally
    if not ensure_ms2_library():
        if view.show_download_confirmation():
            view.show_download_progressBar()

            # Setup worker and thread for download
            thread = QThread()
            worker = DownloadWorker()
            worker.moveToThread(thread)

            # Connect signals
            worker.progress.connect(view.update_download_progressBar)
            worker.finished.connect(thread.quit)
            worker.finished.connect(view.hide_download_progressBar)
            worker.error.connect(thread.quit)
            thread.started.connect(worker.run)

            # Start and wait for the thread to finish
            thread.start()
            while thread.isRunning():
                app.processEvents()

            # Check for errors after thread finishes
            error_message = None

            def set_error(msg):
                nonlocal error_message
                error_message = msg

            worker.error.connect(set_error)

            if error_message:
                view.show_download_failure(error_message)
                os.sys.exit(1)
            else:
                view.show_download_success()
        else:
            logger.error(
                "MS2 library not found. The MS2 functionality will be disabled."
            )

    os.sys.exit(app.exec())


if __name__ == "__main__":
    main()
