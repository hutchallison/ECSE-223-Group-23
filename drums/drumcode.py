#!/usr/bin/python3




import time
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor, Motor, SensorError, BP

motor = Motor("C")
print("drums on")
motor.set_limits(power=50)
motor.reset_encoder()
TouchSensor = TouchSensor(3)
wait_ready_sensors()
is_drumming = False

while True:
	if TouchSensor.is_pressed() == True:
		is_drumming = not is_drumming
		time.sleep(1) 
	if is_drumming:
		motor.set_power(40)
		time.sleep(0.5)

	if not is_drumming:
		motor.set_power(0)
