"""
paths.py

Resolves file paths correctly both when running from source and when frozen
into a standalone executable via PyInstaller. PyInstaller unpacks bundled
data files (assets, theme json, etc.) into a temporary sys._MEIPASS directory
at runtime, so asset lookups must branch on that instead of assuming a fixed
relative path.
"""

import os
import sys


def get_base_path() -> str:
    """
    Returns the directory that assets are bundled relative to.
    Frozen builds resolve to the PyInstaller temp extraction dir;
    source runs resolve to the project root (one level above core/).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*parts) -> str:
    """Builds an absolute path inside the assets/ directory."""
    return os.path.join(get_base_path(), "assets", *parts)


def theme_path() -> str:
    """Absolute path to the custom purple color theme json for customtkinter."""
    return os.path.join(get_base_path(), "gui", "purple_theme.json")
