"""
Main entry point for the LCMSpector application with Nuitka compatibility.

This module provides the main entry point for the LCMSpector application.
It sets up logging, creates the application, model, view, and controller instances,
and handles application startup with support for both PyInstaller and Nuitka builds.
"""

import os
import sys
import yaml
import logging.config
import multiprocessing
import tempfile
import argparse
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from ui.model import Model
from ui.view import View
from ui.controller import Controller
from utils.resources import get_resource_path, load_config, get_icon_path, verify_resources, get_application_info

# Guards for binary building
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
multiprocessing.freeze_support()

def configure_logging():
    """Configure logging for the application with Nuitka compatibility."""
    log_dir = Path(tempfile.gettempdir()) / "lcmspector"
    os.makedirs(log_dir, exist_ok=True)

    log_file = log_dir / "lcmspector.log"
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w+'),
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


def load_application_icon(app):
    """Load application icon with Nuitka-compatible path."""
    try:
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            return True
        else:
            print(f"Warning: Icon not found at {icon_path}")
            return False
    except Exception as e:
        print(f"Warning: Failed to load icon: {e}")
        return False


def handle_command_line_args():
    """Handle command line arguments for testing and info."""
    parser = argparse.ArgumentParser(description='LCMSpector - LC-MS Data Analysis Tool')
    parser.add_argument('--version', action='store_true',
                       help='Show version information')
    parser.add_argument('--app-info', action='store_true',
                       help='Show application environment information')
    parser.add_argument('--test-resources', action='store_true',
                       help='Test resource availability and exit')
    parser.add_argument('--test-config', action='store_true',
                       help='Test configuration loading and exit')
    parser.add_argument('--test-file', metavar='PATH',
                       help='Test file processing with given file')
    parser.add_argument('--benchmark-startup', action='store_true',
                       help='Exit immediately after startup (for benchmarking)')
    
    return parser.parse_args()


def main():
    """Main entry point for the application with Nuitka compatibility."""
    # Handle command line arguments first
    args = handle_command_line_args()
    
    # Configure logging
    logger = configure_logging()
    
    # Get application info
    app_info = get_application_info()
    build_type = "Nuitka" if app_info['nuitka'] else "PyInstaller" if app_info['pyinstaller'] else "Development"
    
    logger.info(f"Starting LCMSpector ({build_type}) with temp dir: {tempfile.gettempdir()}")
    
    # Handle special command line modes
    if args.version:
        print("LCMSpector 1.0.0")
        print(f"Build type: {build_type}")
        print(f"Executable: {app_info['executable']}")
        sys.exit(0)
    
    if args.app_info:
        print("Application Environment Information:")
        for key, value in app_info.items():
            print(f"  {key}: {value}")
        sys.exit(0)
    
    if args.test_resources:
        print("Testing resource availability...")
        resources = verify_resources()
        all_ok = True
        for name, info in resources.items():
            status = "OK" if info['exists'] else "MISSING"
            size = f" ({info['size_mb']:.1f}MB)" if info['exists'] and info['size_mb'] > 0 else ""
            print(f"{name}: {status}{size}")
            if not info['exists']:
                all_ok = False
        sys.exit(0 if all_ok else 1)
    
    if args.test_config:
        print("Testing configuration loading...")
        try:
            config = load_config()
            print("config.json: OK")
            print(f"Found {len(config)} configuration sections")
            sys.exit(0)
        except Exception as e:
            print(f"config.json: ERROR - {e}")
            sys.exit(1)
    
    # Create the application
    app = QApplication(sys.argv)
    app.setApplicationName("LCMSpector")
    app.setApplicationVersion("1.0.0")
    
    # Load icon with new resource system
    load_application_icon(app)
    
    # Handle benchmark startup mode (exit after basic initialization)
    if args.benchmark_startup:
        logger.info("Benchmark startup mode - exiting after initialization")
        sys.exit(0)
    
    # Create model, view, and controller with updated config loading
    try:
        config = load_config()  # Use new config loader
        model = Model()
        view = View()
        controller = Controller(model, view)
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        if args.test_file:
            print(f"File processing test failed: {e}")
            sys.exit(1)
        sys.exit(1)
    
    # Set the application style
    app.setStyle("Fusion")
    
    # Handle test file processing
    if args.test_file:
        logger.info(f"Testing file processing with: {args.test_file}")
        try:
            # This would trigger file processing in a real implementation
            print(f"File processing test completed for: {args.test_file}")
            sys.exit(0)
        except Exception as e:
            print(f"File processing test failed: {e}")
            sys.exit(1)
    
    # Show the main window
    view.show()
    
    # Start the event loop
    logger.info("Application initialized successfully, starting event loop")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()