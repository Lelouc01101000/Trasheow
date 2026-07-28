"""
app.py

Main Trasheow application window built with customtkinter. Responsibilities:
  - live camera preview loop
  - capture / retake toggle
  - save captured photo to disk
  - run Gemini/Vision classification on a background thread
  - light/dark appearance switch (dark + purple by default)
  - entry points to the Credentials and Settings dialogs
"""

import os
import shutil
import tempfile
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox

import customtkinter as ctk
from PIL import Image
import cv2

from core import config_manager
from core import paths
from core.camera_handler import CameraHandler
from core.sound_manager import SoundManager
from core.vision_ai import classify_trash, CredentialsMissingError

PREVIEW_DISPLAY_SIZE = (480, 360)
PREVIEW_INTERVAL_MS = 30


class TrasheowApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config_data = config_manager.load_config()

        ctk.set_default_color_theme(paths.theme_path())
        ctk.set_appearance_mode(self.config_data.get("appearance_mode", "Dark"))

        self.title("Trasheow")
        self.geometry("760x700")
        self.minsize(680, 640)

        self._set_window_icon()

        self.camera = CameraHandler(self.config_data.get("camera_index", 0))
        self.camera_available = False  # set once _init_camera runs, see below

        sound_path = paths.asset_path("capture.mp3")
        self.sound_manager = SoundManager(sound_path)

        self.temp_dir = tempfile.mkdtemp(prefix="trasheow_")
        self.current_image_path = None

        self.is_previewing = True
        self.preview_job = None
        self.detecting = False

        self._build_widgets()
        self._refresh_credentials_banner()

        self.preview_label.configure(image=None, text="Starting camera...")
        self.capture_button.configure(state="disabled")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Defer the actual camera open until after mainloop() is running,
        # instead of opening it synchronously here in __init__. On macOS,
        # the first-ever camera access triggers a TCC permission prompt;
        # completing that handshake requires the app's run loop to already
        # be pumping events. Opening the camera before mainloop() starts
        # races that handshake and crashes the process right after the
        # user grants access (subsequent launches don't hit this because
        # macOS has already cached the decision and skips the live
        # negotiation). self.after() callbacks only fire once the event
        # loop is actually running, which is exactly the delay needed here.
        self.after(50, self._init_camera)

    def _init_camera(self):
        self.camera_available = self.camera.open()

        if self.camera_available:
            self.is_previewing = True
            self.capture_button.configure(state="normal")
            self._schedule_preview()
        else:
            self.preview_label.configure(image=None, text="No camera detected")
            self.capture_button.configure(state="disabled")

    # ---------------------------------------------------------------- setup

    def _set_window_icon(self):
        """Best-effort window icon load; never fatal if the asset is missing."""
        logo_path = paths.asset_path("trasheow_logo.png")
        if not os.path.isfile(logo_path):
            return
        try:
            from PIL import ImageTk
            icon_image = Image.open(logo_path)
            # iconphoto requires a raw Tk PhotoImage, not a CTkImage
            self._tk_icon = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self._tk_icon)
        except Exception as e:
            print(f"could not set window icon: {e}")

    def _build_widgets(self):
        # top bar: title + credentials/settings/appearance controls
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(18, 6))

        title_label = ctk.CTkLabel(top_bar, text="Trasheow", font=("Arial", 24, "bold"))
        title_label.pack(side="left")

        self.appearance_switch = ctk.CTkSegmentedButton(
            top_bar, values=["Light", "Dark"], command=self._on_appearance_change
        )
        self.appearance_switch.set(self.config_data.get("appearance_mode", "Dark"))
        self.appearance_switch.pack(side="right")

        settings_btn = ctk.CTkButton(top_bar, text="Settings", width=90, command=self._open_settings)
        settings_btn.pack(side="right", padx=(0, 10))

        credentials_btn = ctk.CTkButton(top_bar, text="Credentials", width=100, command=self._open_credentials)
        credentials_btn.pack(side="right", padx=(0, 10))

        # credentials banner (hidden once configured)
        self.credentials_banner = ctk.CTkLabel(
            self, text="", text_color=("#8A4B00", "#FFB454"), font=("Arial", 12, "bold")
        )
        self.credentials_banner.pack(pady=(0, 4))

        # camera preview frame
        preview_frame = ctk.CTkFrame(self, width=PREVIEW_DISPLAY_SIZE[0], height=PREVIEW_DISPLAY_SIZE[1])
        preview_frame.pack(pady=10)
        preview_frame.pack_propagate(False)

        self.preview_label = ctk.CTkLabel(preview_frame, text="Starting camera...")
        self.preview_label.pack(expand=True, fill="both")

        # status
        self.status_label = ctk.CTkLabel(self, text="Ready", font=("Arial", 13))
        self.status_label.pack(pady=(10, 6))

        # buttons row
        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(pady=10)

        self.capture_button = ctk.CTkButton(
            button_row, text="Capture", font=("Arial", 14), width=150, command=self._on_capture_button
        )
        self.capture_button.grid(row=0, column=0, padx=8)

        self.save_button = ctk.CTkButton(
            button_row, text="Save Photo", font=("Arial", 14), width=150,
            command=self._save_photo, state="disabled",
        )
        self.save_button.grid(row=0, column=1, padx=8)

        self.detect_button = ctk.CTkButton(
            button_row, text="Detect Waste", font=("Arial", 14), width=150,
            command=self._on_detect_button, state="disabled",
        )
        self.detect_button.grid(row=0, column=2, padx=8)

        # results
        self.result_label = ctk.CTkLabel(self, text="Waste type: -", font=("Arial", 16, "bold"))
        self.result_label.pack(pady=(20, 4))

        self.confidence_label = ctk.CTkLabel(self, text="Confidence: -", font=("Arial", 14))
        self.confidence_label.pack(pady=4)

    # ------------------------------------------------------------- preview

    def _schedule_preview(self):
        self.preview_job = self.after(PREVIEW_INTERVAL_MS, self._update_preview)

    def _update_preview(self):
        if not self.is_previewing or not self.camera_available:
            return

        frame_rgb = self.camera.read_frame_rgb()
        if frame_rgb is not None:
            pil_image = Image.fromarray(frame_rgb)
            ctk_image = ctk.CTkImage(
                light_image=pil_image, dark_image=pil_image, size=PREVIEW_DISPLAY_SIZE
            )
            self.preview_label.configure(image=ctk_image, text="")
            # keep a reference so the image isn't garbage collected between ticks
            self.preview_label.image = ctk_image

        self._schedule_preview()

    # -------------------------------------------------------- capture/save

    def _on_capture_button(self):
        if self.is_previewing:
            self._capture_image()
        else:
            self._resume_preview()

    def _capture_image(self):
        if not self.camera_available:
            return

        try:
            frame_bgr = self.camera.capture_still_bgr()
        except RuntimeError as e:
            self.status_label.configure(text=f"Capture failed: {e}")
            return

        self.is_previewing = False

        self.current_image_path = os.path.join(self.temp_dir, "captured.jpg")
        cv2.imwrite(self.current_image_path, frame_bgr)

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=PREVIEW_DISPLAY_SIZE)
        self.preview_label.configure(image=ctk_image, text="")
        self.preview_label.image = ctk_image

        self.sound_manager.play_capture_sound(self.config_data.get("sound_enabled", True))

        self.capture_button.configure(text="Retake")
        self.save_button.configure(state="normal")
        self.detect_button.configure(state="normal")

        self.result_label.configure(text="Waste type: -")
        self.confidence_label.configure(text="Confidence: -")
        self.status_label.configure(text="Image captured")

    def _resume_preview(self):
        self.is_previewing = True
        self.capture_button.configure(text="Capture")
        self.save_button.configure(state="disabled")
        self.detect_button.configure(state="disabled")
        self.status_label.configure(text="Ready")
        self._schedule_preview()

    def _save_photo(self):
        if not self.current_image_path or not os.path.isfile(self.current_image_path):
            self.status_label.configure(text="No photo to save yet")
            return

        destination = filedialog.asksaveasfilename(
            title="Save photo",
            defaultextension=".jpg",
            filetypes=[("JPEG image", "*.jpg"), ("All files", "*.*")],
        )
        if not destination:
            return

        try:
            shutil.copyfile(self.current_image_path, destination)
            self.status_label.configure(text=f"Saved to {destination}")
        except OSError as e:
            self.status_label.configure(text=f"Save failed: {e}")

    # ------------------------------------------------------------- detect

    def _on_detect_button(self):
        if self.detecting:
            return

        if not self.current_image_path:
            self.status_label.configure(text="Capture an image first")
            return

        if not config_manager.has_credentials(self.config_data):
            if self.config_data.get("use_vision_api", True):
                message = (
                    "Please configure your Gemini API key and Google Cloud credentials "
                    "json path from the Credentials button before running detection."
                )
            else:
                message = (
                    "Please configure your Gemini API key from the Credentials button "
                    "before running detection."
                )
            messagebox.showinfo("Credentials required", message)
            return

        self.detecting = True
        self.detect_button.configure(state="disabled")
        self.status_label.configure(text="Analyzing waste...")

        image_path = self.current_image_path
        api_key = self.config_data.get("gemini_api_key", "")
        credentials_path = self.config_data.get("google_credentials_path", "")
        categories = self.config_data.get("trash_categories", config_manager.DEFAULT_TRASH_CATEGORIES)
        use_vision_api = self.config_data.get("use_vision_api", True)

        thread = threading.Thread(
            target=self._run_detection,
            args=(image_path, api_key, credentials_path, categories, use_vision_api),
            daemon=True,
        )
        thread.start()

    def _run_detection(self, image_path, api_key, credentials_path, categories, use_vision_api):
        try:
            ai_response = classify_trash(
                image_path, api_key, credentials_path, categories, use_vision_api
            )
        except CredentialsMissingError as e:
            # capture the message into a plain variable before the lambda:
            # Python clears the "as e" binding once the except block exits,
            # so the lambda would otherwise see an unbound name when it
            # actually runs later via self.after()
            message = str(e)
            self.after(0, lambda: self._on_detection_done("Not Configured", message, error=True))
            return
        except Exception as e:
            message = str(e)
            self.after(0, lambda: self._on_detection_done("Error", message, error=True))
            return

        self.after(0, lambda: self._on_detection_result(ai_response))

    def _on_detection_result(self, ai_response: str):
        response_parts = ai_response.split()

        if response_parts and response_parts[0] == "error_quota":
            waste_type = "Rate Limited"
            confidence = "Retry Later"
        elif ai_response == "Can Not Identify":
            waste_type = "Can Not Identify"
            confidence = "N/A"
        elif len(response_parts) == 2:
            waste_type = response_parts[0].capitalize()
            confidence = response_parts[1]
        else:
            waste_type = "Can Not Identify"
            confidence = "N/A"

        self._on_detection_done(waste_type, confidence)

    def _on_detection_done(self, waste_type, confidence, error=False):
        self.result_label.configure(text=f"Waste type: {waste_type}")
        self.confidence_label.configure(text=f"Confidence: {confidence}")
        self.status_label.configure(text="Detection failed" if error else "Done")
        self.detecting = False
        self.detect_button.configure(state="normal")

    # --------------------------------------------------------- dialogs

    def _open_credentials(self):
        from gui.credentials_dialog import CredentialsDialog
        CredentialsDialog(self, self.config_data, self._refresh_credentials_banner)

    def _open_settings(self):
        from gui.settings_dialog import SettingsDialog
        active_index = self.camera.camera_index if self.camera_available else None
        SettingsDialog(self, self.config_data, self._on_settings_saved, active_index)

    def _on_settings_saved(self, new_camera_index):
        if new_camera_index is not None:
            self._switch_camera(new_camera_index)
        self._refresh_credentials_banner()

    def _switch_camera(self, new_index: int):
        self.is_previewing = False
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
            self.preview_job = None

        self.camera.camera_index = new_index
        self.camera_available = self.camera.open()

        if self.camera_available:
            self.is_previewing = True
            self.capture_button.configure(state="normal", text="Capture")
            self._schedule_preview()
        else:
            self.preview_label.configure(image=None, text="No camera detected")
            self.capture_button.configure(state="disabled")

    def _refresh_credentials_banner(self):
        if config_manager.has_credentials(self.config_data):
            self.credentials_banner.configure(text="")
        else:
            self.credentials_banner.configure(
                text="Credentials not configured - click Credentials above to enable waste detection"
            )

    def _on_appearance_change(self, mode: str):
        ctk.set_appearance_mode(mode)
        self.config_data["appearance_mode"] = mode
        config_manager.save_config(self.config_data)

    # ------------------------------------------------------------- close

    def _on_close(self):
        self.is_previewing = False
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
        self.camera.release()
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except OSError:
            pass
        self.destroy()
