"""
config_manager.py

Handles persistent storage of user configuration (API credentials and app
settings) in a platform-appropriate user config directory, so the config
survives app restarts and works the same way whether run from source or
as a frozen executable.

NOTE ON SECURITY: the Gemini API key is stored in plain text json on disk.
This is a deliberate tradeoff for a simple, dependency-free desktop tool and
does not use OS keychain integration. Do not treat this as secure storage
for production or shared-machine use.
"""

import json
import os
import sys
from pathlib import Path

APP_NAME = "Trasheow"
CONFIG_FILENAME = "config.json"

DEFAULT_TRASH_CATEGORIES = [
    "plastic", "metallic", "organic", "paper",
    "glass", "e-waste", "wood", "textile", "other",
]

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "google_credentials_path": "",
    "sound_enabled": True,
    "appearance_mode": "Dark",
    "trash_categories": DEFAULT_TRASH_CATEGORIES,
    "camera_index": 0,
    "use_vision_api": True,
}


def get_config_dir() -> Path:
    """
    Returns the OS-appropriate config directory, creating it if needed.
    Config is intentionally kept outside the executable's own directory so
    it persists correctly across PyInstaller-built app updates/reinstalls.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    config_dir = base / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


def load_config() -> dict:
    """
    Loads config from disk, merging over defaults so keys added in later
    app versions don't break older saved config files.
    """
    config = DEFAULT_CONFIG.copy()
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, OSError) as e:
            print(f"config load error, falling back to defaults: {e}")

    return config


def save_config(config: dict) -> None:
    """Writes the full config dict to disk as json."""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"config save error: {e}")


def has_credentials(config: dict) -> bool:
    """
    True if the currently selected mode has everything it needs:
      - Gemini API key is always required.
      - Google Cloud credentials path is only required when use_vision_api
        is True; when Vision API is disabled, the json path is irrelevant
        and it's fine for it to be empty or invalid.
    """
    if not config.get("gemini_api_key"):
        return False

    if config.get("use_vision_api", True):
        return bool(config.get("google_credentials_path"))

    return True
