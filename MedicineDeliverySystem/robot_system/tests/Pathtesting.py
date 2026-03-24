#!/usr/bin/python3

import time
import numpy as np
import threading # <-- 1. Import threading
from create_gauss import create_gaussian
from bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor, Motor
import pickle
from utils.sound import Sound
import simpleaudio as sa
from navigator import Navigator

nav = Navigator()

#color sensor initializer
color_sensor = EV3ColorSensor(3)

#initializes window size for color sensor data
WINDOW_SIZE = 500

#name of color calibration file to use
COLOR_FILE = "final_project.cal"

#creates 2 tone variables for the flute to play
tone1 = Sound(duration=1.0, volume=100, pitch="C4")
tone2 = Sound(duration=1.0, volume=100, pitch="G4")

#dictionary with colors and matching tones
COLOR_TO_SOUND = {
#	"red": tone1,
	"green": tone2,
}

#imports color calibration file
try:
	with open(COLOR_FILE, 'rb') as color_file:
		known_colors = pickle.load(color_file)
except Exception as e:
    print("error loading file "+ str(e))

#initializes numpy array which holds the most recent data
unknown_color_data = np.zeros((3, WINDOW_SIZE))

#initializes sensors
wait_ready_sensors(True)


def detect_color():
	'''
	Collects 500 data samples in sliding window creates a Gaussian...
	'''
	global unknown_color_data

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
	
	return min_bhatta_dist_color

# --- 2. THREADING SETUP ---
current_color = None
color_lock = threading.Lock()
running = True 

def color_worker():
    """Background thread function that constantly updates the current color."""
    global current_color, running
    while running:
        detected = detect_color()
        # Securely update the shared variable
        with color_lock:
            current_color = detected

# Start the background thread
color_thread = threading.Thread(target=color_worker, daemon=True)
color_thread.start()
# --------------------------

#initializes main loop variables
previous_color = None

nav.move_forward(60)

try:
	while True:
		time.sleep(0.1)
		
		# 3. Securely read the latest color from the background thread
		with color_lock:
			color = current_color
			
		print(color)
		
		if color == "green":
			print("green")
			tone1.play()
			tone1.wait_done()
			break
		elif color == "red":
			print("red")
			nav.move_backward(30)
			break
		else:
			# nav.move_forward(3)
			pass

finally:
	# Clean up thread on exit
	running = False