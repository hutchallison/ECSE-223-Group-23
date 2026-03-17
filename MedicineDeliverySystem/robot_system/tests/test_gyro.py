"""
Standalone gyro sensor test.
Prints abs (cumulative degrees) and dps (degrees/second) continuously.
Press Ctrl+C to stop.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.brick import EV3GyroSensor, wait_ready_sensors
from robot_system.config import Config

GYRO_PORT = Config.Ports.GYRO  # Port 4

print(f"Initializing gyro on port {GYRO_PORT} ...")
gyro = EV3GyroSensor(GYRO_PORT, mode="both")
wait_ready_sensors(True)
print("Gyro ready. Printing [abs_deg, dps]. Press Ctrl+C to stop.\n")

try:
    while True:
        value = gyro.get_both_measure()  # returns [abs_degrees, degrees_per_second]
        print(f"abs={value[0]:>7.1f} deg   dps={value[1]:>7.1f} deg/s")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped.")
