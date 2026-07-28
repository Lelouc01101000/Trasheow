"""
sound_manager.py

Plays the capture confirmation sound using pygame's mixer module. pygame is
used instead of the stdlib alone because mp3 playback support across
Windows/macOS/Linux is inconsistent otherwise.
"""

import os

import pygame


class SoundManager:
    """Lazily initializes the pygame mixer and plays the capture sound on demand."""

    def __init__(self, sound_path: str):
        self.sound_path = sound_path
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            pygame.mixer.init()
            self._initialized = True

    def play_capture_sound(self, enabled: bool):
        """Plays capture.mp3 if enabled and the file is present; silently no-ops otherwise."""
        if not enabled:
            return

        if not os.path.isfile(self.sound_path):
            print(f"capture sound not found at: {self.sound_path}")
            return

        try:
            self._ensure_init()
            sound = pygame.mixer.Sound(self.sound_path)
            sound.play()
        except pygame.error as e:
            print(f"sound playback error: {e}")
