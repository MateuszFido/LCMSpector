"""
Resource handling utilities for Nuitka compatibility.

This module provides utilities for handling resources in both development
and Nuitka-compiled environments, following the migration plan specifications.
"""

from __future__ import annotations

import os
import sys
import ssl
import json
from pathlib import Path
import io
import logging
from urllib.request import urlopen
from zipfile import ZipFile, BadZipFile

from PySide6.QtCore import QObject, Signal

LOGGER = logging.getLogger(__name__)

# Public download of the MoNA Orbitrap MSP (as used in CI)
MSP_ZIP_URL = "https://polybox.ethz.ch/index.php/s/CrnWdgwX5canNxL/download"
MSP_FILENAME = "MoNA-export-All_LC-MS-MS_Orbitrap.msp"


def get_resources_dir() -> Path:
    """Returns the path to the resources directory."""
    return Path(__file__).resolve().parent.parent / "resources"


class DownloadWorker(QObject):
    """
    Worker to download the MS2 library in a separate thread.
    """

    progress = Signal(int)
    finished = Signal()
    error = Signal(str)

    def run(self):
        """
        Downloads and extracts the MS2 library MSP file from Polybox.
        """
        resources_dir = get_resources_dir()
        resources_dir.mkdir(parents=True, exist_ok=True)
        msp_path = resources_dir / MSP_FILENAME

        try:
            LOGGER.info("MS2 library not found; downloading from Polybox...")
            context = ssl._create_unverified_context()
            with urlopen(MSP_ZIP_URL, context=context, timeout=60) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                chunk_size = 8192
                data = b""
                bytes_read = 0
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    data += chunk
                    bytes_read += len(chunk)
                    if total_size > 0:
                        percent = int((bytes_read / total_size) * 100)
                        self.progress.emit(percent)

            with ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                candidate = next((n for n in names if n.endswith(".msp")), None)
                if not candidate:
                    msg = "Downloaded archive does not contain an .msp file."
                    LOGGER.error(msg)
                    self.error.emit(msg)
                    return
                zf.extract(member=candidate, path=str(resources_dir))
                extracted = resources_dir / candidate
                if extracted.name != MSP_FILENAME:
                    try:
                        extracted.rename(msp_path)
                    except OSError:
                        file_data = extracted.read_bytes()
                        msp_path.write_bytes(file_data)
                        try:
                            extracted.unlink()
                        except OSError:
                            pass

            if msp_path.exists():
                LOGGER.info("MS2 library downloaded to %s", msp_path)
                self.finished.emit()
            else:
                msg = "Failed to create MSP file after download."
                LOGGER.error(msg)
                self.error.emit(msg)

        except (TimeoutError, BadZipFile, OSError) as e:
            LOGGER.error("Failed to download/extract MS2 library: %s", e)
            self.error.emit(f"Failed to download/extract MS2 library: {e}")
        except Exception as e:
            LOGGER.error("Unexpected error retrieving MS2 library: %s", e)
            self.error.emit(f"Unexpected error retrieving MS2 library: {e}")


def ensure_ms2_library() -> bool:
    """
    Ensure the MS2 library MSP file exists under lcmspector/resources.

    Returns:
        True if the library exists, False otherwise.
    """
    resources_dir = get_resources_dir()
    msp_path = resources_dir / MSP_FILENAME
    return msp_path.exists() and msp_path.is_file()


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for development and Nuitka builds.

    Nuitka uses different resource location strategies than PyInstaller.

    Args:
        relative_path (str): Path relative to the application root

    Returns:
        str: Absolute path to the resource
    """
    # Check for Nuitka build (more reliable detection)
    is_nuitka = (
        getattr(sys, "frozen", False)
        or "main.bin" in sys.executable
        or "main.app" in sys.executable
        or (hasattr(sys, "argv") and sys.argv and "main.bin" in sys.argv[0])
    )

    if is_nuitka:
        # Nuitka standalone build
        if hasattr(sys, "_MEIPASS"):
            # Fallback for PyInstaller compatibility during transition
            base_path = sys._MEIPASS
        else:
            # Nuitka standard resource location - same directory as executable
            base_path = Path(sys.executable).parent
        return os.path.join(base_path, relative_path)
    else:
        # Development environment
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", relative_path
        )


def load_config():
    """Load configuration with Nuitka-compatible path resolution."""
    config_path = get_resource_path("config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)


def get_msp_library_path():
    """Get path to MS library file."""
    return get_resource_path("resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp")


def get_logo_path():
    """Get path to application logo."""
    return get_resource_path("ui/logo.png")


def get_icon_path():
    """Get path to application icon."""
    return get_resource_path("resources/icon.icns")


def verify_resources():
    """
    Verify that all critical resources are available.

    Returns:
        dict: Dictionary with resource names as keys and availability as values
    """
    resources = {
        "config.json": get_resource_path("config.json"),
        "logo.png": get_logo_path(),
        "icon.icns": get_icon_path(),
        "msp_library": get_msp_library_path(),
    }

    results = {}
    for name, path in resources.items():
        results[name] = {
            "path": path,
            "exists": os.path.exists(path),
            "size_mb": os.path.getsize(path) / (1024 * 1024)
            if os.path.exists(path)
            else 0,
        }

    return results


def get_application_info():
    """
    Get information about the current application environment.

    Returns:
        dict: Information about the execution environment
    """
    # Use the same Nuitka detection logic as get_resource_path
    is_nuitka = (
        getattr(sys, "frozen", False)
        or "main.bin" in sys.executable
        or "main.app" in sys.executable
        or (hasattr(sys, "argv") and sys.argv and "main.bin" in sys.argv[0])
    )

    return {
        "frozen": getattr(sys, "frozen", False),
        "nuitka": is_nuitka and not hasattr(sys, "_MEIPASS"),
        "pyinstaller": getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"),
        "executable": sys.executable,
        "argv0": sys.argv[0] if sys.argv else None,
        "base_path": Path(sys.executable).parent
        if is_nuitka
        else Path(__file__).parent.parent,
    }


# Support for command line testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test resource handling")
    parser.add_argument(
        "--test-resources", action="store_true", help="Test resource availability"
    )
    parser.add_argument(
        "--test-config", action="store_true", help="Test configuration loading"
    )
    parser.add_argument(
        "--app-info", action="store_true", help="Show application environment info"
    )

    args = parser.parse_args()

    if args.test_resources:
        print("Testing resource availability...")
        resources = verify_resources()
        for name, info in resources.items():
            status = "OK" if info["exists"] else "MISSING"
            size = (
                f" ({info['size_mb']:.1f}MB)"
                if info["exists"] and info["size_mb"] > 0
                else ""
            )
            print(f"{name}: {status}{size}")
            print(f"  Path: {info['path']}")

    if args.test_config:
        print("Testing configuration loading...")
        try:
            config = load_config()
            print("config.json: OK")
            print(f"  Found {len(config)} configuration sections")
        except Exception as e:
            print(f"config.json: ERROR - {e}")

    if args.app_info:
        print("Application environment information:")
        info = get_application_info()
        for key, value in info.items():
            print(f"  {key}: {value}")

