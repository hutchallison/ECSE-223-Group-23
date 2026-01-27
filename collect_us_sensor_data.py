#!/usr/bin/env python3

"""
This test is used to collect data from the ultrasonic sensor.
It must be run on the robot.
"""

from utils import sound
from utils.brick import TouchSensor, EV3UltrasonicSensor, wait_ready_sensors, reset_brick
from time import sleep
import time


DELAY_SEC = 0.01  # seconds of delay between measurements
US_SENSOR_DATA_FILE = "../data_analysis/us_sensor.csv"
TIME_DATA = "../data_analysis/us_time.csv"
SOUND = sound.Sound(duration=0.3, pitch="A4", volume=60)

print("Program start.\nWaiting for sensors to turn on...")

TOUCH_SENSOR = TouchSensor(1)
US_SENSOR = EV3UltrasonicSensor(2)


wait_ready_sensors(True) # Input True to see what the robot is trying to initialize! False to be silent.
print("Done waiting.")


def collect_continuous_us_data():
    "Collect continuous data from the ultrasonic sensor between two button presses."
    try:
        output_file = open(US_SENSOR_DATA_FILE, "w")
        time_file = open(TIME_DATA, "w")
        while not TOUCH_SENSOR.is_pressed():
            pass  # do nothing while waiting for first button press
        print("Touch sensor pressed")
        sleep(1)
        print("Starting to collect US distance samples")
        sample_count = 0
        while not TOUCH_SENSOR.is_pressed():
        
            start = time.time()
            us_data = US_SENSOR.get_value()  # Float value in centimeters 0, capped to 255 cm
            total = time.time() - start

            if us_data is not None: # If None is given, then data collection failed that time
                print(us_data, total)
                output_file.write(f"{us_data}\n")
                time_file.write(f"{total:.3f}\n")
                sample_count += 1

            sleep(DELAY_SEC)
    except BaseException as e:  # capture all :exceptions including KeyboardInterrupt (Ctrl-C)
        print(f"Error: {e}")
        pass
    finally:
        print("Done collecting US distance samples")

        output_file.close()
        time_file.write(f"{sample_count}")
        time_file.close()
        reset_brick() # Turn off everything on the brick's hardware, and reset it
        exit()

if __name__ == "__main__":
    collect_continuous_us_data()
