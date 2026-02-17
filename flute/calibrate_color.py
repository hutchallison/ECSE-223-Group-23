#!/usr/bin/python3

from create_gauss import create_gaussian
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor
import numpy as np
import pickle
import time

#add name of calibration file you would like to save your values to
COLOR_FILE = "detection_colors.pkl"

#dictionary that will hold saved gaussian distribution
#If a calibration file already exists, load it so we append/merge
try:
	with open(COLOR_FILE, 'rb') as _cf:
		detection_colors = pickle.load(_cf)
		print(f"Loaded {len(detection_colors)} color profiles from {COLOR_FILE}")
except FileNotFoundError:
	detection_colors = {}
except Exception as e:
	print(f"Warning: couldn't load {COLOR_FILE}: {e}")
	detection_colors = {}

#initializes color sensor to port 2
color_sensor = EV3ColorSensor(2)

#initializes touch sensor to port 1
touch_sensor = TouchSensor(1)

wait_ready_sensors(True) 

def collect_color_sensor_data():
	'''
	When user hits the touch sensor collects values from the color sensor
	and returns a numpy array with all red, green and blue values sampled 
	during the sampling period

	Arguments:
		None

	Returns:
		A numpy array with 3 rows for the red values, green values
		and blue values collected respectively

	'''

	#initializes local variables
	data_collected = False
	counter = 0
	red_values = []
	green_values = []
	blue_values = []

	#loop which collects data
	while not data_collected:

		#starts sampling when touch sensor is pressed
		if touch_sensor.is_pressed():
			print("Sampling started")

			while touch_sensor.is_pressed():
				time.sleep(0.1)

			#while loop collects less than or equal to 1000 values 
			while counter < 1000:
				time.sleep(0.001)
				rgb_values = color_sensor.get_rgb()

				#ensures a reading was collected from the sensor
				if rgb_values:
					red, green, blue = rgb_values

					#adds red, green and blue value of the reading to the red green and blue lists
					if red != None and green != None and blue != None:
						red_values.append(int(red))
						green_values.append(int(green))
						blue_values.append(int(blue))
						counter += 1

				#finishes sampling if touch sensor is pressed again
				if touch_sensor.is_pressed():
					print("Sampling ended with " + str(counter) + " data points")
					data_collected = True
					break

			data_collected = True
			print("sampling complete")

	#adds red, green and blue values to a numpy array with 3 rows
	color_data = np.array([red_values, green_values, blue_values])

	return color_data

def create_color_profiles():
	'''
	Creates a dictionary with keys equal to the name of the color that
	the user inputs and values equal to a dictionary with the mean and
	covarience of that color

	Arguments:
		None

	Returns:
		None

	'''
	#initializes local variables
	add_new_color = True

	#main loop that allows new colors to be added
	while add_new_color:

		#asks user if they would like to add another color to their calibration file
		add_new = input("Would you like to add a color? y/n ")

		if add_new.strip().lower() == 'y':
			color = input("Enter the name of the color: ").strip()
			print("Press touch sensor to begin sampling. Press again to stop sampling")
			
			#gets 3 row numpy array with the data collected from the color sampled
			color_data = collect_color_sensor_data()

			#calculates the means and covariance to create a gaussian distribution of the data points
			mean, cov = create_gaussian(color_data)

			#creates a dictionary with the mean and covarience values
			color_dict = {
				"mean": mean,
				"cov": cov
			}

			#adds the mean and covariance dictionary as a value with key 
			#equal to color name in the calibration dictionary
			detection_colors[color] = color_dict
			
		break

def save_detection_colors():
	'''
	Saves the calibration dictionary as a pickle file

	Arguments:
		None

	Returns: 
		None

	'''

	colors_file = open(COLOR_FILE, 'wb')
	pickle.dump(detection_colors, colors_file)
	colors_file.close()

if __name__ == "__main__":
	create_color_profiles()
	save_detection_colors()
