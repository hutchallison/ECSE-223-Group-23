#!/usr/bin/python3
"""
Manual navigation tests for the Navigator class.

Run on the robot with:
    python3 test_navigator.py [test_name] [--gyro]

Available tests:
    forward    - move forward 30 cm and stop
    turn_right - turn 90 degrees clockwise
    turn_left  - turn 90 degrees counterclockwise
    box        - drive a 30 cm square (should return to start)
    box_back   - drive a square in reverse direction (CCW)

Flags:
    --gyro     - enable gyro sensor for turn trimming (default: blind turns only)

With no argument, runs the box test by default.
"""

import sys
import logging
import time
import sys
import os

# Get the directory of the current file (tests/), then go up one level to robot_system/
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Add the parent directory to Python's search path
sys.path.append(parent_dir)

# NOW you can import your classes safely
from navigator import Navigator
from config import Config

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.Logging.LOG_FILE),
    ]
)
log = logging.getLogger("test_navigator")

# ── Helpers ───────────────────────────────────────────────────────────────────

SIDE_CM = 50      # Box side length
PAUSE_S = 0.5     # Brief pause between moves so motors fully settle


def pause():
    time.sleep(PAUSE_S)


def report(nav, label=""):
    return None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_forward(nav):
    """Move straight forward 30 cm."""
    log.info("=== TEST: forward ===")
    nav.move_forward(SIDE_CM)
    report(nav, "after forward")
    log.info("Expected pos ~(30, 0). Error: Δx=%.1f Δy=%.1f", abs(x - 30), abs(y))


def test_turn_right(nav):
    """Turn 90° clockwise (right)."""
    log.info("=== TEST: turn_right ===")
    nav.turn(-90)
    report(nav, "after turn_right")
    log.info("Expected heading ~-90. Error: %.1f°", abs(h - (-90)))


def test_turn_left(nav):
    """Turn 90° counterclockwise (left)."""
    log.info("=== TEST: turn_left ===")
    nav.turn(90)
    report(nav, "after turn_left")
    log.info("Expected heading ~90. Error: %.1f°", abs(h - 90))


def test_box(nav):
    """
    Drive a 30 cm clockwise square (right turns).
    Should return close to (0, 0) with heading ~0° after 4 sides.
    """
    log.info("=== TEST: box (CW, right turns) ===")
    for side in range(1, 5):
        nav.move_forward(SIDE_CM)
        report(nav, f"side {side} done")
        pause()
        nav.turn(-90)
        report(nav, f"turn {side} done")
        pause()


def test_box_back(nav):
    """
    Drive a 30 cm counterclockwise square (left turns).
    Alternative to check turn symmetry.
    """
    log.info("=== TEST: box_back (CCW, left turns) ===")
    for side in range(1, 5):
        nav.move_forward(SIDE_CM)
        report(nav, f"side {side} done")
        pause()
        nav.turn(90)
        report(nav, f"turn {side} done")
        pause()

def go_to_room(nav):
	input("Position robot at start point and press Enter to begin...")
	nav.move_forward(10)
	nav.turn(90)
	nav.move_forward(20)
	for i in range(5):
		nav.turn(-9)
		nav.move_forward(0.01)
	for i in range(5):
		nav.turn(-9)
		nav.move_forward(0.9)
	nav.move_forward(56)
	for i in range(2):
		print("backwords")
		nav.move_backward(30)
		nav.turn(-90)
		nav.move_forward(3)
		nav.turn(90)
		nav.move_forward(30)


# ── Entry point ───────────────────────────────────────────────────────────────

TESTS = {
    "forward":    test_forward,
    "turn_right": test_turn_right,
    "turn_left":  test_turn_left,
    "box":        test_box,
    "box_back":   test_box_back,
	"go_to_room": go_to_room,
}

if __name__ == "__main__":
    args = sys.argv[1:]
    use_gyro = "--gyro" in args
    test_name = next((a for a in args if not a.startswith("--")), "box")

    input("Press Enter to start the test...")
    if test_name not in TESTS:
        log.error("Unknown test '%s'. Available: %s", test_name, ", ".join(TESTS))
        sys.exit(1)

    gyro = None
    if use_gyro:
        from utils.brick import EV3GyroSensor, wait_ready_sensors
        gyro = EV3GyroSensor(Config.Ports.GYRO)
        wait_ready_sensors()
        log.info("Gyro enabled on port %s", Config.Ports.GYRO)
    else:
        log.info("Running without gyro (blind turns)")

    nav = Navigator(gyro=gyro)

    log.info("Starting test: %s", test_name)
    input("Position robot at start point and press Enter to begin...")
    TESTS[test_name](nav)
    log.info("Test complete.")
