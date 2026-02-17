#!/usr/bin/python3




import time
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor, Motor, SensorError, BP

motor = Motor("C")
print("drums initialized")
motor.set_limits(power=50)
motor.reset_encoder()
TouchSensor = TouchSensor(3)
wait_ready_sensors()
is_drumming = False

while True:
	if TouchSensor.is_pressed() == True and not is_drumming:
		is_drumming = not is_drumming
		motor.set_power(50)
		print("Drums ON")
		time.sleep(0.5)

	if  TouchSensor.is_pressed() == True and is_drumming:
		motor.set_power(0)
		print("Drums OFF")
		is_drumming = not is_drumming
		time.sleep(0.5)
