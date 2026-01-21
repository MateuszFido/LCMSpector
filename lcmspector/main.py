"""
Main entry point for the LCMSpector application.

This module provides the main entry point for the LCMSpector application.
It sets up logging, creates the application, model, view, and controller instances,
and handles application startup.
"""

import os
import sys
import yaml
import logging
import logging.handlers
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
    """Configure logging with rotation to keep the last 5 sessions."""
    log_dir = Path(tempfile.gettempdir()) / "lcmspector"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "lcmspector.log"

    # backupCount=5: Keeps the current file + 5 previous copies (app.log, app.log.1, ... app.log.5)
    # maxBytes=10MB: Safety net. If a SINGLE session exceeds 10MB, it will rotate automatically 
    # to prevent disk filling even if the app never restarts.
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, mode='a', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )

    # Force a rollover on startup
    if log_file.exists() and log_file.stat().st_size > 0:
        file_handler.doRollover()

    # We set the ROOT level to INFO to avoid spam from third-party libraries (like urllib3, matplotlib, etc.)
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            file_handler,
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger("lc_inspector")
    logger.setLevel(logging.DEBUG) 
    
    logger.info("Logging configured. New session started.")
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
    main_font = fonts.get_main_font(13)
    app.setStyle("Fusion")
    app.setFont(main_font)

    # Show the main window
    view.show()

    # Start the event loop
    logger.info("Application initialized, starting event loop")

    # Ensure MS2 library exists locally
    if not ensure_ms2_library():
        if view.show_download_confirmation():
            view.show_download_progress_bar()

            # Setup worker and thread for download
            thread = QThread()
            worker = DownloadWorker()
            worker.moveToThread(thread)

            # Connect signals
            worker.progress.connect(view.update_download_progress_bar)
            worker.finished.connect(thread.quit)
            worker.finished.connect(view.hide_download_progress_bar)
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
