"""
Manual navigation tests for the Navigator class.

Run on the robot with:
    python3 test_navigator.py [test_name]

Available tests:
    forward   - move forward 30 cm and stop
    turn_right - turn 90 degrees clockwise
    turn_left  - turn 90 degrees counterclockwise
    box        - drive a 30 cm square (should return to start)
    box_back   - drive a square in reverse direction (CCW)

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

SIDE_CM = 30      # Box side length
PAUSE_S = 0.5     # Brief pause between moves so motors fully settle


def pause():
    time.sleep(PAUSE_S)


def report(nav, label=""):
    x, y, h = nav.get_position()
    log.info("%-20s → pos=(%.1f, %.1f) heading=%.1f°", label, x, y, h)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_forward(nav):
    """Move straight forward 30 cm."""
    log.info("=== TEST: forward ===")
    nav.move_forward(SIDE_CM)
    report(nav, "after forward")
    x, y, _ = nav.get_position()
    log.info("Expected pos ~(30, 0). Error: Δx=%.1f Δy=%.1f", abs(x - 30), abs(y))


def test_turn_right(nav):
    """Turn 90° clockwise (right)."""
    log.info("=== TEST: turn_right ===")
    nav.turn(-90)
    report(nav, "after turn_right")
    _, _, h = nav.get_position()
    log.info("Expected heading ~-90. Error: %.1f°", abs(h - (-90)))


def test_turn_left(nav):
    """Turn 90° counterclockwise (left)."""
    log.info("=== TEST: turn_left ===")
    nav.turn(90)
    report(nav, "after turn_left")
    _, _, h = nav.get_position()
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

    x, y, h = nav.get_position()
    pos_error = (x**2 + y**2) ** 0.5
    heading_error = abs(h % 360)
    log.info("=== BOX RESULT ===")
    log.info("Final pos=(%.1f, %.1f) heading=%.1f°", x, y, h)
    log.info("Position error from origin: %.1f cm", pos_error)
    log.info("Heading error from 0°: %.1f°", heading_error)


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

    x, y, h = nav.get_position()
    pos_error = (x**2 + y**2) ** 0.5
    log.info("=== BOX_BACK RESULT ===")
    log.info("Final pos=(%.1f, %.1f) heading=%.1f°", x, y, h)
    log.info("Position error from origin: %.1f cm", pos_error)


# ── Entry point ───────────────────────────────────────────────────────────────

TESTS = {
    "forward":    test_forward,
    "turn_right": test_turn_right,
    "turn_left":  test_turn_left,
    "box":        test_box,
    "box_back":   test_box_back,
}

if __name__ == "__main__":
    test_name = sys.argv[1] if len(sys.argv) > 1 else "box"
    time.sleep(45)
    if test_name not in TESTS:
        log.error("Unknown test '%s'. Available: %s", test_name, ", ".join(TESTS))
        sys.exit(1)

    # Instantiate without sensors for basic testing.
    # To test with sensors, replace with:
    from utils.brick import EV3GyroSensor, EV3UltrasonicSensor, wait_ready_sensors
    gyro = EV3GyroSensor(Config.Ports.GYRO)
    # us   = EV3UltrasonicSensor(Config.Ports.ULTRASONIC)
    wait_ready_sensors()
    nav = Navigator(gyro=gyro)
    # nav = Navigator()

    log.info("Starting test: %s", test_name)
    TESTS[test_name](nav)
    log.info("Test complete.")
