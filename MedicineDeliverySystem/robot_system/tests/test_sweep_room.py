"""
Sweep-room integration test.

Positions the robot at a room entrance, triggers sweep_room, and verifies
that it returns to (approximately) the entry point.

Run on the robot with:
    python3 test_sweep_room.py [--gyro] [--room1|--standard|--room4]

Flags:
    --gyro      enable gyro sensor (highly recommended for sweep accuracy)
    --room1     use room-1 asymmetric sweep angles  (default)
    --standard  use symmetric 30°/30° sweep
    --room4     use room-4 asymmetric sweep angles

What to observe:
    - Robot advances MID_ROOM_DIST + up to TOTAL_SWEEPS * HALF_BED_DIST
    - Scans left then right each iteration looking for a green bed
    - If bed found: drops medicine (placeholder), anchors on orange door, retreats
    - If no bed:    returns forward_dist via encoder-only dead-reckoning
    - Final position should be back at the entry point facing the original heading
"""

import sys
import os
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from navigator import Navigator
from patient_assessor import PatientAssessor
from payload_controller import PayloadController
from controller import Controller
from config import Config
from utils.brick import EV3GyroSensor, wait_ready_sensors

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("robot_log.txt"),
    ],
)
log = logging.getLogger("test_sweep_room")

# ── Argument parsing ──────────────────────────────────────────────────────────
use_gyro  = "--gyro"     in sys.argv
use_room1 = "--room1"    in sys.argv
use_room4 = "--room4"    in sys.argv
use_std   = "--standard" in sys.argv

# Default to room1 if nothing specified
if not use_room1 and not use_room4 and not use_std:
    use_room1 = True

# ── Setup ─────────────────────────────────────────────────────────────────────
if use_gyro:
    log.info("Initialising gyro on port %d …", Config.Ports.GYRO)
    gyro = EV3GyroSensor(Config.Ports.GYRO)
    wait_ready_sensors()
    log.info("Gyro ready.")
else:
    gyro = None
    log.info("Running WITHOUT gyro (blind turns).")

controller = Controller.__new__(Controller)   # bypass __init__ so we control gyro ourselves
controller.gyro     = gyro
controller.nav      = Navigator(gyro=gyro)
controller.assessor = PatientAssessor()
controller.payload  = PayloadController(controller.nav)
controller._medicine_dropped = 0

# ── Sweep selection ───────────────────────────────────────────────────────────
if use_room1:
    left_angle  = Config.Controller.OBSTACLE_SWEEP_ANGLE
    right_angle = Config.Controller.SWEEP_ANGLE
    label = "room1 (asymmetric)"
elif use_room4:
    left_angle  = Config.Controller.SWEEP_ANGLE
    right_angle = Config.Controller.OBSTACLE_SWEEP_ANGLE
    label = "room4 (asymmetric)"
else:
    left_angle  = Config.Controller.SWEEP_ANGLE
    right_angle = Config.Controller.SWEEP_ANGLE
    label = "standard (symmetric 30°/30°)"

log.info("=== Sweep-room test: %s ===", label)
log.info("MID_ROOM_DIST=%d  HALF_BED_DIST=%d  TOTAL_SWEEPS=%d",
         Config.Controller.MID_ROOM_DIST,
         Config.Controller.HALF_BED_DIST,
         Config.Controller.TOTAL_SWEEPS)

input("Place robot at room entrance and press Enter to begin…")

heading_before = controller.nav.heading
log.info("Entry heading=%.1f", heading_before)

controller.sweep_room(left_angle, right_angle)

heading_after = controller.nav.heading
log.info("=== sweep_room complete ===")
log.info("Heading before=%.1f  after=%.1f  delta=%.1f",
         heading_before, heading_after, heading_after - heading_before)
log.info("Medicine dropped this run: %d", controller._medicine_dropped)
log.info("Robot should now be back at the room entrance.")
