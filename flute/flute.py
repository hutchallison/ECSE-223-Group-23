#!/usr/bin/python3

import time
import numpy as np
from create_gauss import create_gaussian
from bhatta_dist import bhatta_distance
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor, Motor
import pickle
from utils.sound import Sound
import simpleaudio as sa

#emegency button initializer
EmergencyButton = TouchSensor(4)

#drums initializer
motor = Motor("C")
motor.reset_encoder()

#drum button initializer
drums_button = TouchSensor(3)

#color sensor initializer
color_sensor = EV3ColorSensor(2)


#initializes window size for color sensor data
WINDOW_SIZE = 500

#name of color calibration file to use
COLOR_FILE = "detection_colors.pkl"


#creates 4 tone variables for the flute to play
tone1 = Sound(duration=1.0, volume=100, pitch="C4")
tone2 = Sound(duration=1.0, volume=100, pitch="D4")
tone3 = Sound(duration=1.0, volume=100, pitch="E4")
tone4 = Sound(duration=1.0, volume=100, pitch="G4")

#dictionary with colors and matching tones
COLOR_TO_SOUND = {
	"red": tone1,
	"green": tone2,
	"blue": tone3,
	"yellow": tone4,
}


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

#initializes main loop variables
previous_color = None
is_drumming = False


#main loop which stops when emergency button is pressed

while not EmergencyButton.is_pressed():	
	#gets color data
	color = detect_color()

	#Plays sound if color is associated with a note 
	if color not in COLOR_TO_SOUND:
		previous_color = None
	elif color != previous_color:
		COLOR_TO_SOUND[color].play()
		previous_color = color

	#Starts and stops drum based on button presses
	if drums_button.is_pressed(): 
		if not is_drumming:
			is_drumming = not is_drumming
			motor.set_power(75)

		elif is_drumming:
			motor.set_power(0)
			is_drumming = not is_drumming

print("Emergency Stop!")
exit()

