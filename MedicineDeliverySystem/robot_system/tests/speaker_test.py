#!/usr/bin/python3
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.brick import EV3ColorSensor, wait_ready_sensors
from utils.sound import Sound

def main():
	print("color detection started")	
	color_sensor = EV3ColorSensor(3)
	color_sensor.set_mode("id")
	success_sound = Sound(duration=1.0, volume=80, pitch="A4")

	wait_ready_sensors()

	try:
		while True:
			if color_sensor.get_value() == 3:
				print("detected green")
				success_sound.play()
				success_sound.wait_done()
                
			time.sleep(0.1)
            
	except KeyboardInterrupt:
		pass

if __name__ == "__main__":
    main()
