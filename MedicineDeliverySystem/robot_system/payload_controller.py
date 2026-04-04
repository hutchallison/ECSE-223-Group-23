#!/usr/bin/python3



from utils.brick import sys
from config import Config
import time
import logging
from navigator import Navigator
from utils.brick import Motor



class PayloadController:
    def __init__(self, navigator):
        self.nav = navigator
        self.clamp_motor = Motor(Config.Ports.CLAMP_MOTOR)
        self.lift_motor = Motor(Config.Ports.LIFT_MOTOR)
        self.clamp_motor.reset_encoder()
        self.clamp_motor.reset_position()
        self.lift_motor.reset_encoder()
        self.lift_motor.reset_position()
    
    def engage_clamp(self) -> None:
        # closes the claw
        self.clamp_motor.set_position_relative(Config.Payload.CLAMP_CLOSE_DEG)
        time.sleep(Config.Payload.ENGAGE_SLEEP_S)
        #log.info("Claw closed")

    def actually_open(self) -> None:
        self.clamp_motor.set_position_relative(-Config.Payload.CLAMP_CLOSE_DEG + 5)
        time.sleep(Config.Payload.DISENGAGE_SLEEP_S)

    def disengage_clamp(self) -> None:
        # opens the claw
        self.clamp_motor.set_position_relative(Config.Payload.CLAMP_OPEN_DEG)
        time.sleep(Config.Payload.DISENGAGE_SLEEP_S)
        #log.info("Claw opened")

    def lift_clamp(self) -> None:
        self.lift_motor.set_position(Config.Payload.LIFT_UP_POS)
        time.sleep(Config.Payload.LIFT_SLEEP_S)
        #log.info("Claw lifted")

    def drop_clamp(self) -> None:
        self.lift_motor.set_position(Config.Payload.LIFT_DOWN_POS)
        time.sleep(Config.Payload.DROP_SLEEP_S)
        #log.info("Claw dropped")
        
    def pharmacy_pickup(self) -> None:
        #log.info("Picking up meds from pharmacy...")
        #self.drop_clamp()
        self.disengage_clamp()
        self.nav.move_forward(Config.Payload.PHARMACY_FORWARD_CM)
        self.engage_clamp()
        self.lift_clamp()
        self.nav.move_backward(Config.Payload.PHARMACY_FORWARD_CM - Config.Controller.HALF_BED_DIST)
        #log.info("Meds picked up from pharmacy")
        
    def drop_first_med(self) -> None:
       # log.info("Dropping first medicine...")
        
        # releases both medicines
        self.drop_clamp()
        self.disengage_clamp()
        # moves the robot backwards & nudges the second block to the right
        self.nav.move_backward(Config.Payload.DROP_FIRST_BACKUP_CM)
        self.nav.turn(-Config.Payload.DROP_FIRST_NUDGE_DEG)
        # picks up second medicine & returns to original orientation
        self.engage_clamp()
        self.lift_clamp()
        self.nav.turn(Config.Payload.DROP_FIRST_NUDGE_DEG)
        
        #log.info("Dropped first medicine")
        
    def drop_second_med(self) -> None:
        #log.info("Dropping second medicine...")
        # releases second medicine
        self.drop_clamp()
        self.disengage_clamp()
        self.nav.move_backward(Config.Payload.DROP_SECOND_BACKUP_CM)
        self.engage_clamp()
        self.lift_clamp()
        #log.info("Dropped second medicine")
    def drop(self) -> None:
        self.drop_clamp()
        self.disengage_clamp()
        time.sleep(0.5)
        self.lift_clamp()
        self.engage_clamp()
    def pickup(self) -> None:
        self.engage_clamp()
        self.lift_clamp()		
if __name__ =="__main__" :
    nav = Navigator()
    self = PayloadController(nav)
    self.drop_clamp()
    self.disengage_clamp()
    '''self.disengage_clamp()
    time.sleep(1.5)
    self.engage_clamp()
    self.lift_clamp()
    time.sleep(1)
    self.drop_one()
    
	nav = Navigator(gyro=gyro)
	pc = PayloadController(nav)
	pc.pharmacy_pickup()
	time.sleep(1)
	pc.drop_first_med()
'''
