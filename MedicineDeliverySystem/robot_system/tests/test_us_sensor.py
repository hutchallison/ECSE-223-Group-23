#!/usr/bin/python3
"""
Ultrasonic sensor live-read test.

Run on the robot with:
    python3 test_us_sensor.py

Prints distance (cm) continuously until Ctrl-C.
"""

import sys
import os
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.brick import EV3UltrasonicSensor, wait_ready_sensors
from config import Config

us = EV3UltrasonicSensor(Config.Ports.ULTRASONIC)
wait_ready_sensors()

print(f"Reading ultrasonic on port {Config.Ports.ULTRASONIC} — Ctrl-C to stop\n")

try:
    while True:
        dist = us.get_cm()
        print(f"Distance: {dist} cm")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nDone.")
