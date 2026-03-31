"""
Gyro scale calibration tool.
Measures GYRO_SCALE by rotating the robot a known angle and comparing
the raw sensor reading to the true angle.

Usage:
    python3 calibrate_gyro.py

Steps:
  1. Place the robot pointing at a fixed landmark.
  2. Script zeros the gyro offset and waits for you to rotate.
  3. Choose a known angle (e.g. 90, 180, 360) and rotate exactly that far.
  4. Press Enter — script reads raw and compensated values, computes scale.
  5. Repeat with different angles for better statistics.
  6. Press 'q' when done. Prints the final recommended GYRO_SCALE.

Column legend:
  raw      — what the sensor actually reported (no scaling)
  current  — raw * current GYRO_SCALE from config
  true     — the known angle you rotated
  new_scale — scale factor that would make raw == true for this sample
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.brick import EV3GyroSensor, wait_ready_sensors
from robot_system.config import Config

CURRENT_SCALE = Config.Navigation.GYRO_SCALE_LEFT

print("Initializing gyro...")
gyro = EV3GyroSensor(Config.Ports.GYRO, mode="abs")
wait_ready_sensors(True)
print(f"Gyro ready. Current GYRO_SCALE in config: {CURRENT_SCALE}\n")
print(f"  {'sample':>6}  {'true°':>6}  {'raw':>8}  {'current':>9}  {'new_scale':>10}")
print("-" * 52)

samples = []  # list of (true_angle, raw_measured, new_scale)

while True:
    n = len(samples) + 1

    # Take baseline snapshot
    baseline = gyro.get_abs_measure()
    if baseline is None:
        print("ERROR: could not read gyro. Check connection.")
        sys.exit(1)

    print(f"\nSample {n}:")
    print(f"  Align robot to a reference, then rotate a known angle.")

    angle_str = input("  Enter the angle you will rotate (degrees, e.g. 90 / 180 / 360): ").strip()
    try:
        known_angle = float(angle_str)
    except ValueError:
        print("  Invalid number, skipping.")
        continue
    if known_angle <= 0:
        print("  Angle must be positive, skipping.")
        continue

    baseline = gyro.get_abs_measure()  # re-read right before move
    print(f"  Rotate EXACTLY {known_angle:.0f}° now...")
    input("  Press Enter when done rotating... ")

    reading = gyro.get_abs_measure()
    if reading is None:
        print("  ERROR: gyro returned None, skipping.")
        continue

    raw_delta = abs(reading - baseline)
    if raw_delta < 1:
        print("  No rotation detected (raw delta < 1°), skipping.")
        continue

    new_scale = known_angle / raw_delta
    current_compensated = raw_delta * CURRENT_SCALE
    samples.append((known_angle, raw_delta, new_scale))

    print(f"  {n:>6}  {known_angle:>6.1f}  {raw_delta:>8.2f}  {current_compensated:>9.2f}  {new_scale:>10.4f}")

    if len(samples) > 1:
        avg_scale = sum(s for _, _, s in samples) / len(samples)
        # Simple linear fit: scale = true / raw — check if raw→true is linear through 0
        total_raw  = sum(r for _, r, _ in samples)
        total_true = sum(t for t, _, _ in samples)
        lsq_scale  = total_true / total_raw  # least-squares through origin
        print(f"\n  Running stats ({len(samples)} samples):")
        print(f"    Mean of per-sample scales : {avg_scale:.4f}")
        print(f"    Least-squares scale (recommended): {lsq_scale:.4f}")
    print()

    resp = input("  Another sample? [Enter = yes, q = done] ").strip().lower()
    if resp == 'q':
        break

if not samples:
    print("No samples collected.")
    sys.exit(0)

avg_scale = sum(s for _, _, s in samples) / len(samples)
total_raw  = sum(r for _, r, _ in samples)
total_true = sum(t for t, _, _ in samples)
lsq_scale  = total_true / total_raw

print()
print("=" * 52)
print(f"  Samples collected : {len(samples)}")
print(f"  Mean per-sample GYRO_SCALE : {avg_scale:.4f}")
print(f"  Least-squares GYRO_SCALE   : {lsq_scale:.4f}  ← recommended")
print(f"  Current config GYRO_SCALE  : {CURRENT_SCALE:.4f}")
print()
print("  Per-sample breakdown:")
print(f"  {'#':>3}  {'true°':>6}  {'raw':>8}  {'current':>9}  {'new_scale':>10}")
for i, (t, r, s) in enumerate(samples, 1):
    print(f"  {i:>3}  {t:>6.1f}  {r:>8.2f}  {r * CURRENT_SCALE:>9.2f}  {s:>10.4f}")
print()
print(f"  Update config.py:")
print(f"    GYRO_SCALE = {lsq_scale:.4f}")
print("=" * 52)
