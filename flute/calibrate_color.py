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


def _merge_gaussians(mu1, cov1, n1, mu2, cov2, n2):
	"""Merge two sample Gaussians (means + sample covariances).

	Returns (mu, cov, total_n).
	"""
	mu1 = np.asarray(mu1)
	mu2 = np.asarray(mu2)
	cov1 = np.asarray(cov1)
	cov2 = np.asarray(cov2)

	total_n = int(n1 + n2)
	if total_n <= 1:
		return mu2, cov2, int(n2)

	mu = (n1 * mu1 + n2 * mu2) / total_n

	S1 = (n1 - 1) * cov1
	S2 = (n2 - 1) * cov2

	d1 = (mu1 - mu).reshape(-1, 1)
	d2 = (mu2 - mu).reshape(-1, 1)

	S = S1 + S2 + n1 * (d1 @ d1.T) + n2 * (d2 @ d2.T)
	cov = S / (total_n - 1)

	return mu, cov, total_n

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
			n_new = int(color_data.shape[1])

			#calculates the means and covariance to create a gaussian distribution of the data points
			mean_new, cov_new = create_gaussian(color_data)

			#entry with sample count
			color_entry = {"mean": mean_new, "cov": cov_new, "n": n_new}

			if color in detection_colors:
				existing = detection_colors[color]
				mu_old = existing.get("mean")
				cov_old = existing.get("cov")
				n_old = existing.get("n")

				if mu_old is None or cov_old is None:
					# unexpected format — overwrite
					detection_colors[color] = color_entry
					print(f"Overwrote '{color}' (existing profile had unexpected format)")
				else:
					if n_old is None:
						# best-effort fallback for legacy entries
						n_old = 1000
						print(f"Merging '{color}': existing profile lacked sample count — assuming n_old=1000")

					mu_merged, cov_merged, n_total = _merge_gaussians(mu_old, cov_old, int(n_old), mean_new, cov_new, int(n_new))
					detection_colors[color] = {"mean": mu_merged, "cov": cov_merged, "n": n_total}
					print(f"Merged '{color}' (n_old={n_old}, n_new={n_new} => n_total={n_total})")
			else:
				detection_colors[color] = color_entry

		# continue loop (user can add multiple colors)
		# loop will continue until user answers 'n'


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
