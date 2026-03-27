"""
Standalone gyro sensor test.
Prints raw abs, scaled abs, raw dps, and scaled dps continuously.
This lets you compare what the sensor actually reports vs what the
navigator sees after GYRO_SCALE is applied.

Press Ctrl+C to stop.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.brick import EV3GyroSensor, wait_ready_sensors
from robot_system.config import Config

GYRO_PORT = Config.Ports.GYRO  # Port 4
SCALE = Config.Navigation.GYRO_SCALE

print(f"Initializing gyro on port {GYRO_PORT} ...")
gyro = EV3GyroSensor(GYRO_PORT, mode="both")
wait_ready_sensors(True)

# Capture offset so compensated heading starts at 0 (mirrors Navigator logic)
offset = gyro.get_abs_measure() or 0.0

print(f"Gyro ready. GYRO_SCALE = {SCALE}  offset = {offset:.1f}")
print(f"{'raw_abs':>9}  {'comp_abs':>9}  {'raw_dps':>9}  {'comp_dps':>9}")
print("-" * 46)

try:
    while True:
        value = gyro.get_both_measure()  # [abs_degrees, degrees_per_second]
        if value is None:
            print("  (no reading)")
            time.sleep(0.1)
            continue

        raw_abs  = value[0]
        raw_dps  = value[1]
        comp_abs = (raw_abs - offset) * SCALE
        comp_dps = raw_dps * SCALE

        print(f"{raw_abs:>9.1f}  {comp_abs:>9.1f}  {raw_dps:>9.1f}  {comp_dps:>9.1f}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped.")
