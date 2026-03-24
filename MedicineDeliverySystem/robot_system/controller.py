import sys

from navigator import Navigator
from config import Config
from utils.brick import EV3GyroSensor, wait_ready_sensors
from patient_assessor import PatientAssessor
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
        # Code to sweep room 1 for obstacles
        self.nav.move_forward(Config.Controller.ROOM_SWEEP_LENGTH, assessor=self.assessor)
        self.nav.move_backward(Config.Controller.ROOM_SWEEP_LENGTH, assessor=self.assessor)
        self.nav.diff_turn(-90, "left")
        self.nav.move_forward(Config.Controller.SWEEP_DIFF, assessor=self.assessor)
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.ROOM_SWEEP_LENGTH, assessor=self.assessor)
        self.nav.move_backward(Config.Controller.ROOM_SWEEP_LENGTH, assessor=self.assessor)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.SWEEP_DIFF, assessor=self.assessor)
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.ROOM_SWEEP_LENGTH, assessor=self.assessor)
        self.nav.move_backward(Config.Controller.ROOM_SWEEP_LENGTH, assessor=self.assessor)

if __name__ == "__main__":
    controller = Controller()
    controller.collect_medicine()
    controller.go_to_room1()
    controller.sweep_room1()

    