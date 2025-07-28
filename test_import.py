#!/usr/bin/env python
"""
Test script to verify the lcmspector_backend import is working correctly.
"""
import os
import sys

# Add the parent directory to sys.path to make the lcmspector package importable
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    print("Attempting to import lcmspector...")
    import lcmspector
    print("Successfully imported lcmspector")
    
    print("\nChecking if lcmspector_backend was loaded...")
    if hasattr(lcmspector, 'lcmspector_backend'):
        print("lcmspector_backend is available in the lcmspector namespace")
    else:
        print("lcmspector_backend is NOT available in the lcmspector namespace")
    
    print("\nTrying to access the process_files_in_parallel function...")
    if hasattr(lcmspector, 'process_files_in_parallel'):
        print("process_files_in_parallel function is available")
        print(f"Function signature: {lcmspector.process_files_in_parallel}")
    else:
        print("process_files_in_parallel function is NOT available")
    
    print("\nChecking the module's directory...")
    for item in dir(lcmspector):
        if not item.startswith('__'):
            print(f"- {item}")
    
except Exception as e:
    print(f"Error during import test: {e}")
    import traceback
    traceback.print_exc()
