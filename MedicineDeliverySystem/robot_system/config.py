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
        TRACK_WIDTH_CM = 15.5           # Full wheel-to-wheel distance (Navigator divides by 2)

        # Motor polarity: set to -1 if that motor spins physically backwards
        LEFT_MOTOR_POLARITY  = -1
        RIGHT_MOTOR_POLARITY = -1
        # Circumference formula (logic allowed in Python config!)
        WHEEL_CIRCUMFERENCE = 2 * 3.14159 * WHEEL_RADIUS_CM
        
        # Speeds (Degrees Per Second)
        SPEED_NORMAL = 300
        SPEED_ROTATE = 150
        SPEED_ROTATE_ADJUST = 50        # Slow scan/trim speed — lower = less vibration-induced gyro drift

        # PID turn controller (used by _pid_rotate, turn_to_heading)
        TURN_KP = 3.0           # dps per degree of error
        TURN_KI = 0.01          # integral: corrects steady-state stall near target
        TURN_KD = 0.1           # derivative: brakes naturally as error shrinks → less coast
        TURN_MIN_DPS = 30       # floor: below this motors stall; also limits coast

        # Scan-turn coast compensation: stop this many degrees early so coast
        # lands within tolerance. Measure from logs at current SPEED_ROTATE_ADJUST.
        SCAN_TURN_COAST_DEG = 1.5

        # Tolerances
        STOP_DISTANCE_CM = 5.0  # Wall avoidance threshold
        OBSTACLE_STOP_CM = 10.0  # Emergency stop distance during move_forward (cm)

        # Sensor feedback
        POLL_INTERVAL_S = 0.5       # Polling rate for gyro/US sensors
        HEADING_CORRECTION_KP = 2.0 # Proportional gain: heading error (deg) -> DPS offset
        TURN_TOLERANCE_DEG = 1.0    # Stop turning when within this many degrees of target
        GYRO_SCALE_RIGHT = 1.8000
        GYRO_SCALE_LEFT = 1.7647           # Gyro angle scale factor (adjust if gyro is inaccurate)

    class Payload:
        # Clamp Positions (Degrees, relative)
        CLAMP_CLOSE_DEG = 110        # degrees to close the clamp
        CLAMP_OPEN_DEG  = -90        # degrees to open the clamp (reverse close)

        # Lift Positions (Degrees, absolute)
        LIFT_UP_POS  = -15           # absolute encoder position for raised lift
        LIFT_DOWN_POS = 15           # absolute encoder position for lowered lift

        # Sleep durations (seconds)
        ENGAGE_SLEEP_S    = 0.5      # wait after closing clamp
        DISENGAGE_SLEEP_S = 1.0      # wait after opening clamp
        LIFT_SLEEP_S      = 1.0      # wait after raising lift
        DROP_SLEEP_S      = 0.5      # wait after lowering lift

        # Movement distances (cm)
        PHARMACY_FORWARD_CM   = 15   # drive into pharmacy to grab meds
        DROP_FIRST_BACKUP_CM  = 3    # backup before nudging second block
        DROP_FIRST_NUDGE_DEG  = 15   # angle to nudge second block sideways
        DROP_SECOND_BACKUP_CM = 5    # backup after releasing second med

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
    
    class Controller:
        EXIT_ROOM_DIST = 28.5
        HALF_BLACK_LINE_SEGMENT = 11.3  # cm to move forward after detecting black line (half of BLACK_LINE_SEGMENT)
        BLACK_LINE_SEGMENT = 24.4
        S1_SEGMENT3 = 16  # cm to move forward in segment 3 (to patient room)

        S2_SEGMENT1 = 18  # cm to move forward in segment 1 (to patient room)
        S2_SEGMENT2 = 24.8  # cm to move forward in segment 2

        ROOM_SWEEP_LENGTH = 20 # cm to sweep across room for obstacle detection
        SWEEP_DIFF = 5 # cm to move forward/backward during sweep turns

        # Angular sweep (room 1 redesign)
        OBSTACLE_SWEEP_ANGLE = 13           # degrees CCW from entry heading
        SWEEP_ANGLE = 30          # degrees CW from entry heading
        HALF_BED_DIST = 6               # cm nudge forward when no bed detected
        SWEEP_BACKUP_TO_DROP_DIST = 4
        TOTAL_SWEEPS = 3                # Number of times to repeat sweep if no bed found
        MID_ROOM_DIST = 15              # cm to move forward into room before sweeping
        BIAS = 0
        MAX_ROOM_EXIT_DIST = 60         # safety cap for move_until_distance room exit (cm)
        DOOR_EXIT_DISTANCE_CM = 50      # US distance (cm) that indicates robot is at/past the door

        DISTANCE_ROOM4_WALL = 95