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
    level=logging.INFO,
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
        self.nav.move_forward(Config.Controller.HALF_BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.HALF_BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.move_backward(Config.Controller.HALF_BLACK_LINE_SEGMENT, assessor=self.assessor)

    def go_to_room1(self):
        self.nav.turn(90)
        self.nav.move_backward(Config.Controller.HALF_BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.S2_SEGMENT2, assessor=self.assessor)

    def sweep_room(self, sweep_left_angle: int, sweep_right_angle: int):
        """Angular sweep of room 1. Scans left then right using encoders (no gyro).
        Encoder-based scan_turn avoids motor-vibration-induced gyro drift during the sweep.
        Gyro is used only for the absolute return to sweep_origin, which is accurate
        because the robot is stationary when turn_to_heading reads the sensor."""
        self.nav.move_forward(Config.Controller.MID_ROOM_DIST, assessor=self.assessor)
        # Capture absolute gyro position now while stationary — no vibration error yet.
        sweep_origin = self.nav.heading

        total_sweeps = 0
        for _ in range(Config.Controller.TOTAL_SWEEPS):
            total_sweeps += 1
            self.nav.move_forward(Config.Controller.HALF_BED_DIST, assessor=self.assessor)
            # use_gyro=False: encoder odometry for the sweep motion so gyro cannot
            # accumulate vibration drift. The absolute return via turn_to_heading corrects
            # any encoder odometry error at the end of each loop iteration.
            bed_found = self.nav.scan_turn(
                sweep_left_angle, self.assessor, use_gyro=False
            )

            if not bed_found:
                total_right = sweep_left_angle + sweep_right_angle
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
        
        self.nav.move_backward(total_sweeps * Config.Controller.HALF_BED_DIST + Config.Controller.MID_ROOM_DIST) # Should be back at black cross
    
    def sweep_room1(self):
        self.sweep_room(Config.Controller.OBSTACLE_SWEEP_ANGLE, Config.Controller.SWEEP_ANGLE_RIGHT)

    def go_to_room2(self):
        self.nav.turn(90)
        self.nav.move_forward(2 * Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.turn(-90)
    
    def sweep_room_standard(self):
        self.sweep_room(-Config.Controller.SWEEP_ANGLE_RIGHT, Config.Controller.SWEEP_ANGLE_RIGHT)
    
    def go_to_room3(self):
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.turn(90)

    def go_to_room4(self):
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor)
        self.nav.turn(-90)
    
    def sweep_room4(self):
        self.sweep_room(Config.Controller.SWEEP_ANGLE_RIGHT, Config.Controller.OBSTACLE_SWEEP_ANGLE)

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
    controller.go_to_room2()
    controller.sweep_room_standard()
    controller.go_to_room3()
    controller.sweep_room_standard()
    controller.go_to_room4()
    controller.sweep_room4()

    