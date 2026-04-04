import sys

import time

from navigator import Navigator
from config import Config
from utils.brick import EV3GyroSensor, wait_ready_sensors
from patient_assessor import PatientAssessor
from payload_controller import PayloadController
import logging
import math

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
        self.room = 1
    
    def collect_medicine(self):
        self.payload.pickup()
        self.nav.move_backward_until_distance(102.0)
        self.nav.turn_left()
        self.nav.move_until_distance(54.6)

    def go_to_room1(self):
        self.nav.turn_left(bias=0)
        self.nav.move_backward(Config.Controller.ENTER_PHARMA, assessor=self.assessor)
        self.nav.turn_left(bias=2)
        self.nav.move_forward(Config.Controller.S2_SEGMENT2, assessor=self.assessor)

    def go_to_room2(self):
        self.room = 2
        self.nav.move_until_distance(54.5)
        self.nav.turn_left()

    def go_to_room3(self):
        self.room = 3
        self.nav.move_until_distance(28.8)#forward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor, follow_line=True)
        self.nav.turn_right()

    def go_to_room4(self):
        self.nav.move_backward_until_distance(Config.Controller.DISTANCE_ROOM4_WALL - 0.5)
        self.nav.turn_left()

    def drop_cube(self, turn_angle):
        self.nav.scan_turn(turn_angle*-1)
        if self.room != 2 or self._medicine_dropped != 1:
            new_angle = math.degrees(math.asin(math.sin(math.radians(turn_angle))*Config.Drop.BACK/Config.Drop.LENGTH))
            move_back = (math.cos(math.radians(new_angle))*Config.Drop.LENGTH - math.cos(math.radians(turn_angle))*Config.Drop.BACK)
            self.nav.move_backward(move_back)
            self.nav.scan_turn(new_angle)
            self.payload.drop()
            self.nav.scan_turn(new_angle*-1)
        self._medicine_dropped += 1

    def sweep_with_red(self,sweep_left_angle: int, sweep_right_angle: int):
        self.nav.move_forward(Config.Controller.MID_ROOM_DIST)
        for i in range(Config.Controller.TOTAL_SWEEPS):
            self.nav.move_forward(Config.Controller.HALF_BED_DIST)
            color = self.assessor.detect()
            log.info(color)
            if (color == "red"):
                break
            elif (color == "green"):
                self.drop_cube(0)
                break
            self.nav.scan_turn(sweep_left_angle)
            color = self.assessor.detect()
            log.info(color)
            if (color == "red"):
                self.nav.scan_turn(sweep_left_angle*-1)
                break
            elif (color == "green"):
                self.drop_cube(sweep_left_angle)
                break
            self.nav.scan_turn(-1*(sweep_left_angle + sweep_right_angle/2))
            color = self.assessor.detect()
            log.info(color)
            if (color == "red"):
                self.nav.scan_turn(sweep_right_angle/2)
                break
            elif (color == "green"):
                self.drop_cube(-1*sweep_right_angle/2)
                break
            self.nav.scan_turn(-1*sweep_right_angle/2)
            color = self.assessor.detect()
            log.info(color)
            if (color == "red"):
                self.nav.scan_turn(sweep_right_angle)
                break
            elif (color == "green"):
                self.drop_cube(-1*sweep_right_angle)
                break
            self.nav.scan_turn(sweep_right_angle)
        self.nav.move_backward_until_distance(Config.Controller.DOOR_EXIT_DISTANCE_CM, max_dist_cm=Config.Controller.MAX_ROOM_EXIT_DIST)
    
    def sweep_room1(self):
        self.sweep_with_red(Config.Controller.OBSTACLE_SWEEP_ANGLE, Config.Controller.SWEEP_ANGLE)
    
    def sweep_room_standard(self):
        self.sweep_with_red(Config.Controller.SWEEP_ANGLE, Config.Controller.SWEEP_ANGLE)
    
    def sweep_room4(self):
        self.sweep_with_red(Config.Controller.OBSTACLE_SWEEP_ANGLE, Config.Controller.SWEEP_ANGLE)

    def get_cube(self, from_room: int):
        if from_room == 2:
            self.nav.turn_left()
            self.nav.move_until_distance(38.9)
            self.nav.turn_left()
            self.payload.drop_clamp()
            self.payload.actually_open()
            self.nav.move_until_distance(23.7)
            self.payload.pickup()
            self.nav.move_backward_until_distance(51.8)
            self.nav.turn_left()

        elif from_room == 3:
            self.nav.turn_right()
            self.nav.move_until_distance(38.9)
            self.nav.turn_left()
            self.payload.drop_clamp()
            self.payload.actually_open()
            self.nav.move_until_distance(23.7)
            self.payload.pickup()
            self.nav.move_backward_until_distance(51.8)
            self.nav.turn_right()
    
    def return_to_pharmacy(self, from_room: int):
        # Code to return to the pharmacy after deliveries
        if from_room == 1:
            total_dist = Config.Controller.BLACK_LINE_SEGMENT + Config.Controller.HALF_BLACK_LINE_SEGMENT
            self.nav.move_backward(total_dist, assessor=self.assessor)
            self.nav.turn_right()

        elif from_room == 2:
            #self.nav.move_backward(Config.Controller.BLACK_LINE_SEGMENT, assessor=self.assessor)
            self.nav.turn_left()
            self.nav.move_forward(37)
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
    use_gyro = False #input("Use gyro? (y/n): ").strip().lower() == "y"
    left_wheel_compensation = 0 #int(input("Left wheel compensation DPS (0 = none): ").strip() or "0")
    right_wheel_compensation = 0 #int(input("Right wheel compensation DPS (0 = none): ").strip() or "0")
    controller = Controller(use_gyro=use_gyro, left_wheel_compensation=left_wheel_compensation, right_wheel_compensation=right_wheel_compensation)

    controller.collect_medicine()
    input("Press Enter to start room 1 sweep...")
    controller.sweep_room1()
    input("Continue? Press Enter to go to room 2... (dropped packets: %d)" % controller._medicine_dropped)
    
    controller.nav.turn_right(bias=-1)
    controller.go_to_room2()

    input("Continue to room2 sweep?")
    controller.nav.turn_left()
    controller.sweep_room_standard()
    picked_up = False

    if controller._medicine_dropped == 2:
        controller.get_cube(from_room=2)
        controller.go_to_room2()
        controller.sweep_room_standard()
        controller.return_to_pharmacy(from_room=2)

    elif controller._medicine_dropped == 0:
        controller.nav.turn_right(-2)

    elif controller._medicine_dropped == 1:
        controller.get_cube(from_room=2)
        picked_up = True    

    input("Continue? Press Enter to go to room 3... (dropped packets: %d)" % controller._medicine_dropped)
    controller.go_to_room3()

    input("Continue? Press Enter to start room 3 sweep... (dropped packets: %d)" % controller._medicine_dropped)
    controller.sweep_room_standard()

    if controller._medicine_dropped == 2:
        controller.return_to_pharmacy(from_room=3)
        input("Delivery complete!")
        exit(0)
    if not picked_up:
        controller.get_cube(from_room=3)
    else:
        controller.nav.turn_right()
            
    input("Continue? Press Enter to go to room 4... (dropped packets: %d)" % controller._medicine_dropped)
    controller.go_to_room4()
    input("Continue? Press Enter to start room 4 sweep... (dropped packets: %d)" % controller._medicine_dropped)
    controller.sweep_room4()

    if controller._medicine_dropped >= 0:
        controller.return_to_pharmacy(from_room=4)
        input("Delivery complete!")
        exit(0)
