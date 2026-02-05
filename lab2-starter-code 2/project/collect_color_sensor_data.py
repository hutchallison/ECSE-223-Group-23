#!/usr/bin/env python3

"""
This test is used to collect data from the color sensor.
It must be run on the robot.
"""

# Add your imports here, if any
from utils.brick import EV3ColorSensor, wait_ready_sensors, TouchSensor
import time

COLOR_SENSOR_DATA_FILE = "../data_analysis/color_sensor.csv"

# complete this based on your hardware setup
color_sensor = EV3ColorSensor(2)
touch_sensor = TouchSensor(1)

wait_ready_sensors(True) # Input True to see what the robot is trying to initialize! False to be silent.

def collect_color_sensor_data():
    "Collect color sensor data."
    print("# COLOR SENSOR DATA COLLECTION INTIALIZED #")
    print("Press touch sensor to record a new reading.")
    print("Press Ctrl+C to stop.")

    # Open the file in append mode to create the file if it doesn't exist, or add to it if it does.
    with open(COLOR_SENSOR_DATA_FILE, "a") as csv_file:
        # Write the header to the file if it's new.
        if csv_file.tell() == 0:
            csv_file.write("red,green,blue\n")

        try:
            # Use a while loop to continuously check for touch sensor presses.
            counter = 0
            while True:
                # Check if the touch sensor is pressed.
                if touch_sensor.is_pressed():
                    # Read the RGB values from the color sensor.
                    rgb_values = color_sensor.get_rgb()
                    
                    if rgb_values:
                        red, green, blue = rgb_values
                        print(f"Trial {counter} results:")
                        print(f"R: {red}, G: {green}, B: {blue}")

                        # Write the values to the CSV file.
                        csv_file.write(f"{red},{green},{blue}\n")
                        csv_file.flush()

                    # Wait until the touch sensor is released to allow only one reading at a time.
                    while touch_sensor.is_pressed():
                        time.sleep(0.1)
    
                    counter += 1

        except KeyboardInterrupt:
            print("Exiting reading...")
        finally:
            print(f"Data was succesfully saved to {COLOR_SENSOR_DATA_FILE}!")

if __name__ == "__main__":
    collect_color_sensor_data()
