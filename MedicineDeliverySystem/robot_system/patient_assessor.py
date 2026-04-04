import os
import sys
import pickle
import logging
import numpy as np
import time

# Make color_detection importable regardless of cwd
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.append(_here)

from color_detection.create_gauss import create_gaussian
from color_detection.bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor, wait_ready_sensors
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

_CAL_FILE = "test1.pkl"


class PatientAssessor:
    """
    Wraps the EV3 color sensor and Bhattacharyya-distance classifier.

    Call current_room() inline during movement (no threading needed).
    Call needs_medicine() when stopped at a patient bed.

    Rooms:  'patient_room' | 'pharmacy' | 'door' | 'hallway' | 'unknown'
    Meds:   True (needs) | False (healthy) | None (undetermined)
    """

    WINDOW_SIZE = 250

    def __init__(self, cal_file: str = _CAL_FILE):
        self._sensor = EV3ColorSensor(Config.Ports.COLOR)
        wait_ready_sensors(True)
        self._unknown_data = np.zeros((3, self.WINDOW_SIZE))

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
        for _ in range(self.WINDOW_SIZE):
            time.sleep(0.00001)
            rgb_values = self._sensor.get_rgb()
            if rgb_values and None not in rgb_values:
                self._unknown_data = np.roll(self._unknown_data, -1, axis=1)
                red, green, blue = rgb_values
                self._unknown_data[:, -1] = [int(red), int(green), int(blue)]

        mean1, cov1 = create_gaussian(self._unknown_data)

        min_bhatta_dist = None
        min_bhatta_dist_color = None
        for key in self._known_colors:
            mean2 = self._known_colors[key]["mean"]
            cov2 = self._known_colors[key]["cov"]
            current_bhatta_dist = bhatta_distance(mean1, cov1, mean2, cov2)
            if min_bhatta_dist is None:
                min_bhatta_dist = current_bhatta_dist
                min_bhatta_dist_color = key
            elif current_bhatta_dist is None:
                print("wtf")
            elif current_bhatta_dist < min_bhatta_dist:
                min_bhatta_dist = current_bhatta_dist
                min_bhatta_dist_color = key
        return  min_bhatta_dist_color #, unknown_color_data

    # ── Public API ───────────────────────────────────────────────────────────

    def current_room(self):
        """Return the room type the robot is currently over."""
        color = self.detect()
        if color is None:
            return "unknown" 
        return _COLOR_TO_ROOM.get(color.lower(), "unknown")

    def needs_medicine(self):
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

    def fast_color(self, n_samples: int = 5):
        """Quick nearest-mean Euclidean classifier. No Gaussian — low latency for
        real-time line detection while moving."""
        if not self._known_colors:
            return None
        samples = []
        for _ in range(n_samples):
            rgb = self._sensor.get_rgb()
            if rgb and None not in rgb:
                samples.append([int(rgb[0]), int(rgb[1]), int(rgb[2])])
        if not samples:
            return None
        reading = np.mean(samples, axis=0)
        best_color, best_dist = None, None
        for name, profile in self._known_colors.items():
            diff = reading - profile["mean"]
            dist = float(np.dot(diff, diff))
            if best_dist is None or dist < best_dist:
                best_dist, best_color = dist, name
        log.debug("PatientAssessor.fast_color → %s", best_color)
        return best_color

    def is_color(self, target: str, n_samples: int = 5) -> bool:
        """Returns True if fast_color() matches target (case-insensitive)."""
        detected = self.fast_color(n_samples)
        return detected is not None and detected.lower() == target.lower()

if __name__ == "__main__":
    assessor = PatientAssessor()
    while True:
        print(assessor.detect())
