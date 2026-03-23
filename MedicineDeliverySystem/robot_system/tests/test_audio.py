import sys
import logging
import time
import sys
import os

# Get the directory of the current file (tests/), then go up one level to robot_system/
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Add the parent directory to Python's search path
sys.path.append(parent_dir)

# NOW you can import your classes safely
from audio_controller import AudioController
from config import Config


