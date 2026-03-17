"""
Gyro scale calibration tool.
Measures GYRO_SCALE by having you rotate the robot a known angle.

Usage:
    python3 calibrate_gyro.py

Steps:
  1. Place robot pointing at a fixed landmark.
  2. Script zeros the gyro and waits for you to press Enter.
  3. Rotate the robot EXACTLY 360° by hand (back to the same landmark).
  4. Press Enter — script reads the gyro and computes the scale.
  5. Repeat for more samples (averages them for accuracy).
  6. Press 'q' when done. Prints the final GYRO_SCALE value.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.brick import EV3GyroSensor, wait_ready_sensors
from robot_system.config import Config

KNOWN_ANGLE = 360.0  # degrees per rotation

print("Initializing gyro...")
gyro = EV3GyroSensor(Config.Ports.GYRO, mode="abs")
wait_ready_sensors(True)
print("Gyro ready.\n")

samples = []

while True:
    # Reset baseline
    baseline = gyro.get_abs_measure()
    if baseline is None:
        print("ERROR: could not read gyro. Check connection.")
        sys.exit(1)

    print(f"Sample {len(samples) + 1}:")
    print(f"  1) Align robot to a fixed reference point.")
    print(f"  2) Press Enter, then rotate EXACTLY {KNOWN_ANGLE:.0f}° and return to the reference.")
    input("  Press Enter to start... ")

    baseline = gyro.get_abs_measure()
    print("  Rotate now...")
    input("  Press Enter when back at the reference point... ")

    reading = gyro.get_abs_measure()
    if reading is None:
        print("  ERROR: gyro returned None, skipping.")
        continue

    measured = abs(reading - baseline)
    if measured < 1:
        print("  No rotation detected, skipping.")
        continue

    scale = KNOWN_ANGLE / measured
    samples.append(scale)
    print(f"  Gyro read: {measured:.1f}°  →  scale = {KNOWN_ANGLE:.0f} / {measured:.1f} = {scale:.4f}")
    print()

    avg = sum(samples) / len(samples)
    print(f"  Running average ({len(samples)} sample{'s' if len(samples) > 1 else ''}): GYRO_SCALE = {avg:.4f}")
    print()

    resp = input("  Another sample? [Enter = yes, q = done] ").strip().lower()
    if resp == 'q':
        break
    print()

avg = sum(samples) / len(samples)
print()
print("=" * 50)
print(f"  FINAL GYRO_SCALE = {avg:.4f}")
print(f"  (from {len(samples)} sample{'s' if len(samples) > 1 else ''})")
print()
print(f"  Update config.py:")
print(f"    GYRO_SCALE = {avg:.4f}")
print("=" * 50)
