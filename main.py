"""
main.py

Entry point for Trasheow. Launches the customtkinter GUI application.
"""

import os
import sys

# ensure the project root is importable whether run from source or bundled
# via pyinstaller, since a frozen exe's working directory can differ
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, PROJECT_ROOT)

from gui.app import TrasheowApp  # noqa: E402  (import after path setup)

if __name__ == "__main__":
    app = TrasheowApp()
    app.mainloop()
