from utils.brick import Motor
from config import Config
import time
import logging

log = logging.getLogger(__name__)


class PayloadController:
    def __init__(self, navigator):
        self.nav = navigator
        self.clamp_motor = Motor(Config.Ports.CLAMP_MOTOR)
        self.lift_motor = Motor(Config.Ports.LIFT_MOTOR)
    
    def engage_clamp(self) -> None:
        # closes the claw
        self.clamp_motor.set_position_relative(90)
        time.sleep(0.5)
        log.info("Claw closed")

    def disengage_clamp(self) -> None:
        # opens the claw
        self.clamp_motor.set_position_relative(-90)
        time.sleep(0.5)
        log.info("Claw opened")

    def lift_clamp(self) -> None:
        self.lift_motor.set_position_relative(90)
        time.sleep(0.5)
        log.info("Claw lifted")

    def drop_clamp(self) -> None:
        self.lift_motor.set_position_relative(-90)
        time.sleep(0.5)
        log.info("Claw dropped")
        
    def pharmacy_pickup(self) -> None:
        log.info("Picking up meds from pharmacy...")
        self.drop_clamp()
        self.disengage_clamp()
        self.nav.move_forward(5)
        self.engage_clamp()
        self.lift_clamp()
        log.info("Meds picked up from pharmacy")
        
    def drop_first_med(self) -> None:
        log.info("Dropping first medicine...")
        
        # releases both medicines
        self.drop_clamp()
        self.disengage_clamp()
        # moves the robot backwards & nudges the second block to the right
        self.nav.move_forward(-5)
        self.nav.turn(-15)
        # picks up second medicine & returns to original orientation
        self.engage_clamp()
        self.lift_clamp()
        self.nav.turn(15)
        
        log.info("Dropped first medicine")
        
    def drop_second_med(self) -> None:
        log.info("Dropping second medicine...")
        # releases second medicine
        self.drop_clamp()
        self.disengage_clamp()
        log.info("Dropped second medicine")