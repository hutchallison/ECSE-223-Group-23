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

if __name__ == "__main__":
    run()
