#!/usr/bin/env python
"""Launch LCMSpector with hot reload enabled.

Usage:
    uv run python scripts/hot_reload.py

This enables live code reloading during development. When you save changes
to any .py file in the lcmspector/ directory, the changes apply immediately
without restarting the application.

Works well for:
- Function/method body changes
- Adding new functions/methods
- Changing default argument values

May require restart for:
- Class structure changes (new attributes)
- Import statement changes
- Signal/slot connection changes (wired at __init__ time)
"""
import os
import sys
from pathlib import Path

# The app uses relative imports (from ui.model import Model), so we need
# to add lcmspector/ to sys.path, not the project root
project_root = Path(__file__).parent.parent
lcmspector_dir = project_root / "lcmspector"
sys.path.insert(0, str(lcmspector_dir))

# Also change working directory so resource paths resolve correctly
os.chdir(lcmspector_dir)

if __name__ == "__main__":
    # Enable hot reload watching
    import jurigged

    jurigged.watch(str(lcmspector_dir))

    # Import and run - uses relative imports from lcmspector/
    from main import main

    main()
