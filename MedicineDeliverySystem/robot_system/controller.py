import sys

from navigator import Navigator
from config import Config
from utils.brick import EV3GyroSensor, wait_ready_sensors
from patient_assessor import PatientAssessor
from payload_controller import PayloadController
import logging

log = logging.getLogger(__name__)

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.Logging.LOG_FILE),
    ]
)
log = logging.getLogger("controller")

class Controller:
    def __init__(self, use_gyro=True):

        if use_gyro:
            gyro = EV3GyroSensor(Config.Ports.GYRO)
            wait_ready_sensors()
        else:
            gyro = None

        self.gyro = gyro
        self.nav = Navigator(gyro=gyro)
        self.assessor = PatientAssessor()
        self.payload = PayloadController(self.nav)
        self._room1_trips = 0
    
    def collect_medicine(self):
        # Code to navigate to the medicine location and collect it
        self.nav.move_forward(Config.Controller.S1_SEGMENT1, assessor=self.assessor)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.S1_SEGMENT2, assessor=self.assessor)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.S1_SEGMENT3, assessor=self.assessor)
        self.nav.move_backward(Config.Controller.S1_SEGMENT3, assessor=self.assessor)

    def go_to_room1(self):
        self.nav.turn(90)
        self.nav.move_backward(Config.Controller.S1_SEGMENT2, assessor=self.assessor)
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.S2_SEGMENT2, assessor=self.assessor)

    def sweep_room1(self):
        """Angular sweep of room 1. Scans left then right using encoders (no gyro).
        Encoder-based scan_turn avoids motor-vibration-induced gyro drift during the sweep.
        Gyro is used only for the absolute return to sweep_origin, which is accurate
        because the robot is stationary when turn_to_heading reads the sensor."""
        self.nav.move_forward(10, assessor=self.assessor)
        # Capture absolute gyro position now while stationary — no vibration error yet.
        sweep_origin = self.nav.heading

        for _ in range(Config.Controller.TOTAL_SWEEPS):
            self.nav.move_forward(Config.Controller.HALF_BED_DIST, assessor=self.assessor)
            # use_gyro=False: encoder odometry for the sweep motion so gyro cannot
            # accumulate vibration drift. The absolute return via turn_to_heading corrects
            # any encoder odometry error at the end of each loop iteration.
            bed_found = self.nav.scan_turn(
                Config.Controller.SWEEP_ANGLE_LEFT, self.assessor, use_gyro=False
            )

            if not bed_found:
                total_right = Config.Controller.SWEEP_ANGLE_LEFT + Config.Controller.SWEEP_ANGLE_RIGHT
                bed_found = self.nav.scan_turn(-total_right, self.assessor, use_gyro=False)

            if bed_found:
                self.nav.move_backward(Config.Controller.SWEEP_BACKUP_TO_DROP_DIST)
                if self._room1_trips == 0:
                    self.payload.drop_first_med()
                else:
                    self.payload.drop_second_med()
                self._room1_trips += 1
                if self.gyro is not None:
                    self.nav.turn_to_heading(sweep_origin)
                return

            # No bed found — return to sweep_origin using absolute gyro.
            # Because scan_turns used encoders, the gyro has not drifted from vibration,
            # so this accurately restores the physical heading.
            if self.gyro is not None:
                self.nav.turn_to_heading(sweep_origin)
            else:
                self.nav.turn(-self.nav.heading)

if __name__ == "__main__":
    use_gyro = input("Use gyro? (y/n): ").strip().lower() == "y"
    controller = Controller(use_gyro=use_gyro)
    controller.payload.engage_clamp()
    controller.payload.lift_clamp()
    controller.collect_medicine()
    input("Press Enter to start room 1 navigation...")
    controller.go_to_room1()
    input("Press Enter to start room 1 sweep...")
    controller.sweep_room1()
    controller.nav.move_backward(50)

    