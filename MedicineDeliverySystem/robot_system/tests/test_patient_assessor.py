"""
Manual test for PatientAssessor.needs_medicine().

Run on the robot with:
    python3 test_patient_assessor.py

Hold the color sensor over each colour marker when prompted and verify the output.
Expected:
    green marker -> needs_medicine() returns True
    red marker   -> needs_medicine() returns False
    no marker    -> needs_medicine() returns None  (or best-effort unknown colour)
"""

import sys
import os
import time
import pickle
import numpy as np

# Make sure robot_system modules are importable when run from the tests/ folder
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_robot_dir = os.path.dirname(_tests_dir)
sys.path.insert(0, _robot_dir)

from patient_assessor import PatientAssessor
from color_detection.create_gauss import create_gaussian
from color_detection.bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor, wait_ready_sensors

CHECKS = [
    ("GREEN (needs medicine) — hold sensor over green marker", True),
    ("RED   (healthy)        — hold sensor over red marker",   False),
    ("NONE  (no marker)      — hold sensor in the air",        None),
]

def run():
    assessor = PatientAssessor()
    passed = 0

    for prompt, expected in CHECKS:
        input(f"\n>>> {prompt}\n    Press ENTER when ready...")
        result = assessor.needs_medicine()
        status = "PASS" if result == expected else "FAIL"
        print(f"    needs_medicine() = {result!r}  (expected {expected!r})  [{status}]")
        if result == expected:
            passed += 1

    print(f"\n{passed}/{len(CHECKS)} checks passed.")


def run_continuous():
    """Continuously call detect() and print the result. Ctrl-C to stop."""
    assessor = PatientAssessor()
    print("Continuous detect() — move sensor over colours. Ctrl-C to stop.\n")
    while True:
        color = assessor.detect()
        needs = assessor.needs_medicine()
        print(f"  detect={color!r:12s}  needs_medicine={needs!r}")
        time.sleep(0.1)


def run_raw_continuous():
    """
    Replicate detect_color() from path_testing.py exactly — uses final_project.cal,
    samples the sensor directly, prints raw result continuously. Ctrl-C to stop.
    """
    cal_file = os.path.join(_robot_dir, "color_detection", "final_project.cal")
    try:
        with open(cal_file, "rb") as f:
            known_colors = pickle.load(f)
        print(f"Loaded {len(known_colors)} profiles from final_project.cal")
    except Exception as e:
        print(f"ERROR loading {cal_file}: {e}")
        return

    WINDOW_SIZE = 500
    color_sensor = EV3ColorSensor(3)
    wait_ready_sensors(True)
    data = np.zeros((3, WINDOW_SIZE))

    print("Raw detect (final_project.cal) — move sensor over colours. Ctrl-C to stop.\n")

    while True:
        for _ in range(WINDOW_SIZE // 4):
            time.sleep(0.00001)
            rgb = color_sensor.get_rgb()
            if rgb:
                data = np.roll(data, -1, axis=1)
                data[:, -1] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]

        mean1, cov1 = create_gaussian(data)

        best_color, best_dist = None, None
        for name, profile in known_colors.items():
            dist = bhatta_distance(mean1, cov1, profile["mean"], profile["cov"])
            if dist is None:
                continue
            if best_dist is None or dist < best_dist:
                best_dist, best_color = dist, name

        print(f"  raw detect={best_color!r:12s}  dist={best_dist}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        run_continuous()
    elif len(sys.argv) > 1 and sys.argv[1] == "raw":
        run_raw_continuous()
    else:
        run()
