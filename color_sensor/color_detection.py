#!/usr/bin/python3

import time
import numpy as np
from create_gauss import create_gaussian
from bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor
import pickle
from utils.sound import Sound
import simpleaudio as sa

WINDOW_SIZE = 250

COLOR_FILE = "detection_colors.pkl"

tone1 = Sound(duration=1.0, volume=80, pitch="C3")
tone2 = Sound(duration=1.0, volume=80, pitch="D3")
tone3 = Sound(duration=1.0, volume=80, pitch="E3")
tone4 = Sound(duration=1.0, volume=80, pitch="F3")

COLOR_TO_SOUND = {
	"red": tone1,
	"green": tone2,
	"blue": tone3,
	"yellow": tone4,
}

try:
	with open(COLOR_FILE, 'rb') as color_file:
		known_colors = pickle.load(color_file)
except Exception as e:
    print("error loading file "+ str(e))

print(known_colors)

unknown_color_data = np.zeros((3, WINDOW_SIZE))

color_sensor = EV3ColorSensor(2)
wait_ready_sensors(True)

def detect_color():#(unknown_color_data):
	global unknown_color_data
	for i in range(500):
		time.sleep(0.00001)
		rgb_values = color_sensor.get_rgb()
		if rgb_values:
			unknown_color_data = np.roll(unknown_color_data, -1, axis=1)
			red, green, blue = rgb_values
			#unknown_color_data = np.insert(unknown_color_data2, [-1], [[int(red)],[int(green)],[int(blue)]], axis=1)
			unknown_color_data[:, -1] = [int(red), int(green), int(blue)]
			#print(unknown_color_data)
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
			print("wtf")
		elif current_bhatta_dist < min_bhatta_dist:
			min_bhatta_dist = current_bhatta_dist
			min_bhatta_dist_color = key
	return  min_bhatta_dist_color #, unknown_color_data

previous_color = None

while True:
	color = detect_color()#, unknown_color_data = detect_color(unknown_color_data)
	print(color)

	if color not in COLOR_TO_SOUND:
		previous_color = None
	elif color != previous_color:
		COLOR_TO_SOUND[color].play().wait_done()
		previous_color = color


