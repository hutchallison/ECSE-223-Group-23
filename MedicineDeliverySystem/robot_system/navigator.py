import math
import time
import logging
from utils.brick import Motor, EV3UltrasonicSensor
from config import Config

log = logging.getLogger(__name__)


class Navigator:
    def __init__(self, gyro=None, left_wheel_compensation=0):
        self.left_motor = Motor(Config.Ports.LEFT_MOTOR)
        self.right_motor = Motor(Config.Ports.RIGHT_MOTOR)
        self.gyro = gyro
        self.left_wheel_compensation = left_wheel_compensation
        self.us = EV3UltrasonicSensor(Config.Ports.ULTRASONIC)
        self.heading = 0.0
        # Directional scale: CCW (left) and CW (right) are calibrated separately.
        # _gyro_scale is set to the appropriate value at the start of every rotation.
        self._gyro_scale = Config.Navigation.GYRO_SCALE_LEFT

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
        return (reading - self._gyro_offset) * self._gyro_scale

    def get_wall_distance(self):
        """Read ultrasonic distance in cm. Returns None on sensor error."""
        try:
            return self.us.get_cm()
        except Exception:
            return None

    def move_until_distance(self, threshold_cm: float, direction: int = 1,
                            max_dist_cm: float = 150.0):
        """
        Move in direction (1=forward, -1=backward) until the ultrasonic sensor
        reads <= threshold_cm, or max_dist_cm is reached as a safety stop.
        Returns actual distance traveled in cm.
        """
        log.info("move_until_distance threshold=%.1f direction=%d | heading=%.1f",
                 threshold_cm, direction, self.heading)

        rw = Config.Navigation.WHEEL_RADIUS_CM
        max_encoder_deg = (180 * max_dist_cm) / (math.pi * rw)
        base_dps = Config.Navigation.SPEED_NORMAL
        kp = Config.Navigation.HEADING_CORRECTION_KP
        target_heading = self.heading

        self.left_motor.reset_encoder()
        self.right_motor.reset_encoder()

        while True:
            left_deg  = abs(self.left_motor.get_encoder())
            right_deg = abs(self.right_motor.get_encoder())
            avg_deg   = (left_deg + right_deg) / 2

            if avg_deg >= max_encoder_deg:
                log.warning("move_until_distance: safety stop at %.1f cm", max_dist_cm)
                break

            dist = self.get_wall_distance()
            if dist is not None and dist <= threshold_cm:
                log.info("move_until_distance: stopped at %.1f cm from wall", dist)
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

            time.sleep(0.05)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        avg_deg = (abs(self.left_motor.get_encoder()) +
                   abs(self.right_motor.get_encoder())) / 2
        actual_cm = (math.pi * rw * avg_deg) / 180
        log.info("move_until_distance done | traveled=%.1f cm", actual_cm)
        return actual_cm

    def move_backward_until_distance(self, threshold_cm: float,
                                     max_dist_cm: float = 150.0):
        """Move backward until ultrasonic reads <= threshold_cm."""
        return self.move_until_distance(threshold_cm, -1, max_dist_cm)

    # ── Movement ─────────────────────────────────────────────────────

    def move(self, distance_cm, direction, assessor=None, follow_line=False):
        """
        Move by distance_cm in direction (1=forward, -1=backward).
        If assessor is provided, samples the color sensor each loop tick and
        returns the last detected room string. Otherwise returns None.
        If follow_line=True and assessor is provided, boosts heading correction
        gain whenever the color sensor leaves black, steering the robot back.
		ur robotic system is undergoing extensive testing to ensure its safety in your hospital environment.
        Only effective when moving forward (direction=1).
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
            # if current_heading is not None:
            #     self.heading = current_heading
            #     active_kp = kp
            #     if follow_line and direction == 1 and assessor is not None:
            #         on_line = assessor.fast_color(n_samples=3)
            #         if on_line != "black":
            #             active_kp = Config.Navigation.HEADING_CORRECTION_KP_BOOST
            #             log.debug("follow_line: off black (%s), boosting KP heading=%.1f",
            #                       on_line, self.heading)
            #     correction = active_kp * (target_heading - current_heading)

            lp = direction * Config.Navigation.LEFT_MOTOR_POLARITY
            rp = direction * Config.Navigation.RIGHT_MOTOR_POLARITY
            left_comp = self.left_wheel_compensation if direction == 1 else 0
            self.left_motor.set_dps(lp * (base_dps - correction + left_comp))
            self.right_motor.set_dps(rp * (base_dps + correction))

            # Log position every 2 seconds
            now = time.time()
            if now - last_log_time >= Config.Logging.LOG_FREQUENCY:
                progress = (avg_deg / target_encoder_deg) * 100
                log.debug("moving | progress=%.0f%% heading=%.1f correction=%.1f encoders=(%.0f, %.0f)",
                          progress, self.heading, correction, left_deg, right_deg)
                last_log_time = now

            # Obstacle check — only while moving forward
            '''if direction == 1:
                us_dist = self.get_wall_distance()
                if us_dist is not None and us_dist < Config.Navigation.OBSTACLE_STOP_CM:
                    log.warning("move: obstacle at %.1f cm — stopping early", us_dist)
                    #break'''

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

    def move_forward(self, distance_cm, assessor=None, follow_line=False):
        return self.move(distance_cm, 1, assessor, follow_line=follow_line)

    def move_backward(self, distance_cm, assessor=None):
        return self.move(distance_cm, -1, assessor)
	
    def _pid_rotate(self, angle_deg, pivot_wheel=None):
        """
        PID-controlled rotation using the gyro.

        pivot_wheel=None  : standard in-place turn (both wheels, opposite directions)
        pivot_wheel='left': pivot around left wheel  (only right wheel moves)
        pivot_wheel='right': pivot around right wheel (only left wheel moves)

        The gyro offset is zeroed immediately before the PID loop while the
        robot is stationary, so prior motor vibration does not pollute the
        baseline. The D term naturally decelerates the motor as it approaches
        the target, eliminating coast overshoot without needing a separate
        micro-trim pass. After the turn the offset is re-anchored so that
        subsequent _read_gyro() calls and turn_to_heading() remain consistent.

        Falls back to _turn_blind if no gyro is available.
        """
        angle_deg = float(angle_deg)
        if angle_deg == 0:
            return

        if self.gyro is None:
            self._turn_blind(angle_deg)
            return

        # Select scale based on rotation direction before zeroing the offset.
        self._gyro_scale = (Config.Navigation.GYRO_SCALE_LEFT
                            if angle_deg > 0
                            else Config.Navigation.GYRO_SCALE_RIGHT)

        # Zero gyro relative to current physical pose (motors stationary = clean read).
        pre_turn_heading = self.heading
        raw_before = self.gyro.get_abs_measure()
        if raw_before is None:
            log.warning("_pid_rotate: gyro None at start, falling back to blind turn")
            self._turn_blind(angle_deg)
            return
        self._gyro_offset = raw_before  # _read_gyro() now returns 0.0 right now

        target    = angle_deg           # _read_gyro() is in scaled degrees
        kp        = Config.Navigation.TURN_KP
        ki        = Config.Navigation.TURN_KI
        kd        = Config.Navigation.TURN_KD
        max_dps   = Config.Navigation.SPEED_ROTATE
        min_dps   = Config.Navigation.TURN_MIN_DPS
        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        dt        = 0.02
        lp        = Config.Navigation.LEFT_MOTOR_POLARITY
        rp        = Config.Navigation.RIGHT_MOTOR_POLARITY

        integral   = 0.0
        prev_error = target   # initial error = full angle

        log.info("_pid_rotate %.1f deg pivot=%s", angle_deg, pivot_wheel)

        while True:
            current = self._read_gyro()
            if current is None:
                log.warning("_pid_rotate: gyro read None, stopping")
                break

            error = target - current
            if abs(error) <= tolerance:
                break

            integral   += error * dt
            integral    = max(-50.0, min(50.0, integral))   # anti-windup
            derivative  = (error - prev_error) / dt
            prev_error  = error

            output = kp * error + ki * integral + kd * derivative
            output = max(-max_dps, min(max_dps, output))    # speed ceiling
            if 0 < abs(output) < min_dps:                   # stall floor
                output = math.copysign(min_dps, output)

            if pivot_wheel is None:
                direction = 1 if output > 0 else -1
                speed     = abs(output)
                self.left_motor.set_dps(lp  * (-direction * speed))
                self.right_motor.set_dps(rp *  (direction * speed))
            elif pivot_wheel == "left":
                # positive output = CCW = right wheel forward (rp * positive_output → forward)
                self.left_motor.set_dps(0)
                self.right_motor.set_dps(rp * output)
            else:  # right
                # positive output = CCW = left wheel backward (lp * -output → backward)
                self.right_motor.set_dps(0)
                self.left_motor.set_dps(lp * (-output))

            time.sleep(dt)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)

        # Settle: D term already slowed the motor, so 200ms coast is < 0.5 deg.
        time.sleep(0.25)

        actual_rotation = self._read_gyro()   # relative to reset baseline
        self.heading = pre_turn_heading + (actual_rotation if actual_rotation is not None else angle_deg)

        # Re-anchor offset so _read_gyro() == self.heading for move() and turn_to_heading().
        raw_after = self.gyro.get_abs_measure()
        if raw_after is not None:
            self._gyro_offset = raw_after - (self.heading / self._gyro_scale)

        log.info("_pid_rotate done | target=%.1f actual=%.1f heading=%.1f",
                 angle_deg, actual_rotation or angle_deg, self.heading)

    def turn(self, angle_deg):
        """Rotate in place by angle_deg using PID gyro control. Positive=CCW, Negative=CW."""
        log.info("turn %.1f deg | heading=%.1f", angle_deg, self.heading)
        self._pid_rotate(angle_deg)
        log.info("turn done | heading=%.1f", self.heading)

    def turn_right(self, bias: int = 0):
        """Rotate 90 degrees clockwise in place."""
        self._turn_blind(-90 + bias)

    def turn_left(self, bias: int = 0):
        """Rotate 90 degrees counter-clockwise in place."""
        self._turn_blind(90 + bias)
    
    def diff_turn(self, angle_deg, pivot_wheel):
        """Pivot turn around one wheel using PID gyro control.
        pivot_wheel: 'left' or 'right' (that wheel stays stationary)."""
        pivot_wheel = str(pivot_wheel).strip().lower()
        if pivot_wheel not in ("left", "right"):
            raise ValueError("pivot_wheel must be 'left' or 'right'")
        log.info("diff_turn %.1f deg pivot=%s | heading=%.1f", angle_deg, pivot_wheel, self.heading)
        self._pid_rotate(float(angle_deg), pivot_wheel=pivot_wheel)
        log.info("diff_turn done | heading=%.1f", self.heading)

    def _turn_blind(self, angle_deg):
        """Encoder-based turn at constant SPEED_ROTATE. No feedback."""
        self.left_motor.reset_encoder()
        self.right_motor.reset_encoder()
        time.sleep(0.1)		
        rw = Config.Navigation.WHEEL_RADIUS_CM
        rb = Config.Navigation.TRACK_WIDTH_CM / 2
        wheel_degrees = angle_deg * (rb / rw)

        self.left_motor.set_limits(dps=Config.Navigation.SPEED_ROTATE)
        self.right_motor.set_limits(dps=Config.Navigation.SPEED_ROTATE)

        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY
        self.left_motor.set_position_relative(lp * (-wheel_degrees))
        self.right_motor.set_position_relative(rp * wheel_degrees)
        log.info("TURNED "+ str(angle_deg) +" DEGREES")
        self.left_motor.wait_is_moving()
        self.left_motor.wait_is_stopped()
        self.right_motor.wait_is_stopped()

        self.heading += angle_deg

    def scan_turn(self, angle_deg, assessor=None, use_gyro=True):
        """
        Blind turn using _turn_blind then sample the color sensor at the endpoint.
        Positive angle_deg = CCW (left), negative = CW (right).

        Returns True if a bed is detected after the turn, False otherwise.
        """
        angle_deg = float(angle_deg)
        if angle_deg == 0:
            return False

        log.info("scan_turn %.1f deg | heading=%.1f", angle_deg, self.heading)
        self._turn_blind(angle_deg)

        bed_found = assessor is not None and assessor.needs_medicine()
        log.info("scan_turn done | heading=%.1f bed_found=%s", self.heading, bed_found)
        return bed_found

    def reset_heading(self, known_heading=0.0):
        """
        Re-anchor the gyro offset to the current physical pose.
        Call this only when the robot is stationary at a physically verified
        heading (e.g. pressed against a wall, or at a known landmark).
        Eliminates all accumulated gyro drift up to this point.
        """
        if self.gyro is None:
            return
        raw = self.gyro.get_abs_measure()
        if raw is not None:
            self._gyro_offset = raw - (known_heading / self._gyro_scale)
        self.heading = known_heading
        log.info("reset_heading | physical_heading=%.1f new_offset=%.1f",
                 known_heading, self._gyro_offset)

    def turn_to_heading(self, target_heading):
        """
        Rotate to target_heading using a proportional speed controller.

        Speed = kp * |error|, clamped to [min_dps, SPEED_ROTATE_ADJUST].
        The robot is already near-stopped when it reaches the target,
        so coast overshoot is ~0.3 deg instead of ~1.6 deg at constant 80 dps.

        Because the stop condition is an absolute gyro reading, GYRO_SCALE error
        and accumulated heading drift cancel out: we stop when the raw sensor
        returns to the same value it had at target_heading, regardless of scale.
        """
        if self.gyro is None:
            raise RuntimeError("turn_to_heading requires a gyro sensor")

        current = self._read_gyro()
        if current is None:
            raise RuntimeError("gyro returned None at turn_to_heading start")

        tolerance = Config.Navigation.TURN_TOLERANCE_DEG
        if abs(target_heading - current) <= tolerance:
            self.heading = current
            return

        # Set directional scale before the feedback loop.
        self._gyro_scale = (Config.Navigation.GYRO_SCALE_LEFT
                            if target_heading > current
                            else Config.Navigation.GYRO_SCALE_RIGHT)

        kp      = 3.0   # dps per degree of error
        min_dps = 35    # below this motors stall; also limits coast to ~0.35 deg
        max_dps = Config.Navigation.SPEED_ROTATE_ADJUST  # 80 dps ceiling
        loop_dt = 0.02
        lp = Config.Navigation.LEFT_MOTOR_POLARITY
        rp = Config.Navigation.RIGHT_MOTOR_POLARITY

        log.info("turn_to_heading %.1f | current=%.1f", target_heading, current)

        while True:
            current = self._read_gyro()
            if current is None:
                break
            error = target_heading - current
            if abs(error) <= tolerance:
                break
            direction = 1 if error > 0 else -1
            speed = max(min_dps, min(max_dps, abs(error) * kp))
            self.left_motor.set_dps(lp * (-direction * speed))
            self.right_motor.set_dps(rp * (direction * speed))
            time.sleep(loop_dt)

        self.left_motor.set_dps(0)
        self.right_motor.set_dps(0)
        time.sleep(0.1)   # at min_dps=35, coast in 0.1s is ~0.35 deg
        final = self._read_gyro()
        if final is not None:
            self.heading = final

        log.info("turn_to_heading done | target=%.1f actual=%.1f",
                target_heading, self.heading)
