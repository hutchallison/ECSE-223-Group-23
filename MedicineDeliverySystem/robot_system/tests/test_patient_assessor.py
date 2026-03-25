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

# Make sure robot_system modules are importable when run from the tests/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from patient_assessor import PatientAssessor

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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        run_continuous()
    else:
        run()
