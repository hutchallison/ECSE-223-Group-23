import math
import time
import logging
from utils.brick import Motor
from config import Config

log = logging.getLogger(__name__)


class Navigator:
    def __init__(self, gyro=None, us=None):
        self.left_motor = Motor(Config.Ports.LEFT_MOTOR)
        self.right_motor = Motor(Config.Ports.RIGHT_MOTOR)
        self.gyro = gyro
        self.heading = 0.0

        # Gyro baseline so heading starts at 0
        self._gyro_offset = 0.0
        if self.gyro is not None:
            initial = self.gyro.get_abs_measure()
            if initial is not None:
                self._gyro_offset = initial

        log.info("Navigator init | gyro=%s gyro_offset=%.1f",
             gyro is not None, self._gyro_offset)

    # ── Sensors ──────────────────────────────────────────────────────

    def _read_gyro(self):
        """Read current heading from gyro (offset-adjusted, scaled). Returns None if unavailable."""
        if self.gyro is None:
            return None
        reading = self.gyro.get_abs_measure()
        if reading is None:
            log.warning("Gyro read returned None")
            return None
        return (reading - self._gyro_offset) * Config.Navigation.GYRO_SCALE

    def get_wall_distance(self):
        """Ultrasonic is not used in this navigator revision."""
        return None

    # ── Movement ─────────────────────────────────────────────────────

    def move(self, distance_cm, direction):
        """
        Move forward by distance_cm. Uses gyro for heading correction if available,
        otherwise drives straight open-loop via set_dps.
        """
        log.info("move_forward %.1f cm | heading=%.1f", distance_cm, self.heading)

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

            lp = direction * Config.Navigation.LEFT_MOTOR_POLARITY
            rp = direction * Config.Navigation.RIGHT_MOTOR_POLARITY
            self.left_motor.set_dps(lp * (base_dps - correction))
            self.right_motor.set_dps(rp * (base_dps + correction))

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

        avg_deg = (abs(self.left_motor.get_encoder()) + abs(self.right_motor.get_encoder())) / 2
        actual_distance = (math.pi * rw * avg_deg) / 180
        log.info("move_forward done | traveled=%.1f cm heading=%.1f", actual_distance, self.heading)
	
    def move_forward(self, distance_cm):
        self.move(distance_cm, 1)
	
    def move_backward(self, distance_cm):
        self.move(distance_cm, -1)
	
    def turn(self, angle_deg):
        """
        Rotate in place by angle_deg. Positive = CCW (left), Negative = CW (right).
        Phase 1 (blind): full-speed encoder-based turn for the whole angle.
        Phase 2 (trim): if gyro available, one constant-speed correction pass.
        """
        log.info("turn %.1f deg | heading=%.1f", angle_deg, self.heading)

        target_heading = self.heading + angle_deg
        self._turn_blind(angle_deg)
        self._turn_gyro_trim(target_heading)

        log.info("turn done | heading=%.1f", self.heading)
    
    def diff_turn(self, direction, forward=True):
        """
        Pivot turn by 90° around one wheel in two phases:
        1) Blind encoder-based coarse turn (~85°)
        2) Slow gyro trim for final few degrees

        - direction: +1 for left (CCW), -1 for right (CW)
        - active wheel runs; pivot wheel stays at 0 DPS
        - forward=False reverses active wheel direction
        """
        if self.gyro is None:
            raise RuntimeError("diff_turn requires a gyro sensor")

        if direction not in (-1, 1):
            raise ValueError("direction must be +1 (left) or -1 (right)")

        start_heading = self._read_gyro()
        if start_heading is None:
            raise RuntimeError("gyro returned None at diff_turn start")

        base_dps = Config.Navigation.SPEED_ROTATE
        trim_dps = Config.Navigation.SPEED_ROTATE_ADJUST
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        loop_dt = 0.02
        target_abs_deg = 90.0
        trim_window_deg = 5.0
        coarse_target_deg = max(0.0, target_abs_deg - trim_window_deg)
        travel_sign = 1 if forward else -1

        def wrap_to_180(angle):
            return (angle + 180.0) % 360.0 - 180.0

        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY

        def get_progress_deg(current_heading):
            turned_delta = wrap_to_180(current_heading - start_heading)
            return direction * turned_delta

        wheel_deg_per_robot_deg = Config.Navigation.TRACK_WIDTH_CM / Config.Navigation.WHEEL_RADIUS_CM
        coarse_wheel_deg = coarse_target_deg * wheel_deg_per_robot_deg
        active_step_deg = travel_sign * coarse_wheel_deg

        self.left_motor.set_limits(dps=base_dps)
        self.right_motor.set_limits(dps=base_dps)

        log.info("diff_turn coarse start | direction=%s target=%.1f°",
                 "left" if direction > 0 else "right", coarse_target_deg)

        if direction > 0:
            self.left_motor.set_dps(0)
            self.right_motor.set_position_relative(rp * active_step_deg)
            self.right_motor.wait_is_moving()
            self.right_motor.wait_is_stopped()
        else:
            self.right_motor.set_dps(0)
            self.left_motor.set_position_relative(lp * active_step_deg)
            self.left_motor.wait_is_moving()
            self.left_motor.wait_is_stopped()

        log.info("diff_turn trim start | target=%.1f° tolerance=%.1f°", target_abs_deg, tolerance)

        active_trim_dps = trim_dps * travel_sign
        if direction > 0:
            self.left_motor.set_dps(0)
            self.right_motor.set_dps(rp * active_trim_dps)
        else:
            self.right_motor.set_dps(0)
            self.left_motor.set_dps(lp * active_trim_dps)

        while True:
            current_heading = self._read_gyro()
            if current_heading is None:
                log.warning("Gyro read returned None during diff_turn; stopping")
                break

            progress_deg = get_progress_deg(current_heading)
            if progress_deg >= (target_abs_deg - tolerance):
                break

            time.sleep(loop_dt)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        final_heading = self._read_gyro()
        if final_heading is not None:
            self.heading = final_heading

        log.info("diff_turn done | heading=%.1f", self.heading)

    def _turn_blind(self, angle_deg):
        """Encoder-based turn at constant SPEED_ROTATE. No feedback."""
        rw = Config.Navigation.WHEEL_RADIUS_CM
        rb = Config.Navigation.TRACK_WIDTH_CM / 2
        wheel_degrees = angle_deg * (rb / rw)

        self.left_motor.set_limits(dps=Config.Navigation.SPEED_ROTATE)
        self.right_motor.set_limits(dps=Config.Navigation.SPEED_ROTATE)

        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY
        self.left_motor.set_position_relative(lp * (-wheel_degrees))
        self.right_motor.set_position_relative(rp * wheel_degrees)

        self.left_motor.wait_is_moving()
        self.left_motor.wait_is_stopped()
        self.right_motor.wait_is_stopped()

        self.heading += angle_deg

    def _turn_gyro_trim(self, target_heading):
        """After a blind turn, nudge at constant SPEED_ROTATE_ADJUST until within tolerance."""
        if self.gyro is None:
            return

        current = self._read_gyro()
        if current is None:
            return
        self.heading = current

        error = target_heading - current
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        if abs(error) <= tolerance:
            return

        adjust_dps = Config.Navigation.SPEED_ROTATE_ADJUST
        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY
        direction = 1 if error > 0 else -1
        self.left_motor.set_dps(lp * (-direction * adjust_dps))
        self.right_motor.set_dps(rp * (direction * adjust_dps))

        while True:
            current = self._read_gyro()
            if current is None:
                break
            self.heading = current
            if abs(target_heading - current) <= tolerance:
                break
            time.sleep(0.02)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)
        log.debug("gyro trim done | target=%.1f actual=%.1f", target_heading, self.heading)

    # ── Accessors ────────────────────────────────────────────────────

    def get_position(self):
        """Position tracking disabled; returns heading as third value for compatibility."""
        return (0.0, 0.0, self.heading)
