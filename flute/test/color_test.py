#!/usr/bin/python3

import time
import csv
import os
import sys
import numpy as np

# Add project root (ECSE-223-Group-23/) to sys.path so 'flute' package is found
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
	sys.path.insert(0, project_root)

# package-style imports — run as module (python -m flute.test.color_test)
from flute.create_gauss import create_gaussian
from flute.bhatta_dist import bhatta_distance
from flute.utils.brick import EV3ColorSensor, TouchSensor, wait_ready_sensors
import pickle


#color sensor initializer
color_sensor = EV3ColorSensor(2)
EmergencyButton = TouchSensor(4)

timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())

#initializes window size for color sensor data
WINDOW_SIZE = 500

#name of color calibration file to use (path relative to package root)
PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))
COLOR_FILE = os.path.join(PACKAGE_ROOT, 'detection_colors.pkl')

# store test output in a dedicated data folder and ensure it exists
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
COLOR_COLLECTION_FILE = os.path.join(DATA_DIR, f"detection_colors_collection_{timestamp}.csv")

NUM_DATA_POINTS = 500


#imports color calibration file
try:
	with open(COLOR_FILE, 'rb') as color_file:
		known_colors = pickle.load(color_file)
except Exception as e:
    print("error loading file "+ str(e))

#initializes numpy array which holds the most recent data
#obtained from the color sensor in the data window range
unknown_color_data = np.zeros((3, WINDOW_SIZE))

#initializes sensors
wait_ready_sensors(True)


def detect_color():
	'''
	Collects 500 data samples in sliding window creates a Gaussian
	of the unknow sample and calculates the Bhattacharyya distance 
	between the Gaussian distributions saved in the color calibration
	file and the unknown Gaussian distribution. Returns the name of 
	the color with the closet Bharracharyya distance in the calibration
	dictionary
	
	Arguments:
		None
	
	Returns:
		String name of the closest color 

	'''

	#accesses the sliding window of data
	global unknown_color_data

	#resets the sliding window to avoid stale data
	unknown_color_data = np.zeros((3, WINDOW_SIZE))

	#Collects data points and adds the to the sliding window of data
	for i in range(WINDOW_SIZE//4):
		time.sleep(0.00001)
		rgb_values = color_sensor.get_rgb()
	
		if rgb_values:
			unknown_color_data = np.roll(unknown_color_data, -1, axis=1)
			red, green, blue = rgb_values
			unknown_color_data[:, -1] = [int(red), int(green), int(blue)]
	
	#Creates a gaussian with the sliding window data
	mean1, cov1 = create_gaussian(unknown_color_data)

	#initializes minimum distance and color with minimum distance
	min_bhatta_dist = None
	min_bhatta_dist_color = None

	#iterates through the colors in the calibration dictionary and
	#finds the color with the minimum distance
	for key in known_colors:
		mean2 = known_colors[key]["mean"]
		cov2 = known_colors[key]["cov"]
		current_bhatta_dist = bhatta_distance(mean1, cov1, mean2, cov2)

		if min_bhatta_dist is None:
			min_bhatta_dist = current_bhatta_dist
			min_bhatta_dist_color = key

		elif current_bhatta_dist is None:
			pass

		elif current_bhatta_dist < min_bhatta_dist:
			min_bhatta_dist = current_bhatta_dist
			min_bhatta_dist_color = key
	
	return  min_bhatta_dist_color


# Initialize CSV file with headers
with open(COLOR_COLLECTION_FILE, 'w', newline='') as f:
	writer = csv.writer(f)
	writer.writerow(['Expected Color', 'Brightness', 'Detected Color'])

while True:
	# Prompt user for expected color
	expected_color = input("Enter expected color (or 'quit' to exit): ").strip()
	if expected_color.lower() == 'quit':
		break

	# Prompt user for brightness level
	brightness = input("Enter brightness level (small/medium/high): ").strip().lower()
	if brightness not in ['small', 'medium', 'high']:
		print("Invalid brightness level. Please enter 'small', 'medium', or 'high'.")
		continue

	print(f"Collecting {NUM_DATA_POINTS} detections for {expected_color} ({brightness})...")

	for i in range(NUM_DATA_POINTS):
		detected_color = detect_color()

		with open(COLOR_COLLECTION_FILE, 'a', newline='') as f:
			writer = csv.writer(f)
			writer.writerow([expected_color, brightness, detected_color])

		if (i + 1) % 100 == 0:
			print(f"  {i + 1}/{NUM_DATA_POINTS} done...")

		if EmergencyButton.is_pressed():
			print("Emergency stop triggered!")
			break

	if EmergencyButton.is_pressed():
		break

	print(f"Done collecting for {expected_color} ({brightness}).")

print("Data collection completed!")