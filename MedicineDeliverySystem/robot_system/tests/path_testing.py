#!/usr/bin/python3

import sys
import os
import time
import numpy as np
import threading
import pickle
import simpleaudio as sa

current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)  # .../robot_system
if project_dir not in sys.path:
	sys.path.append(project_dir)

from color_detection.create_gauss import create_gaussian
from color_detection.bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor, Motor
from utils.sound import Sound
from navigator import Navigator

nav = Navigator()
color_sensor = EV3ColorSensor(3)
WINDOW_SIZE = 500
COLOR_FILE = "test.pkl" #os.path.join(project_dir, "color_detection", "final_project.cal")

tone1 = Sound(duration=1.0, volume=100, pitch="C4")
tone2 = Sound(duration=1.0, volume=100, pitch="G4")

COLOR_TO_SOUND = {
	"green": tone2,
}

try:
	with open(COLOR_FILE, 'rb') as color_file:
		known_colors = pickle.load(color_file)
except Exception as e:
    print("error loading file "+ str(e))

unknown_color_data = np.zeros((3, WINDOW_SIZE))
wait_ready_sensors(True)

def detect_color():
	global unknown_color_data

	for i in range(WINDOW_SIZE//4):
		time.sleep(0.00001)
		rgb_values = color_sensor.get_rgb()
	
		if rgb_values:
			unknown_color_data = np.roll(unknown_color_data, -1, axis=1)
			red, green, blue = rgb_values
			unknown_color_data[:, -1] = [int(red), int(green), int(blue)]
	
	mean1, cov1 = create_gaussian(unknown_color_data)

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


current_color = None
color_lock = threading.Lock()
running = True 

def color_worker():
    global current_color, running
    while running:
        detected = detect_color()
        with color_lock:
            current_color = detected

color_thread = threading.Thread(target=color_worker, daemon=True)
color_thread.start()

previous_color = None

nav.move_forward(60)

try:
	while True:
		time.sleep(0.1)
		
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
			nav.move_forward(1)	

finally:
	running = False
