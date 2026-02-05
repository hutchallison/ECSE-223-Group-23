#!/usr/bin/env python3
import numpy as np
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor
import time

color_sensor = EV3ColorSensor(2)
touch_sensor = TouchSensor(1)
COLOR_SENSOR_DATA_FILE = "../data_analysis/"

def collect_color_sensor_data():
    print("# COLOR SENSOR DATA COLLECTION INTIALIZED #")
    print("Press touch sensor to record a new reading.")
    print("Press Ctrl+C to stop.")
    if touch_sensor.is_pressed():
        red_red = np.array([])
        red_green = np.array([])
        red_blue = np.array([])
        for i in range(0,100):
                rgb_values = color_sensor.get_rgb()
                if rgb_values:
                    red, green, blue = rgb_values
                    red_red = np.append(red_red, red)
                    red_green = np.append(red_green, green)
                    red_blue = np.append(red_blue, blue)
                    time.sleep(0.1)
                    
        np.save(COLOR_SENSOR_DATA_FILE + 'red_red.npy', red_red)
        np.save(COLOR_SENSOR_DATA_FILE + 'red_blue.npy', red_blue)
        np.save(COLOR_SENSOR_DATA_FILE + 'red_green.npy', red_green)
        print(f"Data was successfully saved to {COLOR_SENSOR_DATA_FILE}!")

if __name__ == "__main__":
    collect_color_sensor_data()
