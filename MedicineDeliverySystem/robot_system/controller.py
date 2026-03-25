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
    def __init__(self):
        gyro = EV3GyroSensor(Config.Ports.GYRO)
        wait_ready_sensors()
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
        self.nav.move_backward(Config.Controller.S2_SEGMENT1, assessor=self.assessor)
        self.nav.diff_turn(90, "right")
        self.nav.move_forward(Config.Controller.S2_SEGMENT2, assessor=self.assessor)

    def sweep_room1(self):
        """Angular sweep of room 1. Scans left 20deg then right to -45deg.
        If a bed is found, backs up and drops medicine.
        If no bed, realigns to 0deg and nudges forward as a final check."""

        # Phase A: sweep left ~20 deg (CCW)
        for _ in range(Config.Controller.TOTAL_SWEEPS):
            bed_found = self.nav.scan_turn(
                Config.Controller.SWEEP_ANGLE_LEFT, self.assessor
            )

            if not bed_found:
                total_right = Config.Controller.SWEEP_ANGLE_LEFT + Config.Controller.SWEEP_ANGLE_RIGHT
                bed_found = self.nav.scan_turn(-total_right, self.assessor)

            if bed_found:
                self.nav.move_backward(Config.Controller.SWEEP_BACKUP_TO_DROP_DIST)
                if self._room1_trips == 0:
                    self.payload.drop_first_med()
                else:
                    self.payload.drop_second_med()
                self._room1_trips += 1
                return

            # No bed found — realign to 0 deg and nudge for final confirmation
            self.nav.turn(-self.nav.heading)
            self.nav.move_forward(Config.Controller.HALF_BED_DIST, assessor=self.assessor)

if __name__ == "__main__":
    controller = Controller()
    controller.payload.lift_clamp()
    # controller.collect_medicine()
    # controller.go_to_room1()
    controller.sweep_room1()
    controller.nav.move_backward(25)

    