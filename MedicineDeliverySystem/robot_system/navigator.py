import math
import time
import logging
from utils.brick import Motor
from config import Config

log = logging.getLogger(__name__)


class Navigator:
    def __init__(self, gyro=None):
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

    def move(self, distance_cm, direction, assessor=None):
        """
        Move by distance_cm in direction (1=forward, -1=backward).
        If assessor is provided, samples the color sensor each loop tick and
        returns the last detected room string. Otherwise returns None.
        """
        log.info("move %.1f cm direction=%d | heading=%.1f", distance_cm, direction, self.heading)

        rw = Config.Navigation.WHEEL_RADIUS_CM
        target_encoder_deg = (180 * distance_cm) / (math.pi * rw)
        base_dps = Config.Navigation.SPEED_NORMAL
        kp = Config.Navigation.HEADING_CORRECTION_KP
        target_heading = self.heading

        self.left_motor.reset_encoder()
        self.right_motor.reset_encoder()

        last_log_time = time.time()
        current_room = "unknown"

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

            # Color scanning — runs inline, no threading needed
            if assessor is not None:
                detected = assessor.current_room()
                if detected != "unknown":
                    current_room = detected
                    log.debug("move scanning | room=%s", current_room)

            time.sleep(0.05)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        avg_deg = (abs(self.left_motor.get_encoder()) + abs(self.right_motor.get_encoder())) / 2
        actual_distance = (math.pi * rw * avg_deg) / 180
        log.info("move done | traveled=%.1f cm heading=%.1f room=%s",
                 actual_distance, self.heading, current_room if assessor else "-")
        return current_room if assessor is not None else None

    def move_forward(self, distance_cm, assessor=None):
        return self.move(distance_cm, 1, assessor)

    def move_backward(self, distance_cm, assessor=None):
        return self.move(distance_cm, -1, assessor)
	
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
    
    def diff_turn(self, angle_deg, pivot_wheel):
        """
        Pivot turn by any angle around one wheel in two phases:
        1) Blind encoder-based coarse turn (all but a small trim window)
        2) Slow gyro trim for final few degrees

        - angle_deg: signed angle in degrees (+left/CCW, -right/CW)
        - pivot_wheel: 'left' or 'right' (wheel that stays at 0 DPS)
        - active wheel runs; pivot wheel stays at 0 DPS
        """
        if self.gyro is None:
            raise RuntimeError("diff_turn requires a gyro sensor")

        angle_deg = float(angle_deg)
        if angle_deg == 0:
            return

        pivot_wheel = str(pivot_wheel).strip().lower()
        if pivot_wheel not in ("left", "right"):
            raise ValueError("pivot_wheel must be 'left' or 'right'")

        direction = 1 if angle_deg > 0 else -1

        start_heading = self._read_gyro()
        if start_heading is None:
            raise RuntimeError("gyro returned None at diff_turn start")

        base_dps = Config.Navigation.SPEED_ROTATE
        trim_dps = Config.Navigation.SPEED_ROTATE_ADJUST
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        loop_dt = 0.02
        target_abs_deg = abs(angle_deg)
        trim_window_deg = 10.0   # start slow phase 10° before target
        coast_deg       = 5.0    # degrees robot coasts after set_dps(0) at trim speed
        coarse_target_deg = max(0.0, target_abs_deg - trim_window_deg)

        def wrap_to_180(angle):
            return (angle + 180.0) % 360.0 - 180.0

        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY

        def get_progress_deg(current_heading):
            turned_delta = wrap_to_180(current_heading - start_heading)
            return direction * turned_delta

        # Sign for active wheel movement based on pivot side and turn direction.
        # Around left pivot:  +angle => right wheel forward, -angle => right wheel backward
        # Around right pivot: +angle => left wheel backward, -angle => left wheel forward
        active_sign = direction if pivot_wheel == "left" else -direction

        wheel_deg_per_robot_deg = Config.Navigation.TRACK_WIDTH_CM / Config.Navigation.WHEEL_RADIUS_CM
        coarse_wheel_deg = coarse_target_deg * wheel_deg_per_robot_deg
        active_step_deg = active_sign * coarse_wheel_deg

        self.left_motor.set_limits(dps=base_dps)
        self.right_motor.set_limits(dps=base_dps)

        log.info("diff_turn coarse start | turn=%s pivot=%s target=%.1f°",
                 "left" if direction > 0 else "right", pivot_wheel, coarse_target_deg)

        if pivot_wheel == "left":
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

        active_trim_dps = active_sign * trim_dps
        if pivot_wheel == "left":
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
            if progress_deg >= (target_abs_deg - tolerance - coast_deg):
                break

            time.sleep(loop_dt)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        final_heading = self._read_gyro()
        if final_heading is not None:
            self.heading = final_heading
        else:
            self.heading += angle_deg

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

    def scan_turn(self, angle_deg, assessor=None):
        """
        Rotate slowly at SPEED_ROTATE_ADJUST, sampling the color sensor inline.
        Positive angle_deg = CCW (left), negative = CW (right).

        Returns True if a bed color (green or red) is detected mid-sweep,
        False if the full angle is swept without finding a bed.
        Requires gyro.
        """
        if self.gyro is None:
            raise RuntimeError("scan_turn requires a gyro sensor")

        angle_deg = float(angle_deg)
        if angle_deg == 0:
            return False

        direction = 1 if angle_deg > 0 else -1
        target_abs_deg = abs(angle_deg)
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        dps = Config.Navigation.SPEED_ROTATE_ADJUST
        loop_dt = 0.02

        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY

        start_heading = self._read_gyro()
        if start_heading is None:
            raise RuntimeError("gyro returned None at scan_turn start")

        def wrap_to_180(a):
            return (a + 180.0) % 360.0 - 180.0

        log.info("scan_turn %.1f deg | heading=%.1f", angle_deg, self.heading)

        self.left_motor.set_limits(dps=dps)
        self.right_motor.set_limits(dps=dps)
        self.left_motor.set_dps(lp * (-direction * dps))
        self.right_motor.set_dps(rp * (direction * dps))

        bed_found = False
        while True:
            current_heading = self._read_gyro()
            if current_heading is None:
                log.warning("Gyro read returned None during scan_turn; stopping")
                break

            progress_deg = direction * wrap_to_180(current_heading - start_heading)

            if assessor is not None and assessor.sees_bed():
                bed_found = True
                log.info("scan_turn: bed detected at %.1f deg into sweep", progress_deg)
                break

            if progress_deg >= target_abs_deg - tolerance:
                break

            time.sleep(loop_dt)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        final_heading = self._read_gyro()
        if final_heading is not None:
            self.heading = final_heading
        else:
            self.heading += angle_deg

        log.info("scan_turn done | heading=%.1f bed_found=%s", self.heading, bed_found)
        return bed_found

    # ── Accessors ────────────────────────────────────────────────────

    def get_position(self):
        """Position tracking disabled; returns heading as third value for compatibility."""
        return (0.0, 0.0, self.heading)
