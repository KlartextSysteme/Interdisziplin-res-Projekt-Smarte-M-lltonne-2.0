import time


class GlobalController:
    """
    Zentrale State Machine des Picos.
    Koordiniert Sensoren, Motoren, Netzwerk und Logik.
    """

    # --- Pico-Zustände (Interne Logik) --- 
    STATE_STANDBY = "STANDBY"
    STATE_LINE_FOLLOWING = "LINE_FOLLOWING"
    STATE_USER_PAUSED = "USER_PAUSED"
    STATE_LINE_LOST = "LINE_LOST"
    STATE_OBSTACLE_WAIT = "OBSTACLE_WAIT"
    STATE_AVOID_RIGHT = "AVOID_RIGHT"
    STATE_AVOID_LEFT = "AVOID_LEFT"
    STATE_AVOID_NOT_POSSIBLE = "AVOID_NOT_POSSIBLE"
    STATE_WAIT_AT_STREET = "WAIT_AT_STREET"
    # Zustände für manuelle Anforderungen per Touchpanel
    STATE_MANUAL_GOTO_STREET_REQUEST = "MANUAL_GOTO_STREET_REQUEST"
    STATE_MANUAL_RETURN_HOME_REQUEST = "MANUAL_RETURN_HOME_REQUEST"

    def __init__(
        self,
        line_sensor=None,
        obstacle_sensors=None,
        pd_controller=None,
        motors=None,
        buzzer=None,
        touchpanel=None,
        base_speed=45,
        min_speed=0,
        max_speed=95,
    ):
        self.line_sensor = line_sensor
        self.obstacle_sensors = obstacle_sensors
        self.pd_controller = pd_controller
        self.motors = motors
        self.buzzer = buzzer
        self.touchpanel = touchpanel

        self.base_speed = base_speed
        self.min_speed = min_speed
        self.max_speed = max_speed

        self.state = self.STATE_STANDBY
        self.state_since_ms = time.ticks_ms()

        self.last_line_seen_ms = time.ticks_ms()
        self.last_left_speed = self.base_speed
        self.last_right_speed = self.base_speed

        self.line_lost_timeout_ms = 10000
        
        self.obstacle_wait_ms = 10000
        self.obstacle_stop_cm = 30
        self.avoid_side = None

        self.avoid_speed = 35
        self.avoid_turn_speed = 35

        self.avoid_turn_90_ms = 850
        self.avoid_forward_ms = 900
        self.avoid_side_max_ms = 5000
        self.avoid_line_search_max_ms = 6000

        self.avoid_step = 0
        self.avoid_step_since_ms = time.ticks_ms()

    def set_state(self, new_state):
        if self.state == new_state:
            return

        print("State:", self.state, "->", new_state)
        self.state = new_state
        self.state_since_ms = time.ticks_ms()

        if new_state in (self.STATE_AVOID_RIGHT, self.STATE_AVOID_LEFT):
            self.avoid_step = 0
            self.avoid_step_since_ms = self.state_since_ms
    
    def _next_avoid_step(self):
        self.avoid_step += 1
        self.avoid_step_since_ms = time.ticks_ms()
    
    def _line_found_during_avoidance(self):
        if self.line_sensor is None:
            return False

        position = self.line_sensor.get_position(force=True)
        return position is not None

    def request_goto_street(self):
        if self.state in (
            self.STATE_STANDBY,
            self.STATE_WAIT_AT_STREET,
            self.STATE_MANUAL_GOTO_STREET_REQUEST,
        ):
            self.set_state(self.STATE_LINE_FOLLOWING)

    def request_return_home(self):
        if self.state in (
            self.STATE_WAIT_AT_STREET,
            self.STATE_MANUAL_RETURN_HOME_REQUEST,
        ):
            self.set_state(self.STATE_LINE_FOLLOWING)

    def pause(self):
        if self.state in (
            self.STATE_LINE_FOLLOWING,
            self.STATE_LINE_LOST,
            self.STATE_OBSTACLE_WAIT,
            self.STATE_AVOID_RIGHT,
            self.STATE_AVOID_LEFT,
        ):
            if self.motors:
                self.motors.stop()
            self.set_state(self.STATE_USER_PAUSED)

    def resume(self):
        if self.state == self.STATE_USER_PAUSED:
            self.set_state(self.STATE_LINE_FOLLOWING)

    def stop(self):
        if self.motors:
            self.motors.stop()
        self.set_state(self.STATE_STANDBY)

    def run(self):
        if self.state == self.STATE_STANDBY:
            self._logic_standby()
        elif self.state == self.STATE_LINE_FOLLOWING:
            self._logic_line_following()
        elif self.state == self.STATE_LINE_LOST:
            self._logic_line_lost()
        elif self.state == self.STATE_OBSTACLE_WAIT:
            self._logic_obstacle_wait()
        elif self.state == self.STATE_AVOID_RIGHT:
            self._logic_avoid_right()
        elif self.state == self.STATE_AVOID_LEFT:
            self._logic_avoid_left()
        elif self.state == self.STATE_AVOID_NOT_POSSIBLE:
            self._logic_avoid_not_possible()
        elif self.state == self.STATE_WAIT_AT_STREET:
            self._logic_wait_at_street()
        elif self.state == self.STATE_USER_PAUSED:
            self._logic_user_paused()

    def _logic_standby(self):
        pass

    def _logic_line_following(self):
        if self.line_sensor is None or self.pd_controller is None or self.motors is None:
            if self.motors:
                self.motors.stop()
            return

        if self.obstacle_sensors is not None:
            self.obstacle_sensors.run_front()

            if self.obstacle_sensors.front_obstacle_detected():
                self.motors.stop()
                self.set_state(self.STATE_OBSTACLE_WAIT)
                return

        position = self.line_sensor.get_position()

        if position == "street":
            self.motors.stop()
            self.set_state(self.STATE_WAIT_AT_STREET)
            return

        if position is None:
            self.set_state(self.STATE_LINE_LOST)
            return

        self.last_line_seen_ms = time.ticks_ms()

        left_speed, right_speed, correction = self.pd_controller.get_motor_speeds(
            current_position=position,
            base_speed=self.base_speed,
            min_speed=self.min_speed,
            max_speed=self.max_speed,
        )

        self.last_left_speed = left_speed
        self.last_right_speed = right_speed

        self.motors.drive_forward_differential(left_speed, right_speed)

    def _logic_line_lost(self):
        if self.motors is None:
            return

        position = None
        if self.line_sensor is not None:
            position = self.line_sensor.get_position()

        if position == "street":
            self.motors.stop()
            self.set_state(self.STATE_WAIT_AT_STREET)
            return

        if position is not None:
            self.set_state(self.STATE_LINE_FOLLOWING)
            return

        if time.ticks_diff(time.ticks_ms(), self.last_line_seen_ms) < self.line_lost_timeout_ms:
            self.motors.drive_forward_differential(
                self.last_left_speed,
                self.last_right_speed,
            )
        else:
            self.motors.stop()
            self.set_state(self.STATE_STANDBY)

    def _logic_obstacle_wait(self):
        if self.motors:
            self.motors.stop()

        if time.ticks_diff(time.ticks_ms(), self.state_since_ms) < self.obstacle_wait_ms:
            return

        if self.obstacle_sensors is None:
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        side = self.obstacle_sensors.choose_avoidance_side()
        self.avoid_side = side

        if side == "right":
            self.set_state(self.STATE_AVOID_RIGHT)
        elif side == "left":
            self.set_state(self.STATE_AVOID_LEFT)
        else:
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)

    def _logic_avoid_right(self):
        if self.motors is None:
            return

        elapsed = time.ticks_diff(time.ticks_ms(), self.avoid_step_since_ms)

        # Schritt 0: 90 Grad nach rechts drehen
        if self.avoid_step == 0:
            self.motors.turn_right(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self._next_avoid_step()
            return

        # Schritt 1: Am Hindernis entlang geradeaus fahren,
        # bis links wieder frei ist oder Timeout erreicht ist.
        if self.avoid_step == 1:
            self.motors.forward(self.avoid_speed)

            if self.obstacle_sensors is not None:
                self.obstacle_sensors.measure_left()
                if self.obstacle_sensors.left_is_clear():
                    self._next_avoid_step()
                    return

            if elapsed >= self.avoid_side_max_ms:
                self._next_avoid_step()
            return

        # Schritt 2: Etwas weiter geradeaus, damit die Tonne am Hindernis vorbei ist
        if self.avoid_step == 2:
            self.motors.forward(self.avoid_speed)
            if elapsed >= self.avoid_forward_ms:
                self._next_avoid_step()
            return

        # Schritt 3: 90 Grad nach links drehen, parallel zur ursprünglichen Richtung
        if self.avoid_step == 3:
            self.motors.turn_left(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self._next_avoid_step()
            return

        # Schritt 4: Geradeaus in Richtung Linie fahren
        if self.avoid_step == 4:
            self.motors.forward(self.avoid_speed)
            if elapsed >= self.avoid_forward_ms:
                self._next_avoid_step()
            return

        # Schritt 5: Zusatzstueck geradeaus
        if self.avoid_step == 5:
            self.motors.forward(self.avoid_speed)
            if elapsed >= self.avoid_forward_ms:
                self._next_avoid_step()
            return

        # Schritt 6: 90 Grad nach links drehen, zur Linie zurück
        if self.avoid_step == 5:
            self.motors.turn_left(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self._next_avoid_step()
            return

        # Schritt 7: Linie suchen
        if self.avoid_step == 6:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self._next_avoid_step()
                return

            if elapsed >= self.avoid_line_search_max_ms:
                self.motors.stop()
                self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # Schritt 8: 90 Grad nach rechts drehen und Linienfolge fortsetzen
        if self.avoid_step == 7:
            self.motors.turn_right(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self.motors.stop()
                self.set_state(self.STATE_LINE_FOLLOWING)
            return

    def _logic_avoid_left(self):
        if self.motors is None:
            return

        elapsed = time.ticks_diff(time.ticks_ms(), self.avoid_step_since_ms)

        # Schritt 0: 90 Grad nach links drehen
        if self.avoid_step == 0:
            self.motors.turn_left(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self._next_avoid_step()
            return

        # Schritt 1: Am Hindernis entlang geradeaus fahren,
        # bis rechts wieder frei ist oder Timeout erreicht ist.
        if self.avoid_step == 1:
            self.motors.forward(self.avoid_speed)

            if self.obstacle_sensors is not None:
                self.obstacle_sensors.measure_right()
                if self.obstacle_sensors.right_is_clear():
                    self._next_avoid_step()
                    return

            if elapsed >= self.avoid_side_max_ms:
                self._next_avoid_step()
            return

        # Schritt 2: Etwas weiter geradeaus
        if self.avoid_step == 2:
            self.motors.forward(self.avoid_speed)
            if elapsed >= self.avoid_forward_ms:
                self._next_avoid_step()
            return

        # Schritt 3: 90 Grad nach rechts drehen
        if self.avoid_step == 3:
            self.motors.turn_right(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self._next_avoid_step()
            return

        # Schritt 4: Geradeaus in Richtung Linie fahren
        if self.avoid_step == 4:
            self.motors.forward(self.avoid_speed)
            if elapsed >= self.avoid_forward_ms:
                self._next_avoid_step()
            return
        
        # Schritt 5: Zusatzstueck geradeaus
        if self.avoid_step == 5:
            self.motors.forward(self.avoid_speed)
            if elapsed >= self.avoid_forward_ms:
                self._next_avoid_step()
            return

        # Schritt 6: 90 Grad nach rechts drehen, zur Linie zurueck
        if self.avoid_step == 5:
            self.motors.turn_right(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self._next_avoid_step()
            return

        # Schritt 7: Linie suchen
        if self.avoid_step == 6:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self._next_avoid_step()
                return

            if elapsed >= self.avoid_line_search_max_ms:
                self.motors.stop()
                self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # Schritt 8: 90 Grad nach links drehen und Linienfolge fortsetzen
        if self.avoid_step == 7:
            self.motors.turn_left(self.avoid_turn_speed)
            if elapsed >= self.avoid_turn_90_ms:
                self.motors.stop()
                self.set_state(self.STATE_LINE_FOLLOWING)
            return

    def _logic_avoid_not_possible(self):
        if self.motors:
            self.motors.stop()

    def _logic_wait_at_street(self):
        pass

    def _logic_user_paused(self):
        if self.motors:
            self.motors.stop()