"""
credentials_dialog.py

Standalone window for entering the Gemini API key and the Google Cloud
credentials json path. Kept separate from the general Settings window per
spec. Both fields are masked with "*" by default (password-entry style),
each with its own show/hide toggle, and values persist to config.json via
config_manager so they survive an app restart.
"""

import tkinter.filedialog as filedialog

import customtkinter as ctk

from core import config_manager

# outline-style button colors, explicit rather than relying on the theme
# default (which uses white text on a transparent fill - unreadable in
# light mode since it blends into the light background)
OUTLINE_BORDER_COLOR = ("#B9AFD6", "#4A4066")
OUTLINE_TEXT_COLOR = ("#2B2733", "#E8E4F0")
OUTLINE_HOVER_COLOR = ("#DCD6EA", "#2D2748")

TUTORIAL_TEXT = (
    "Credentials are stored locally and are required to run waste detection.\n"
    "The app will still open and the camera preview will still work without them.\n"
    "For Gemini API Key: Go to google AI studio -> Dashboard -> API Keys ->\n"
    "Create API key -> Create key -> copy API Key.\n"
    "For JSON file: IAM->Grant access->Role->Vertex AI Custom Code Service Agent role->Save->Close->\n"
    "Service Accounts->create service account->Permission Role->Vertex AI Custom Code Service Agent role->\n"
    "Click on service account email->Keys->Add key->Create new key->Json->Create\n"
    "Lastly for JSON enable Vision API: APIs and services -> Enable APIs and services ->\n"
    "Enable APIs and services -> Cloud Vision API -> Enable\n"
    "\n"
    "Note: the JSON credentials file is only required if Vision API label\n"
    "detection is turned on in Settings. If it is turned off, this app only\n"
    "needs the Gemini API key and the JSON field can be left empty or invalid."
)


class CredentialsDialog(ctk.CTkToplevel):
    def __init__(self, master, config: dict, on_saved):
        """
        master: parent window
        config: the live in-memory config dict shared with the main app
        on_saved: callback invoked after a successful save, so the main app
                  can refresh its "credentials configured" banner state
        """
        super().__init__(master)
        self.title("Trasheow - API Credentials")
        self.geometry("560x560")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.config_data = config
        self.on_saved = on_saved

        self._build_widgets()

    def _build_widgets(self):
        pad_x = 20

        info_box = ctk.CTkTextbox(self, width=510, height=190, wrap="word")
        info_box.insert("1.0", TUTORIAL_TEXT)
        info_box.configure(state="disabled")
        info_box.pack(padx=pad_x, pady=(18, 12), fill="x")

        # gemini api key row
        key_label = ctk.CTkLabel(self, text="Gemini API Key")
        key_label.pack(padx=pad_x, anchor="w")

        key_row = ctk.CTkFrame(self, fg_color="transparent")
        key_row.pack(padx=pad_x, pady=(2, 12), fill="x")

        self.key_entry = ctk.CTkEntry(key_row, show="*", width=340)
        self.key_entry.insert(0, self.config_data.get("gemini_api_key", ""))
        self.key_entry.pack(side="left", fill="x", expand=True)

        self.key_toggle_btn = ctk.CTkButton(
            key_row, text="Show", width=60, command=self._toggle_key_visibility
        )
        self.key_toggle_btn.pack(side="left", padx=(8, 0))

        # google credentials json path row
        path_label = ctk.CTkLabel(self, text="Google Cloud Credentials JSON Path (only needed if Vision API is enabled)")
        path_label.pack(padx=pad_x, anchor="w")

        path_row = ctk.CTkFrame(self, fg_color="transparent")
        path_row.pack(padx=pad_x, pady=(2, 12), fill="x")

        self.path_entry = ctk.CTkEntry(path_row, show="*", width=250)
        self.path_entry.insert(0, self.config_data.get("google_credentials_path", ""))
        self.path_entry.pack(side="left", fill="x", expand=True)

        self.path_toggle_btn = ctk.CTkButton(
            path_row, text="Show", width=60, command=self._toggle_path_visibility
        )
        self.path_toggle_btn.pack(side="left", padx=(8, 0))

        browse_btn = ctk.CTkButton(path_row, text="Browse", width=70, command=self._browse_json)
        browse_btn.pack(side="left", padx=(8, 0))

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

    def _toggle_key_visibility(self):
        if self.key_entry.cget("show") == "*":
            self.key_entry.configure(show="")
            self.key_toggle_btn.configure(text="Hide")
        else:
            self.key_entry.configure(show="*")
            self.key_toggle_btn.configure(text="Show")

    def _toggle_path_visibility(self):
        if self.path_entry.cget("show") == "*":
            self.path_entry.configure(show="")
            self.path_toggle_btn.configure(text="Hide")
        else:
            self.path_entry.configure(show="*")
            self.path_toggle_btn.configure(text="Show")

    def _browse_json(self):
        selected = filedialog.askopenfilename(
            title="Select Google Cloud credentials json file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, selected)

    def _save(self):
        self.config_data["gemini_api_key"] = self.key_entry.get().strip()
        self.config_data["google_credentials_path"] = self.path_entry.get().strip()
        config_manager.save_config(self.config_data)

        if self.on_saved:
            self.on_saved()

        self.destroy()
