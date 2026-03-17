import math
import time
import threading
from utils.brick import Motor, EV3GyroSensor, EV3UltrasonicSensor
import Config


class Navigator:
    def __init__(self, gyro=None, us=None):
        """
        Initialize the Navigator with motors and optional sensors.

        Args:
            gyro: An EV3GyroSensor instance, or None if not available.
            us:   An EV3UltrasonicSensor instance, or None if not available.
        """
        self.left_motor = Motor(Config.Ports.LEFT_MOTOR)
        self.right_motor = Motor(Config.Ports.RIGHT_MOTOR)

        self.gyro = gyro
        self.us = us

        # Dead-reckoned pose (x, y in cm, heading in degrees; 0 = initial forward)
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

        # Latest ultrasonic reading
        self.wall_distance = None

        # Gyro baseline: offset so heading starts at 0
        self._gyro_offset = 0.0
        if self.gyro is not None:
            initial = self.gyro.get_abs_measure()
            if initial is not None:
                self._gyro_offset = initial

        # Polling state (for passive US monitoring)
        self._polling = False
        self._poll_thread = None

    # ── Gyro helpers ─────────────────────────────────────────────────

    def _read_gyro(self):
        """Read current heading from gyro (degrees, offset-adjusted). Returns None on failure."""
        if self.gyro is None:
            return None
        reading = self.gyro.get_abs_measure()
        if reading is None:
            return None
        return reading - self._gyro_offset

    # ── Polling (passive US monitoring) ──────────────────────────────

    def _start_polling(self):
        """Start background thread to poll ultrasonic sensor."""
        if self.us is None:
            return
        self._polling = True
        self._poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        """Stop background polling thread."""
        self._polling = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None

    def _polling_loop(self):
        """Poll ultrasonic sensor at the configured interval."""
        while self._polling:
            if self.us is not None:
                dist = self.us.get_cm()
                if dist is not None:
                    self.wall_distance = dist
            time.sleep(Config.Navigation.POLL_INTERVAL_S)

    # ── Movement ─────────────────────────────────────────────────────

    def move_forward(self, distance_cm):
        """
        Move the robot forward by the given distance (in cm).

        With gyro: DPS-based control with proportional heading correction.
        Without gyro: position-relative open-loop control.
        """
        rw = Config.Navigation.WHEEL_RADIUS_CM
        target_heading = self.heading

        if self.gyro is not None:
            self._move_forward_corrected(distance_cm, target_heading, rw)
        else:
            self._move_forward_open_loop(distance_cm, rw)

        # Update dead-reckoned position using actual encoder distance
        actual_deg_left = abs(self.left_motor.get_encoder())
        actual_deg_right = abs(self.right_motor.get_encoder())
        avg_deg = (actual_deg_left + actual_deg_right) / 2
        actual_distance = (math.pi * rw * avg_deg) / 180

        heading_rad = math.radians(self.heading)
        self.x += actual_distance * math.cos(heading_rad)
        self.y += actual_distance * math.sin(heading_rad)

    def _move_forward_open_loop(self, distance_cm, rw):
        """Straight-line movement without gyro correction."""
        degrees = (180 * distance_cm) / (math.pi * rw)

        self.left_motor.set_limits(dps=Config.Navigation.SPEED_NORMAL)
        self.right_motor.set_limits(dps=Config.Navigation.SPEED_NORMAL)

        self.left_motor.reset_encoder()
        self.right_motor.reset_encoder()

        self._start_polling()

        self.left_motor.set_position_relative(degrees)
        self.right_motor.set_position_relative(degrees)

        self.left_motor.wait_is_moving()
        self.left_motor.wait_is_stopped()
        self.right_motor.wait_is_stopped()

        self._stop_polling()

    def _move_forward_corrected(self, distance_cm, target_heading, rw):
        """Straight-line movement with direct gyro heading correction."""
        target_encoder_deg = (180 * distance_cm) / (math.pi * rw)
        base_dps = Config.Navigation.SPEED_NORMAL
        kp = Config.Navigation.HEADING_CORRECTION_KP

        self.left_motor.reset_encoder()
        self.right_motor.reset_encoder()

        self._start_polling()

        while True:
            left_deg = abs(self.left_motor.get_encoder())
            right_deg = abs(self.right_motor.get_encoder())
            avg_deg = (left_deg + right_deg) / 2

            if avg_deg >= target_encoder_deg:
                break

            # Read gyro directly for responsive correction
            current_heading = self._read_gyro()
            if current_heading is not None:
                self.heading = current_heading
                heading_error = target_heading - current_heading
                correction = kp * heading_error
            else:
                correction = 0

            self.left_motor.set_dps(base_dps - correction)
            self.right_motor.set_dps(base_dps + correction)

            time.sleep(0.05)  # Tight loop for responsive correction

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        self._stop_polling()

    # ── Turning ──────────────────────────────────────────────────────

    def turn(self, angle_deg):
        """
        Rotate the robot in place by the given angle (in degrees).
        Positive = counterclockwise (left), Negative = clockwise (right).

        With gyro: closed-loop turn — spins until gyro confirms target heading.
        Without gyro: open-loop position-relative turn.
        """
        if self.gyro is not None:
            self._turn_corrected(angle_deg)
        else:
            self._turn_open_loop(angle_deg)

    def _turn_open_loop(self, angle_deg):
        """Open-loop turn using wheel encoder degrees."""
        rw = Config.Navigation.WHEEL_RADIUS_CM
        rb = Config.Navigation.TRACK_WIDTH_CM / 2
        wheel_degrees = angle_deg * (rb / rw)

        self.left_motor.set_limits(dps=Config.Navigation.SPEED_ROTATE)
        self.right_motor.set_limits(dps=Config.Navigation.SPEED_ROTATE)

        self.left_motor.set_position_relative(-wheel_degrees)
        self.right_motor.set_position_relative(wheel_degrees)

        self.left_motor.wait_is_moving()
        self.left_motor.wait_is_stopped()
        self.right_motor.wait_is_stopped()

        self.heading += angle_deg

    def _turn_corrected(self, angle_deg):
        """Closed-loop turn using gyro feedback. Spins until target heading is reached."""
        target_heading = self.heading + angle_deg
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        base_dps = Config.Navigation.SPEED_ROTATE
        kp = Config.Navigation.HEADING_CORRECTION_KP

        while True:
            current_heading = self._read_gyro()
            if current_heading is not None:
                self.heading = current_heading

            error = target_heading - self.heading

            if abs(error) <= tolerance:
                break

            # Proportional speed: fast when far, slow when close
            turn_dps = max(min(kp * error, base_dps), -base_dps)

            # Left backward, right forward for positive (CCW) rotation
            self.left_motor.set_dps(-turn_dps)
            self.right_motor.set_dps(turn_dps)

            time.sleep(0.05)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

    # ── Accessors ────────────────────────────────────────────────────

    def get_position(self):
        """Return the current estimated pose as (x, y, heading_degrees)."""
        return (self.x, self.y, self.heading)

    def get_wall_distance(self):
        """Return the latest ultrasonic distance reading (cm), or None."""
        return self.wall_distance