import math
import time
import logging
from utils.brick import Motor, EV3GyroSensor, EV3UltrasonicSensor
import Config

log = logging.getLogger(__name__)


class Navigator:
    def __init__(self, gyro=None, us=None):
        self.left_motor = Motor(Config.Ports.LEFT_MOTOR)
        self.right_motor = Motor(Config.Ports.RIGHT_MOTOR)
        self.gyro = gyro
        self.us = us

        # Dead-reckoned pose (x, y in cm, heading in degrees)
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

        # Gyro baseline so heading starts at 0
        self._gyro_offset = 0.0
        if self.gyro is not None:
            initial = self.gyro.get_abs_measure()
            if initial is not None:
                self._gyro_offset = initial

        log.info("Navigator init | gyro=%s us=%s gyro_offset=%.1f",
                 gyro is not None, us is not None, self._gyro_offset)

    # ── Sensors ──────────────────────────────────────────────────────

    def _read_gyro(self):
        """Read current heading from gyro (offset-adjusted). Returns None if unavailable."""
        if self.gyro is None:
            return None
        reading = self.gyro.get_abs_measure()
        if reading is None:
            log.warning("Gyro read returned None")
            return None
        return reading - self._gyro_offset

    def get_wall_distance(self):
        """Read ultrasonic distance (cm) on demand. Returns None if unavailable."""
        if self.us is None:
            return None
        dist = self.us.get_cm()
        log.debug("US distance: %s cm", dist)
        return dist

    # ── Movement ─────────────────────────────────────────────────────

    def move_forward(self, distance_cm):
        """
        Move forward by distance_cm. Uses gyro for heading correction if available,
        otherwise drives straight open-loop via set_dps.
        """
        log.info("move_forward %.1f cm | pos=(%.1f, %.1f) heading=%.1f",
                 distance_cm, self.x, self.y, self.heading)

        rw = Config.Navigation.WHEEL_RADIUS_CM
        target_encoder_deg = (180 * distance_cm) / (math.pi * rw)
        base_dps = Config.Navigation.SPEED_NORMAL
        kp = Config.Navigation.HEADING_CORRECTION_KP
        target_heading = self.heading

        self.left_motor.reset_encoder()
        self.right_motor.reset_encoder()

        last_log_time = time.time()

        while True:
            left_deg = abs(self.left_motor.get_encoder())
            right_deg = abs(self.right_motor.get_encoder())
            avg_deg = (left_deg + right_deg) / 2

            if avg_deg >= target_encoder_deg:
                break

            correction = 0
            current_heading = self._read_gyro()
            if current_heading is not None:
                self.heading = current_heading
                correction = kp * (target_heading - current_heading)

            self.left_motor.set_dps(base_dps - correction)
            self.right_motor.set_dps(base_dps + correction)

            # Log position every 2 seconds
            now = time.time()
            if now - last_log_time >= Config.Logging.LOG_FREQUENCY:
                progress = (avg_deg / target_encoder_deg) * 100
                log.debug("moving | progress=%.0f%% heading=%.1f correction=%.1f encoders=(%.0f, %.0f)",
                          progress, self.heading, correction, left_deg, right_deg)
                last_log_time = now

            time.sleep(0.05)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        # Update position from encoders
        avg_deg = (abs(self.left_motor.get_encoder()) + abs(self.right_motor.get_encoder())) / 2
        actual_distance = (math.pi * rw * avg_deg) / 180
        heading_rad = math.radians(self.heading)
        self.x += actual_distance * math.cos(heading_rad)
        self.y += actual_distance * math.sin(heading_rad)

        log.info("move_forward done | traveled=%.1f cm pos=(%.1f, %.1f) heading=%.1f",
                 actual_distance, self.x, self.y, self.heading)

    # ── Turning ──────────────────────────────────────────────────────

    def turn(self, angle_deg):
        """
        Rotate in place by angle_deg. Positive = CCW (left), Negative = CW (right).
        With gyro: closed-loop proportional control.
        Without gyro: open-loop wheel-encoder based.
        """
        log.info("turn %.1f deg | mode=%s pos=(%.1f, %.1f) heading=%.1f",
                 angle_deg, "gyro" if self.gyro else "open-loop",
                 self.x, self.y, self.heading)

        if self.gyro is not None:
            self._turn_corrected(angle_deg)
        else:
            self._turn_open_loop(angle_deg)

        log.info("turn done | heading=%.1f", self.heading)

    def _turn_open_loop(self, angle_deg):
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
        target_heading = self.heading + angle_deg
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        base_dps = Config.Navigation.SPEED_ROTATE
        kp = Config.Navigation.HEADING_CORRECTION_KP

        last_log_time = time.time()

        while True:
            current_heading = self._read_gyro()
            if current_heading is not None:
                self.heading = current_heading

            error = target_heading - self.heading
            if abs(error) <= tolerance:
                break

            turn_dps = max(min(kp * error, base_dps), -base_dps)
            self.left_motor.set_dps(-turn_dps)
            self.right_motor.set_dps(turn_dps)

            now = time.time()
            if now - last_log_time >= Config.Logging.LOG_FREQUENCY:
                log.debug("turning | target=%.1f current=%.1f error=%.1f dps=%.1f",
                          target_heading, self.heading, error, turn_dps)
                last_log_time = now

            time.sleep(0.05)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

    # ── Accessors ────────────────────────────────────────────────────

    def get_position(self):
        """Return current estimated pose as (x, y, heading_degrees)."""
        return (self.x, self.y, self.heading)