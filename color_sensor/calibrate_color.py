#!/usr/bin/python3

from create_gauss import create_gaussian
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor
import numpy as np
import pickle
import time

COLOR_FILE = "dummy"

detection_colors = {}

color_sensor = EV3ColorSensor(2)
touch_sensor = TouchSensor(1)

wait_ready_sensors(True) 

def collect_color_sensor_data():
	data_collected = False
	counter = 0
	red_values = []
	green_values = []
	blue_values = []
	while not data_collected:
		if touch_sensor.is_pressed():
			print("Sampling started")
			while touch_sensor.is_pressed():
				time.sleep(0.1)
			while counter < 1000:
				time.sleep(0.001)
				rgb_values = color_sensor.get_rgb()
				if rgb_values:
					red, green, blue = rgb_values
					if red != None and green != None and blue != None:
						red_values.append(int(red))
						green_values.append(int(green))
						blue_values.append(int(blue))
						counter += 1
				if touch_sensor.is_pressed():
					print("Sampling ended with " + str(counter) + " data points")
					data_collected = True
					break
			data_collected = True
			print("sampling complete")
	color_data = np.array([red_values, green_values, blue_values])
	return color_data

def create_color_profiles():
	add_new_color = True
	while add_new_color:
		add_new = input("Would you like to add a color? y/n ")
		if add_new == ('y' or 'Y'):
			color = input("What color would you like to sample? ")
			print("Press touch sensor to begin sampling. Press again to stop sampling")
			color_data = collect_color_sensor_data()
			mean, cov = create_gaussian(color_data)
			color_dict = {
				"mean": mean,
				"cov": cov
			}
			detection_colors[color] = color_dict
		else:
			add_new_color = False

def save_detection_colors():
	colors_file = open(COLOR_FILE, 'wb')
	pickle.dump(detection_colors, colors_file)
	colors_file.close()

if __name__ == "__main__":
	create_color_profiles()
	save_detection_colors()
