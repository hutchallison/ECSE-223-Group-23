class Config:
    """Centralized configuration for Group 23 Medical Delivery System."""

    class Ports:
        # Sensors (S1-S4)
        COLOR = 3
        ULTRASONIC = 1
        GYRO = 4
        TOUCH = 2
        
        # Motors (A-D)
        LEFT_MOTOR = "A"
        RIGHT_MOTOR = "D"
        CLAMP_MOTOR = "C"
        LIFT_MOTOR = "B"

    class Navigation:
        # Physical Measurements
        WHEEL_RADIUS_CM = 4.2/2          # Wheel radius (half of 4.2 cm diameter)
        TRACK_WIDTH_CM = 15.6            # Full wheel-to-wheel distance (Navigator divides by 2)

        # Motor polarity: set to -1 if that motor spins physically backwards
        LEFT_MOTOR_POLARITY  = -1
        RIGHT_MOTOR_POLARITY = -1
        # Circumference formula (logic allowed in Python config!)
        WHEEL_CIRCUMFERENCE = 2 * 3.14159 * WHEEL_RADIUS_CM
        
        # Speeds (Degrees Per Second)
        SPEED_NORMAL = 300
        SPEED_ROTATE = 150
        
        # Tolerances
        STOP_DISTANCE_CM = 5.0  # Wall avoidance threshold

        # Sensor feedback
        POLL_INTERVAL_S = 0.5       # Polling rate for gyro/US sensors
        HEADING_CORRECTION_KP = 2.0 # Proportional gain: heading error (deg) -> DPS offset
        TURN_TOLERANCE_DEG = 1.0    # Stop turning when within this many degrees of target

    class Payload:
        # Clamp Positions (Degrees)
        CLAMP_OPEN = 0
        CLAMP_CLOSED = 90
        CLAMP_GRAB_STRENGTH = 75 # Power limit

    class Colors:
        # Mappings from your flute training
        PHARMACY = "BLUE"
        PATIENT_NEED = "GREEN"
        PATIENT_HEALTHY = "RED"
        PATIENT_ROOM = "YELLOW"
        DOOR_MARKER = "ORANGE"

    class Audio:
        FILE_DELIVERY = "delivery_confirmed.wav"
        FILE_START = "mission_start.wav"
        FILE_COMPLETE = "victory.wav"
    
    class Logging:
        LOG_FILE = "robot_log.txt"
        LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
        LOG_FREQUENCY = 2.0  # Seconds between periodic in-motion debug logs