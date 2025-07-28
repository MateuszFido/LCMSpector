import sys
import os
import importlib.machinery
import importlib.util

# Locate the compiled extension
extension_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'target', 'release'))
dylib_path = os.path.join(extension_dir, 'liblcmspector_backend.dylib')

if not os.path.exists(dylib_path):
    print(f"Warning: Extension file not found at {dylib_path}")
    # Try looking in alternative locations
    possible_locations = [
        os.path.join(os.path.dirname(__file__), '..', 'target', 'debug', 'liblcmspector_backend.dylib'),
        os.path.join(os.path.dirname(__file__), 'liblcmspector_backend.so'),
        os.path.join(os.path.dirname(__file__), 'lcmspector_backend.so'),
    ]
    
    for loc in possible_locations:
        if os.path.exists(loc):
            dylib_path = loc
            print(f"Found extension at alternative location: {dylib_path}")
            break

try:
    # Load the dynamic library directly
    loader = importlib.machinery.ExtensionFileLoader('lcmspector_backend', dylib_path)
    spec = importlib.util.spec_from_loader('lcmspector_backend', loader)
    lcmspector_backend = importlib.util.module_from_spec(spec)
    loader.exec_module(lcmspector_backend)
    
    # Import all attributes from the module
    from_list = dir(lcmspector_backend)
    for name in from_list:
        if not name.startswith('__'):
            globals()[name] = getattr(lcmspector_backend, name)
    
    print(f"Successfully loaded lcmspector_backend from {dylib_path}")
except Exception as e:
    print(f"Error loading lcmspector_backend: {e}")
    print(f"Attempted to load from: {dylib_path}")
    print(f"Current sys.path: {sys.path}")
