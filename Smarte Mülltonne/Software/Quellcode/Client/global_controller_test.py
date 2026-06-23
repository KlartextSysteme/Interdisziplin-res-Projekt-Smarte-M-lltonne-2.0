import time


class GlobalController:
    """
    Zentrale State Machine des Picos.
    Koordiniert Sensoren, Motoren, Netzwerk und Logik.
    """

    # --- Pico-Zustände (Interne Logik) --- 
    STATE_AT_HOME = "AT_HOME"
    STATE_LINE_FOLLOWING = "LINE_FOLLOWING"
    STATE_USER_PAUSED = "USER_PAUSED"
    STATE_LINE_LOST = "LINE_LOST"
    STATE_OBSTACLE_WAIT = "OBSTACLE_WAIT"
    STATE_AVOID_RIGHT = "AVOID_RIGHT"
    STATE_AVOID_LEFT = "AVOID_LEFT"
    STATE_AVOID_NOT_POSSIBLE = "AVOID_NOT_POSSIBLE"
    STATE_WAIT_AT_STREET = "WAIT_AT_STREET"
    STATE_TURN_AT_HOME = "TURN_AT_HOME"
    # Zustände für manuelle Anforderungen per Touchpanel
    STATE_MANUAL_GOTO_STREET_REQUEST = "MANUAL_GOTO_STREET_REQUEST"
    STATE_MANUAL_RETURN_HOME_REQUEST = "MANUAL_RETURN_HOME_REQUEST"
    #Zustände aus der Webapp

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

        self.state = self.STATE_AT_HOME
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

        self.avoid_forward_ms = 900
        self.avoid_side_max_ms = 5000
        self.avoid_line_search_max_ms = 6000

        self.help_front_clear_since_ms = None
        self.help_resume_delay_ms = 5000

        # müssen noch angepasst werden
        self.avoid_turn_90_steps = 16000
        self.turn_home_180_steps = 32000

        self.avoid_turn_90_ms = 0
        self.turn_home_180_ms = 0

        self.avoid_step = 0
        self.avoid_step_since_ms = time.ticks_ms()

        self.state_before_pause = self.STATE_AT_HOME

        #müssen noch konfiguriert werden
        self.side_obstacle_cm = 200
        self.avoid_extra_steps = 15000
        self.avoid_extra_ms = 0

        self.help_buzzer_started = False
        self.drive_target = None

        # -------- zum Testen --------
        self.last_debug_ms = time.ticks_ms()
        self.debug_interval_ms = 500

    def set_state(self, new_state):
        if self.state == new_state:
            return

        print("State:", self.state, "->", new_state)
        self.state = new_state
        self.state_since_ms = time.ticks_ms()

        if new_state in (self.STATE_AVOID_RIGHT, self.STATE_AVOID_LEFT):
            self.avoid_step = 0
            self.avoid_extra_ms = 0
            self.avoid_step_since_ms = self.state_since_ms
        if new_state == self.STATE_AVOID_NOT_POSSIBLE:
            self.help_buzzer_started = False
            self.help_front_clear_since_ms = None
        if new_state == self.STATE_TURN_AT_HOME:
            self.turn_home_180_ms = 0
        
        if new_state in (
            self.STATE_LINE_FOLLOWING,
            self.STATE_AT_HOME,
            self.STATE_WAIT_AT_STREET,
            self.STATE_USER_PAUSED,
        ):
            if self.buzzer is not None:
                self.buzzer.stop()
    
    def _next_avoid_step(self):
        self.avoid_step += 1
        self.avoid_step_since_ms = time.ticks_ms()

    def _debug_print(self, text):
        now = time.ticks_ms()

        if time.ticks_diff(now, self.last_debug_ms) < self.debug_interval_ms:
            return

        print(text)
        self.last_debug_ms = now

    def _motor_debug_text(self):
        if self.motors is None:
            return ""

        left_speed, right_speed = self.motors.get_last_speeds()
        left_freq, right_freq = self.motors.get_last_frequencies()

        return (
            " Speed L/R: "
            + str(round(left_speed, 1))
            + " "
            + str(round(right_speed, 1))
            + " Freq L/R: "
            + str(left_freq)
            + " "
            + str(right_freq)
        )

    def _line_debug_text(self):
        if self.line_sensor is None:
            return ""

        values = self.line_sensor.read_values()
        bits = self.line_sensor.get_bits()

        return " Sensoren: " + str(values) + " Bits: " + bin(bits)

    def _debug_state(self, extra=""):
        text = "State: " + self.state + " Ziel: " + str(self.drive_target)

        if extra:
            text += " " + extra

        text += self._motor_debug_text()
        self._debug_print(text)
    
    def _line_found_during_avoidance(self):
        if self.line_sensor is None:
            return False

        position = self.line_sensor.get_position(force=True)

        if position == "street":
            if self.motors is not None:
                self.motors.stop()
            self.set_state(self.STATE_WAIT_AT_STREET)
            return True

        return position is not None
    
    def _left_obstacle_detected(self):
        if self.obstacle_sensors is None:
            return False

        self.obstacle_sensors.measure_left()
        return not self.obstacle_sensors.left_is_clear()

    def _right_obstacle_detected(self):
        if self.obstacle_sensors is None:
            return False

        self.obstacle_sensors.measure_right()
        return not self.obstacle_sensors.right_is_clear()

    def request_goto_street(self):
        if self.state == self.STATE_AT_HOME:
            self.set_state(self.STATE_MANUAL_GOTO_STREET_REQUEST)
        else:
            print("Befehl goto_street ignoriert in State:", self.state)

    def _logic_manual_goto_street_request(self):
        print("Manuelle Anforderung: Fahrt zur Strasse")
        self.drive_target = "street"
        self.set_state(self.STATE_LINE_FOLLOWING)


    def request_return_home(self):
        if self.state == self.STATE_WAIT_AT_STREET:
            self.set_state(self.STATE_MANUAL_RETURN_HOME_REQUEST)
        else:
            print("Befehl goto_home ignoriert in State:", self.state)
    
    def _logic_manual_return_home_request(self):
        print("Manuelle Anforderung: Rueckfahrt nach Hause")
        self.drive_target = "home"
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
            self.state_before_pause = self.state
            self.set_state(self.STATE_USER_PAUSED)

    def resume(self):
        if self.state == self.STATE_USER_PAUSED:
            self.set_state(self.state_before_pause)

    def stop(self):
        if self.motors:
            self.motors.stop()
        self.set_state(self.STATE_AT_HOME)
    
    def handle_touch_action(self, action):
        print("Touch-Action:", action)

        if action == "goto_street":
            self.request_goto_street()
            return

        if action == "goto_home":
            self.request_return_home()
            return

        if action == "shutdown":
            self.stop()
            return

    def run(self):
        if self.touchpanel is not None:
            self.touchpanel.tick()
        if self.state == self.STATE_AT_HOME:
            self._logic_at_home()
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
        elif self.state == self.STATE_TURN_AT_HOME:
            self._logic_turn_at_home()
        elif self.state == self.STATE_MANUAL_GOTO_STREET_REQUEST:
            self._logic_manual_goto_street_request()
        elif self.state == self.STATE_MANUAL_RETURN_HOME_REQUEST:
            self._logic_manual_return_home_request()

    def _logic_at_home(self):
        if self.motors is not None:
            self.motors.stop()

        if self.buzzer is not None:
            self.buzzer.stop()

        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="full_home",
                location="home",
            )

        self._debug_state("warte")
            

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

            if self.drive_target == "home":
                self.set_state(self.STATE_TURN_AT_HOME)
            else:
                self.set_state(self.STATE_WAIT_AT_STREET)

            return

        if position is None:
            self.set_state(self.STATE_LINE_LOST)
            return
        
        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="line_ok",
                line_ok=True,
            )

        self.last_line_seen_ms = time.ticks_ms()

        left_speed, right_speed, correction = self.pd_controller.get_motor_speeds(
            current_position=position,
            base_speed=self.base_speed,
            min_speed=self.min_speed,
            max_speed=self.max_speed,
        )

        line_values = self.line_sensor.read_values()

        self._debug_print(
            "LINE_FOLLOWING | Ziel: "
            + str(self.drive_target)
            + " | Sensoren: "
            + str(line_values)
            + " | Position: "
            + str(position)
            + " | Korrektur: "
            + str(round(correction, 1))
            + " | Speed L/R: "
            + str(round(left_speed, 1))
            + " / "
            + str(round(right_speed, 1))
        )

        self.last_left_speed = left_speed
        self.last_right_speed = right_speed

        self.motors.drive_forward_differential(left_speed, right_speed)

        self._debug_print(
            "State: "
            + self.state
            + " Ziel: "
            + str(self.drive_target)
            + self._line_debug_text()
            + " Position: "
            + str(position)
            + " Correction: "
            + str(round(correction, 1))
            + self._motor_debug_text()
        )

    def _logic_line_lost(self):
        if self.motors is None:
            return

        position = None
        if self.line_sensor is not None:
            position = self.line_sensor.get_position()

        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="line_lost",
                line_ok=False,
            )

        if position == "street":
            self.motors.stop()

            if self.drive_target == "home":
                self.set_state(self.STATE_TURN_AT_HOME)
            else:
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

            self._debug_print(
                "State: "
                + self.state
                + " Ziel: "
                + str(self.drive_target)
                + self._line_debug_text()
                + " Linie verloren, fahre weiter mit letzter Speed L/R: "
                + str(round(self.last_left_speed, 1))
                + " "
                + str(round(self.last_right_speed, 1))
                + self._motor_debug_text()
            )
        else:
            self.motors.stop()
            self.set_state(self.STATE_AT_HOME)

    def _logic_obstacle_wait(self):
        if self.motors is not None:
            self.motors.stop()
        
        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="obstacle",
                obstacle_cm=0,
            )

        wait_time_ms = time.ticks_diff(time.ticks_ms(), self.state_since_ms)

        front_distance = None
        if self.obstacle_sensors is not None:
            front_distance = self.obstacle_sensors.front.read_distance_cm()

        self._debug_state(
            "Hindernis vorne: "
            + str(front_distance)
            + " cm Wartezeit ms: "
            + str(wait_time_ms)
        )

        if wait_time_ms < self.obstacle_wait_ms:
            return

        if self.obstacle_sensors is None:
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        self.obstacle_sensors.measure_right()
        right_free = self.obstacle_sensors.right_is_clear()

        self.obstacle_sensors.measure_left()
        left_free = self.obstacle_sensors.left_is_clear()

        if right_free:
            self.avoid_side = "right"
            self.set_state(self.STATE_AVOID_RIGHT)
            return

        if left_free:
            self.avoid_side = "left"
            self.set_state(self.STATE_AVOID_LEFT)
            return

        self.avoid_side = None
        self.set_state(self.STATE_AVOID_NOT_POSSIBLE)


    def _logic_avoid_right(self):
        if self.motors is None:
            return

        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="obstacle",
                obstacle_cm=0,
            )

        elapsed = time.ticks_diff(time.ticks_ms(), self.avoid_step_since_ms)

        self._debug_print(
            "State: "
            + self.state
            + " Ziel: "
            + str(self.drive_target)
            + " Avoid-Step: "
            + str(self.avoid_step)
            + " Elapsed ms: "
            + str(elapsed)
            + self._line_debug_text()
            + self._motor_debug_text()
        )

        # Schritt 0: 90 Grad nach rechts drehen
        if self.avoid_step == 0:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_right(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self._next_avoid_step()
            return

        # Schritt 1: Geradeaus fahren, bis das Hindernis links erkannt wird
        if self.avoid_step == 1:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 2: Weiterfahren, bis das Hindernis links nicht mehr erkannt wird
        if self.avoid_step == 2:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if not self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 3: 15000 Zusatzschritte geradeaus
        if self.avoid_step == 3:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # Schritt 4: 90 Grad nach links drehen
        if self.avoid_step == 4:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_left(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self._next_avoid_step()
            return

        # Schritt 5: Geradeaus fahren, bis das Hindernis links wieder erkannt wird
        if self.avoid_step == 5:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 6: Weiterfahren, bis das Hindernis links nicht mehr erkannt wird
        if self.avoid_step == 6:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if not self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 7: Wieder 15000 Zusatzschritte geradeaus
        if self.avoid_step == 7:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # Schritt 8: 90 Grad nach links drehen, zurück Richtung Linie
        if self.avoid_step == 8:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_left(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self._next_avoid_step()
            return

        # Schritt 9: Geradeaus fahren, bis die Linie erkannt wird
        if self.avoid_step == 9:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_line_search_max_ms:
                self.motors.stop()
                self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # Schritt 10: 90 Grad nach rechts drehen, danach wieder Linienfolge
        if self.avoid_step == 10:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_right(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self.set_state(self.STATE_LINE_FOLLOWING)
            return

    def _logic_avoid_left(self):
        if self.motors is None:
            return
        
        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="obstacle",
                obstacle_cm=0,
            )

        elapsed = time.ticks_diff(time.ticks_ms(), self.avoid_step_since_ms)

        self._debug_print(
            "State: "
            + self.state
            + " Ziel: "
            + str(self.drive_target)
            + " Avoid-Step: "
            + str(self.avoid_step)
            + " Elapsed ms: "
            + str(elapsed)
            + self._line_debug_text()
            + self._motor_debug_text()
        )

        # Schritt 0: 90 Grad nach links drehen
        if self.avoid_step == 0:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_left(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self._next_avoid_step()
            return

        # Schritt 1: Geradeaus fahren, bis das Hindernis rechts erkannt wird
        if self.avoid_step == 1:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 2: Weiterfahren, bis das Hindernis rechts nicht mehr erkannt wird
        if self.avoid_step == 2:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if not self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 3: 15000 Zusatzschritte geradeaus
        if self.avoid_step == 3:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # Schritt 4: 90 Grad nach rechts drehen
        if self.avoid_step == 4:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_right(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self._next_avoid_step()
            return

        # Schritt 5: Geradeaus fahren, bis das Hindernis rechts wieder erkannt wird
        if self.avoid_step == 5:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 6: Weiterfahren, bis das Hindernis rechts nicht mehr erkannt wird
        if self.avoid_step == 6:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if not self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # Schritt 7: Wieder 15000 Zusatzschritte geradeaus
        if self.avoid_step == 7:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # Schritt 8: 90 Grad nach rechts drehen, zurück Richtung Linie
        if self.avoid_step == 8:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_right(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self._next_avoid_step()
            return

        # Schritt 9: Geradeaus fahren, bis die Linie erkannt wird
        if self.avoid_step == 9:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = 10
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_line_search_max_ms:
                self.motors.stop()
                self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # Schritt 10: 90 Grad nach links drehen, danach wieder Linienfolge
        if self.avoid_step == 10:
            if self.avoid_turn_90_ms == 0:
                self.avoid_turn_90_ms = self.motors.steps_to_ms(
                    self.avoid_turn_90_steps,
                    self.avoid_turn_speed
                )

            self.motors.turn_left(self.avoid_turn_speed)

            if elapsed >= self.avoid_turn_90_ms:
                self.avoid_turn_90_ms = 0
                self.motors.stop()
                self.set_state(self.STATE_LINE_FOLLOWING)
            return

    def _logic_avoid_not_possible(self):
        if self.motors is not None:
            self.motors.stop()

        if self.buzzer is not None:
            if not self.help_buzzer_started:
                self.buzzer.play(
                    [
                        (True, 300),
                        (False, 300),
                        (True, 300),
                        (False, 300),
                        (True, 300),
                        (False, 1000),
                    ],
                    repeat=True,
                    repeat_min_ms=1000,
                    repeat_max_ms=1000,
                )
                self.help_buzzer_started = True

            self.buzzer.run()

        if self.touchpanel is not None:
            self.touchpanel.set_status(status_kind="help")
        
        if self.obstacle_sensors is not None:
            self.obstacle_sensors.run_front(force=True)

            if self.obstacle_sensors.front_obstacle_detected():
                self.help_front_clear_since_ms = None
            else:
                now = time.ticks_ms()

                if self.help_front_clear_since_ms is None:
                    self.help_front_clear_since_ms = now

                clear_time_ms = time.ticks_diff(now, self.help_front_clear_since_ms)

                if clear_time_ms >= self.help_resume_delay_ms:
                    if self.buzzer is not None:
                        self.buzzer.stop()

                    self.set_state(self.STATE_LINE_FOLLOWING)
                    return

        self._debug_state("Hilfe benoetigt / warte 5s bis vorne frei bleibt")

    def _logic_wait_at_street(self):
        if self.motors is not None:
            self.motors.stop()

        if self.buzzer is not None:
            self.buzzer.stop()

        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="full_home",
                location="truck",
                line_ok=True,
            )

        self._debug_state("warte an der Strasse")

    def _logic_turn_at_home(self):
        if self.motors is None:
            return

        if self.turn_home_180_ms == 0:
            self.turn_home_180_ms = self.motors.steps_to_ms(
                self.turn_home_180_steps,
                self.avoid_turn_speed
            )

        elapsed = time.ticks_diff(time.ticks_ms(), self.state_since_ms)

        self.motors.turn_right(self.avoid_turn_speed)

        self._debug_state(
            "180-Grad-Drehung zuhause Elapsed ms: "
            + str(elapsed)
            + " Zielzeit ms: "
            + str(self.turn_home_180_ms)
        )

        if elapsed >= self.turn_home_180_ms:
            self.motors.stop()
            self.turn_home_180_ms = 0
            self.set_state(self.STATE_AT_HOME)

    def _logic_user_paused(self):
        if self.motors is not None:
            self.motors.stop()

        if self.buzzer is not None:
            self.buzzer.stop()

        self._debug_state("pausiert")
