"""
Push Assistant — entry point.

Usage
-----
    python run.py          # shows console (good for debugging)
    pythonw run.py         # hides console (clean tray-only experience)
"""
import sys
import os

# Make all package imports resolve from the project root
# regardless of the working directory used to launch the script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assistant.main import main

if __name__ == "__main__":
    main()
