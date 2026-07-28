"""
camera_handler.py

Cross-platform camera interface built on OpenCV's VideoCapture, replacing the
Raspberry Pi specific rpicam-jpeg subprocess call. OpenCV selects the correct
backend automatically per OS (V4L2 on Linux, DirectShow/MSMF on Windows,
AVFoundation on macOS), so no platform branching is required here.
"""

import contextlib
import os
import sys

import cv2

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480


@contextlib.contextmanager
def _suppress_native_stderr():
    """
    Temporarily redirects the OS-level stderr file descriptor to devnull.

    Some OpenCV camera backends (notably macOS AVFoundation) print
    "out device of bound" / "camera failed to properly initialize" directly
    to stderr from native (non-Python) code when a probed index doesn't
    exist. That bypasses OPENCV_LOG_LEVEL and cv2.setLogLevel entirely, so
    an OS-level file descriptor redirect is the only way to actually
    silence it. Restores the original stderr fd afterwards no matter what.
    """
    stderr_fd = sys.stderr.fileno()
    saved_fd = os.dup(stderr_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, stderr_fd)
        yield
    finally:
        os.dup2(saved_fd, stderr_fd)
        os.close(devnull_fd)
        os.close(saved_fd)


class CameraHandler:
    """Owns a single OpenCV VideoCapture device and exposes preview/still access."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.capture = None

    def open(self) -> bool:
        """Opens the configured camera index. Returns True on success."""
        self.release()
        with _suppress_native_stderr():
            self.capture = cv2.VideoCapture(self.camera_index)
            opened = self.capture.isOpened()

        if not opened:
            self.capture = None
            return False

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_HEIGHT)
        return True

    def is_open(self) -> bool:
        return self.capture is not None and self.capture.isOpened()

    def read_frame_rgb(self):
        """
        Grabs one frame for the live preview loop, converted to RGB
        (OpenCV captures in BGR by default). Returns None on failure.
        """
        if not self.is_open():
            return None

        ok, frame = self.capture.read()
        if not ok:
            return None

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def capture_still_bgr(self):
        """
        Grabs a single fresh frame in raw BGR form for saving/classification.
        Kept separate from read_frame_rgb so callers writing to disk with
        cv2.imwrite (which expects BGR) don't need to convert back.
        """
        if not self.is_open():
            raise RuntimeError("camera is not open")

        ok, frame = self.capture.read()
        if not ok:
            raise RuntimeError("failed to read frame from camera")

        return frame

    def release(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None


def enumerate_cameras(max_index: int = 5, skip_index: int = None) -> list:
    """
    Probes camera indices 0..max_index-1 and returns the ones that open
    successfully. Used to populate a selection dropdown in Settings instead
    of accepting a raw text index, which cannot validate non-numerical input.

    skip_index: an index already known to be open and in active use
    elsewhere (the live preview camera). It is trusted and appended
    without a second probe, since opening a concurrent VideoCapture
    session on a device that's already streaming can cause some backends
    (e.g. macOS AVFoundation) to renegotiate resolution and glitch the
    existing preview.

    Stops probing at the first index (other than skip_index) that fails
    to open, since camera indices are contiguous on essentially every OS/
    driver - this avoids printing native "device out of bound" warnings
    for a long range of indices that obviously don't exist.
    """
    available = []
    with _suppress_native_stderr():
        for index in range(max_index):
            if index == skip_index:
                available.append(index)
                continue

            cap = cv2.VideoCapture(index)
            opened = cap.isOpened()
            cap.release()

            if opened:
                available.append(index)
            else:
                break

    return available
