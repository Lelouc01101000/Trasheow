"""
settings_dialog.py

App settings window: capture sound toggle, optional Vision API label
detection, editable trash category list sent to Gemini, and camera
selection. Camera selection uses a dropdown populated from
enumerate_cameras() rather than a free-text index field, since a raw text
field cannot validate non-numerical input.
"""

import customtkinter as ctk

from core import config_manager
from core.camera_handler import enumerate_cameras

# outline-style button colors, explicit rather than relying on the theme
# default (which uses white text on a transparent fill - unreadable in
# light mode since it blends into the light background)
OUTLINE_BORDER_COLOR = ("#B9AFD6", "#4A4066")
OUTLINE_TEXT_COLOR = ("#2B2733", "#E8E4F0")
OUTLINE_HOVER_COLOR = ("#DCD6EA", "#2D2748")


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, config: dict, on_saved, active_camera_index=None):
        """
        master: parent window
        config: the live in-memory config dict shared with the main app
        on_saved: callback(new_camera_index) invoked after save, so the main
                  app can apply the sound/category/camera changes immediately
        active_camera_index: the index currently held open by the live
                  preview, if any. Passed through to enumerate_cameras() so
                  it isn't re-opened by a second, concurrent probe (which
                  can glitch the live preview's resolution on some backends).
        """
        super().__init__(master)
        self.title("Trasheow - Settings")
        self.geometry("480x440")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.config_data = config
        self.on_saved = on_saved
        self.active_camera_index = active_camera_index

        self._build_widgets()

    def _build_widgets(self):
        pad_x = 20

        # capture sound toggle
        self.sound_var = ctk.BooleanVar(value=self.config_data.get("sound_enabled", True))
        sound_check = ctk.CTkCheckBox(
            self, text="Play sound on capture", variable=self.sound_var
        )
        sound_check.pack(padx=pad_x, pady=(20, 12), anchor="w")

        # vision api toggle
        self.vision_var = ctk.BooleanVar(value=self.config_data.get("use_vision_api", True))
        vision_check = ctk.CTkCheckBox(
            self,
            text="Use Google Cloud Vision API (label detection before Gemini)",
            variable=self.vision_var,
        )
        vision_check.pack(padx=pad_x, pady=(0, 4), anchor="w")

        vision_note = ctk.CTkLabel(
            self,
            text="When disabled, Gemini classifies from the image alone and the\n"
                 "credentials json is not required.",
            font=("Arial", 11),
            text_color=("#5A5468", "#A79FC0"),
            justify="left",
        )
        vision_note.pack(padx=pad_x, pady=(0, 16), anchor="w")

        # trash categories
        categories_label = ctk.CTkLabel(self, text="Trash categories (comma separated)")
        categories_label.pack(padx=pad_x, anchor="w")

        current_categories = self.config_data.get(
            "trash_categories", config_manager.DEFAULT_TRASH_CATEGORIES
        )
        self.categories_entry = ctk.CTkEntry(self, width=420)
        self.categories_entry.insert(0, ", ".join(current_categories))
        self.categories_entry.pack(padx=pad_x, pady=(4, 16), fill="x")

        # camera selection
        camera_label = ctk.CTkLabel(self, text="Camera")
        camera_label.pack(padx=pad_x, anchor="w")

        detected = enumerate_cameras(skip_index=self.active_camera_index)
        if not detected:
            detected = [0]  # fall back so the dropdown is never empty

        self.camera_options = [f"Camera {i}" for i in detected]
        self.camera_indices = detected

        current_index = self.config_data.get("camera_index", 0)
        default_label = f"Camera {current_index}" if current_index in detected else self.camera_options[0]

        self.camera_menu_var = ctk.StringVar(value=default_label)
        camera_menu = ctk.CTkOptionMenu(
            self, values=self.camera_options, variable=self.camera_menu_var
        )
        camera_menu.pack(padx=pad_x, pady=(4, 20), anchor="w")

        # save / cancel
        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(padx=pad_x, pady=(10, 0), fill="x")

        save_btn = ctk.CTkButton(button_row, text="Save", command=self._save)
        save_btn.pack(side="right")

        cancel_btn = ctk.CTkButton(
            button_row,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            border_color=OUTLINE_BORDER_COLOR,
            text_color=OUTLINE_TEXT_COLOR,
            hover_color=OUTLINE_HOVER_COLOR,
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(0, 8))

    def _save(self):
        self.config_data["sound_enabled"] = self.sound_var.get()
        self.config_data["use_vision_api"] = self.vision_var.get()

        raw_categories = self.categories_entry.get()
        categories = [c.strip().lower() for c in raw_categories.split(",") if c.strip()]
        if categories:
            self.config_data["trash_categories"] = categories

        selected_label = self.camera_menu_var.get()
        selected_index = self.camera_indices[self.camera_options.index(selected_label)]
        camera_changed = selected_index != self.config_data.get("camera_index", 0)
        self.config_data["camera_index"] = selected_index

        config_manager.save_config(self.config_data)

        if self.on_saved:
            self.on_saved(selected_index if camera_changed else None)

        self.destroy()
