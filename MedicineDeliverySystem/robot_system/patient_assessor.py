import os
import sys
import pickle
import logging
import numpy as np

# Make color_detection importable regardless of cwd
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.append(_here)

from color_detection.create_gauss import create_gaussian
from color_detection.bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor
from config import Config

log = logging.getLogger(__name__)

# ── Color → room and status mappings ────────────────────────────────────────

_COLOR_TO_ROOM = {
    "yellow": "patient_room",
    "blue":   "pharmacy",
    "orange": "door",
    "white":  "hallway",
    "black":  "hallway",
}

_NEEDS_MEDICINE_COLOR = "green"
_NO_MEDICINE_COLOR    = "red"

_CAL_FILE = os.path.join(_here, "color_detection", "detection_colors.pkl")


class PatientAssessor:
    """
    Wraps the EV3 color sensor and Bhattacharyya-distance classifier.

    Call current_room() inline during movement (no threading needed).
    Call needs_medicine() when stopped at a patient bed.

    Rooms:  'patient_room' | 'pharmacy' | 'door' | 'hallway' | 'unknown'
    Meds:   True (needs) | False (healthy) | None (undetermined)
    """

    WINDOW_SIZE = 500

    def __init__(self, cal_file: str = _CAL_FILE):
        self._sensor = EV3ColorSensor(Config.Ports.COLOR)
        self._window = np.zeros((3, self.WINDOW_SIZE))

        try:
            with open(cal_file, "rb") as f:
                self._known_colors = pickle.load(f)
            log.info("PatientAssessor loaded %d color profiles from %s",
                     len(self._known_colors), cal_file)
        except Exception as exc:
            log.error("PatientAssessor: could not load calibration file: %s", exc)
            self._known_colors = {}

    # ── Core detection ───────────────────────────────────────────────────────

    def detect(self):
        """Sample the sensor, update the sliding window, return closest color name."""
        if not self._known_colors:
            return None

        for _ in range(self.WINDOW_SIZE // 4):
            rgb = self._sensor.get_rgb()
            if rgb:
                self._window = np.roll(self._window, -1, axis=1)
                self._window[:, -1] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]

        mean1, cov1 = create_gaussian(self._window)

        best_color, best_dist = None, None
        for name, profile in self._known_colors.items():
            dist = bhatta_distance(mean1, cov1, profile["mean"], profile["cov"])
            if dist is None:
                continue
            if best_dist is None or dist < best_dist:
                best_dist, best_color = dist, name

        log.debug("PatientAssessor.detect → %s (dist=%s)", best_color, best_dist)
        return best_color

    # ── Public API ───────────────────────────────────────────────────────────

    def current_room(self) -> str:
        """Return the room type the robot is currently over."""
        color = self.detect()
        if color is None:
            return "unknown"
        return _COLOR_TO_ROOM.get(color.lower(), "unknown")

    def needs_medicine(self) -> bool | None:
        """Return True (needs medicine), False (healthy), or None (undetermined)."""
        color = self.detect()
        if color is None:
            return None
        color = color.lower()
        if color == _NEEDS_MEDICINE_COLOR:
            return True
        if color == _NO_MEDICINE_COLOR:
            return False
        return None