"""
Resource handling utilities for Nuitka compatibility.

This module provides utilities for handling resources in both development
and Nuitka-compiled environments, following the migration plan specifications.
"""

import os
import sys
import json
from pathlib import Path


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for development and Nuitka builds.
    
    Nuitka uses different resource location strategies than PyInstaller.
    
    Args:
        relative_path (str): Path relative to the application root
        
    Returns:
        str: Absolute path to the resource
    """
    if getattr(sys, 'frozen', False):
        # Nuitka standalone build
        if hasattr(sys, '_MEIPASS'):
            # Fallback for PyInstaller compatibility during transition
            base_path = sys._MEIPASS
        else:
            # Nuitka standard resource location
            base_path = Path(sys.executable).parent
        return os.path.join(base_path, relative_path)
    else:
        # Development environment
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', relative_path)


def load_config():
    """Load configuration with Nuitka-compatible path resolution."""
    config_path = get_resource_path('config.json')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def get_msp_library_path():
    """Get path to MS library file."""
    return get_resource_path('resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp')


def get_logo_path():
    """Get path to application logo."""
    return get_resource_path('ui/logo.png')


def get_icon_path():
    """Get path to application icon."""
    return get_resource_path('resources/icon.icns')


def verify_resources():
    """
    Verify that all critical resources are available.
    
    Returns:
        dict: Dictionary with resource names as keys and availability as values
    """
    resources = {
        'config.json': get_resource_path('config.json'),
        'logo.png': get_logo_path(),
        'icon.icns': get_icon_path(),
        'msp_library': get_msp_library_path()
    }
    
    results = {}
    for name, path in resources.items():
        results[name] = {
            'path': path,
            'exists': os.path.exists(path),
            'size_mb': os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0
        }
    
    return results


def get_application_info():
    """
    Get information about the current application environment.
    
    Returns:
        dict: Information about the execution environment
    """
    return {
        'frozen': getattr(sys, 'frozen', False),
        'nuitka': getattr(sys, 'frozen', False) and not hasattr(sys, '_MEIPASS'),
        'pyinstaller': getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'),
        'executable': sys.executable,
        'argv0': sys.argv[0] if sys.argv else None,
        'base_path': Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
    }


# Support for command line testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test resource handling')
    parser.add_argument('--test-resources', action='store_true',
                       help='Test resource availability')
    parser.add_argument('--test-config', action='store_true',
                       help='Test configuration loading')
    parser.add_argument('--app-info', action='store_true',
                       help='Show application environment info')
    
    args = parser.parse_args()
    
    if args.test_resources:
        print("Testing resource availability...")
        resources = verify_resources()
        for name, info in resources.items():
            status = "OK" if info['exists'] else "MISSING"
            size = f" ({info['size_mb']:.1f}MB)" if info['exists'] and info['size_mb'] > 0 else ""
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