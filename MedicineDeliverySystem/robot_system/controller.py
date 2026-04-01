import sys
import time

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
    def __init__(self, use_gyro=True, left_wheel_compensation=0, right_wheel_compensation=0):

        if use_gyro:
            gyro = EV3GyroSensor(Config.Ports.GYRO)
            wait_ready_sensors()
        else:
            gyro = None

        self.gyro = gyro
        self.nav = Navigator(gyro=gyro, left_wheel_compensation=left_wheel_compensation, right_wheel_compensation=right_wheel_compensation)
        self.assessor = PatientAssessor()
        self.payload = PayloadController(self.nav)
        self._medicine_dropped = 0
    
    def collect_medicine(self):
        # Code to navigate to the medicine location and collect it
        self.nav.move_forward(Config.Controller.EXIT_ROOM_DIST, assessor=self.assessor)#, follow_line=True)
        self.nav.turn_right(bias=-10)
        self.nav.move_forward(Config.Controller.ENTER_PHARMA, assessor=self.assessor)#, follow_line=True)
        self.nav.turn_right(bias=-6)
        self.payload.pharmacy_pickup()

    def go_to_room1(self):
        self.nav.turn_left()
        self.nav.move_backward(Config.Controller.ENTER_PHARMA, assessor=self.assessor)
        self.nav.turn_left()
        self.nav.move_forward(Config.Controller.S2_SEGMENT2, assessor=self.assessor)

    def sweep_room(self, sweep_left_angle: int, sweep_right_angle: int):
        if self.gyro:
            self.sweep_room_gyro(sweep_left_angle, sweep_right_angle)
        else:
            self.sweep_room_dumb(sweep_left_angle, sweep_right_angle)

    def sweep_room_dumb(self, sweep_left_angle: int, sweep_right_angle: int):
        log.info("sweep_room_dumb start | left=%d right=%d", sweep_left_angle, sweep_right_angle)
        self.nav.move_forward(Config.Controller.MID_ROOM_DIST, assessor=self.assessor)
        forward_dist = Config.Controller.MID_ROOM_DIST
        bed_was_found = False
        for sweep_i in range(Config.Controller.TOTAL_SWEEPS):
            log.info("sweep_room_dumb sweep %d/%d | forward_dist=%.1f", sweep_i + 1, Config.Controller.TOTAL_SWEEPS, forward_dist)
            self.nav.move_forward(Config.Controller.HALF_BED_DIST, assessor=self.assessor)
            forward_dist += Config.Controller.HALF_BED_DIST

            log.info("sweep_room_dumb scanning LEFT %d deg", sweep_left_angle)
            bed_found = self.nav.scan_turn(sweep_left_angle, self.assessor)
            if bed_found:
                log.info("sweep_room_dumb bed found on LEFT scan")
                correction = -sweep_left_angle
            else:
                total_right = sweep_left_angle + sweep_right_angle
                log.info("sweep_room_dumb no bed on left, scanning RIGHT %d deg", total_right)
                bed_found = self.nav.scan_turn(-total_right, self.assessor)
                correction = sweep_right_angle  # returns to entry heading whether bed found or not
                if bed_found:
                    log.info("sweep_room_dumb bed found on RIGHT scan")
                else:
                    log.info("sweep_room_dumb no bed found this sweep")

            if bed_found:
                log.info("sweep_room_dumb dropping medicine #%d | correction=%.1f deg", self._medicine_dropped + 1, correction)
                self.nav.move_backward(Config.Controller.SWEEP_BACKUP_TO_DROP_DIST)
                if self._medicine_dropped == 0:
                    self.payload.drop_first_med()
                else:
                    self.payload.drop_second_med()
                self._medicine_dropped += 1
                log.info("sweep_room_dumb returning to entry heading, then exiting room")
                self.nav._turn_blind(correction)
                self.nav.move_backward(forward_dist - Config.Controller.HALF_BED_DIST)
                self.nav.move_backward_until_distance(
                    Config.Controller.DOOR_EXIT_DISTANCE_CM,
                    max_dist_cm=Config.Controller.MAX_ROOM_EXIT_DIST
                )
                bed_was_found = True
                break

            log.info("sweep_room_dumb correcting back to entry heading (%d deg)", correction)
            self.nav._turn_blind(correction)

        if bed_was_found:
            log.info("sweep_room_dumb done | bed found, medicine_dropped=%d", self._medicine_dropped)
            return
        log.info("sweep_room_dumb done | no bed found after all sweeps, exiting room")
        self.nav.move_backward(forward_dist - Config.Controller.HALF_BED_DIST, assessor=self.assessor)
        self.nav.move_backward_until_distance(Config.Controller.DOOR_EXIT_DISTANCE_CM, max_dist_cm=Config.Controller.MAX_ROOM_EXIT_DIST)

    def sweep_room_gyro(self, sweep_left_angle: int, sweep_right_angle: int):
        """Angular sweep of room 1. Scans left then right using encoders (no gyro).
        Encoder-based scan_turn avoids motor-vibration-induced gyro drift during the sweep.
        Gyro is used only for the absolute return to sweep_origin, which is accurate
        because the robot is stationary when turn_to_heading reads the sensor."""
        self.nav.move_forward(Config.Controller.MID_ROOM_DIST, assessor=self.assessor)
        # Capture absolute gyro position now while stationary — no vibration error yet.
        sweep_origin = self.nav.heading
        # Track exact net forward distance so we can reverse back to the start precisely.
        forward_dist = Config.Controller.MID_ROOM_DIST
        bed_was_found = False

        for _ in range(Config.Controller.TOTAL_SWEEPS):
            self.nav.move_forward(Config.Controller.HALF_BED_DIST, assessor=self.assessor)
            forward_dist += Config.Controller.HALF_BED_DIST

            bed_found = self.nav.scan_turn(
                sweep_left_angle, self.assessor, use_gyro=False
            )
            if not bed_found:
                total_right = sweep_left_angle + sweep_right_angle
                bed_found = self.nav.scan_turn(-total_right, self.assessor, use_gyro=False)

            if bed_found:
                self.nav.move_backward(Config.Controller.SWEEP_BACKUP_TO_DROP_DIST)
                if self._medicine_dropped == 0:
                    self.payload.drop_first_med()
                else:
                    self.payload.drop_second_med()
                self._medicine_dropped += 1
                # Restore entry heading while stationary (most reliable gyro read)
                if self.gyro is not None:
                    self.nav.turn_to_heading(sweep_origin)
                else:
                    self.nav.turn(-self.nav.heading)
                # Anchor-based exit: reverse until ultrasonic detects door opening
                self.nav.move_backward(forward_dist - Config.Controller.HALF_BED_DIST)  # retreat into hallway to ensure clear US reading
                self.nav.move_backward_until_distance(
                    Config.Controller.DOOR_EXIT_DISTANCE_CM,
                    max_dist_cm=Config.Controller.MAX_ROOM_EXIT_DIST
                )
                bed_was_found = True
                break

            # No bed found — restore heading for the next sweep iteration.
            # Because scan_turns used encoders, the gyro has not drifted from vibration,
            # so this accurately restores the physical heading.
            if self.gyro is not None:
                self.nav.turn_to_heading(sweep_origin - Config.Controller.BIAS)
                log.info("No bed detected, returning to heading %d° and moving forward for next sweep…", sweep_origin - Config.Controller.BIAS)

            else:
                self.nav.turn(-self.nav.heading)

        if bed_was_found:
            return
        self.nav.move_backward(forward_dist - Config.Controller.HALF_BED_DIST, assessor=self.assessor)
        self.nav.move_backward_until_distance(Config.Controller.DOOR_EXIT_DISTANCE_CM, max_dist_cm=Config.Controller.MAX_ROOM_EXIT_DIST)
    
    def sweep_room1(self):
        self.sweep_room(Config.Controller.OBSTACLE_SWEEP_ANGLE, Config.Controller.SWEEP_ANGLE)

    def go_to_room2(self):
        self.nav.turn_right()
        self.nav.move_forward(2 * Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor, follow_line=True)
    
    def sweep_room_standard(self):
        self.sweep_room(Config.Controller.SWEEP_ANGLE, Config.Controller.SWEEP_ANGLE)
    
    def go_to_room3(self):
        self.nav.move_forward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor, follow_line=True)
        self.nav.turn_right()

    def go_to_room4(self):
        self.nav.turn_right()
        self.nav.move_backward_until_distance(Config.Controller.DISTANCE_ROOM4_WALL, di)
        self.nav.turn_left()
    
    def sweep_room4(self):
        self.sweep_room(Config.Controller.SWEEP_ANGLE, Config.Controller.OBSTACLE_SWEEP_ANGLE)
    
    def sweep_room_cuts(self):
        self.nav.move_forward(35)
        self.nav.turn_left(10)
        self.nav.turn_right(10)
        self.nav.move_backwards(35)
    def return_to_pharmacy(self, from_room: int):
        # Code to return to the pharmacy after deliveries
        if from_room == 1:
            total_dist = Config.Controller.BLACK_LINE_SEGMENT + Config.Controller.HALF_BLACK_LINE_SEGMENT
            self.nav.move_backward(total_dist, assessor=self.assessor)
            self.nav.turn_right()

        elif from_room == 2:
            self.nav.move_backward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor)
            self.nav.turn_left()
            self.nav.move_until_distance(Config.Controller.STOP_PHARMACY)

        elif from_room == 3:
            self.nav.turn_right()
            self.nav.move_forward(2 * Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor, follow_line=True)
            self.nav.turn_left()
            self.nav.move_until_distance(Config.Controller.STOP_PHARMACY)

        elif from_room == 4:
            self.nav.turn_right()
            self.nav.move_forward(3 * Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor, follow_line=True)
            self.nav.turn_left()
            self.nav.move_until_distance(Config.Controller.STOP_PHARMACY)

if __name__ == "__main__":
    use_gyro = input("Use gyro? (y/n): ").strip().lower() == "y"
    left_wheel_compensation = int(input("Left wheel compensation DPS (0 = none): ").strip() or "0")
    right_wheel_compensation = int(input("Right wheel compensation DPS (0 = none): ").strip() or "0")
    controller = Controller(use_gyro=use_gyro, left_wheel_compensation=left_wheel_compensation, right_wheel_compensation=right_wheel_compensation)
    # controller.payload.engage_clamp()
    # controller.payload.lift_clamp()

    controller.collect_medicine()
    input("Press Enter to start room 1 navigation...")
    controller.go_to_room1()
    input("Press Enter to start room 1 sweep...")
    controller.sweep_room1()
    input("Continue? Press Enter to go to room 2... (dropped packets: %d)" % controller._medicine_dropped)
    controller.go_to_room2()

    if controller._medicine_dropped == 0:
        input("Continue to room2 sweep?")
        controller.nav.turn_left()
        controller.sweep_room_standard()
        controller.nav.turn_right()

    input("Continue? Press Enter to go to room 3... (dropped packets: %d)" % controller._medicine_dropped)
    controller.go_to_room3()
    input("Continue? Press Enter to start room 3 sweep... (dropped packets: %d)" % controller._medicine_dropped)
    controller.sweep_room_standard()

    if controller._medicine_dropped == 2:
        controller.return_to_pharmacy(from_room=3)
        input("Delivery complete!")
        exit(0)
    
    input("Continue? Press Enter to go to room 4... (dropped packets: %d)" % controller._medicine_dropped)
    controller.go_to_room4()
    input("Continue? Press Enter to start room 4 sweep... (dropped packets: %d)" % controller._medicine_dropped)
    controller.sweep_room4()

    if controller._medicine_dropped == 2:
        controller.return_to_pharmacy(from_room=4)
        input("Delivery complete!")
        exit(0)
