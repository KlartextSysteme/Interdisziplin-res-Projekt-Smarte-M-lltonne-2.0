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
    STATE_TURN_AT_STREET = "TURN_AT_STREET"
    STATE_TURN_AT_HOME = "TURN_AT_HOME"
    # Zustände für manuelle Anforderungen per Touchpanel
    STATE_MANUAL_GOTO_STREET_REQUEST = "MANUAL_GOTO_STREET_REQUEST"
    STATE_MANUAL_RETURN_HOME_REQUEST = "MANUAL_RETURN_HOME_REQUEST"
    STATE_PARTY = "PARTY"   # Easter-Egg: dreht sich + Buzzer-Jingle
    #Zustände aus der Webapp

    # --- Unterzustände für AVOID_RIGHT ---
    AVOID_RIGHT_TURN_OUT = 0
    AVOID_RIGHT_FIND_OBSTACLE = 1
    AVOID_RIGHT_PASS_OBSTACLE = 2
    AVOID_RIGHT_EXTRA_AFTER_PASS = 3
    AVOID_RIGHT_TURN_PARALLEL = 4
    AVOID_RIGHT_FIND_OBSTACLE_AGAIN = 5
    AVOID_RIGHT_PASS_OBSTACLE_AGAIN = 6
    AVOID_RIGHT_EXTRA_AFTER_SECOND_PASS = 7
    AVOID_RIGHT_TURN_TO_LINE = 8
    AVOID_RIGHT_SEARCH_LINE = 9
    AVOID_RIGHT_ALIGN_ON_LINE = 10

    # --- Unterzustände für AVOID_LEFT ---
    AVOID_LEFT_TURN_OUT = 0
    AVOID_LEFT_FIND_OBSTACLE = 1
    AVOID_LEFT_PASS_OBSTACLE = 2
    AVOID_LEFT_EXTRA_AFTER_PASS = 3
    AVOID_LEFT_TURN_PARALLEL = 4
    AVOID_LEFT_FIND_OBSTACLE_AGAIN = 5
    AVOID_LEFT_PASS_OBSTACLE_AGAIN = 6
    AVOID_LEFT_EXTRA_AFTER_SECOND_PASS = 7
    AVOID_LEFT_TURN_TO_LINE = 8
    AVOID_LEFT_SEARCH_LINE = 9
    AVOID_LEFT_ALIGN_ON_LINE = 10

    def __init__(
        self,
        line_sensor=None,
        obstacle_sensors=None,
        pd_controller=None,
        motors=None,
        buzzer=None,
        fuellstand_sensor=None,
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
        self.fuellstand_sensor = fuellstand_sensor
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
        self.obstacle_stop_cm = 15
        self.avoid_side = None

        self.avoid_speed = 35
        self.avoid_turn_speed = 35

        self.avoid_forward_ms = 900
        self.avoid_side_max_ms = 5000
        self.avoid_line_search_max_ms = 6000

        self.help_front_clear_since_ms = None
        self.help_resume_delay_ms = 5000

        # müssen noch angepasst werden
        self.avoid_turn_90_steps = 22000
        self.turn_home_180_steps = 44000

        self.avoid_turn_90_ms = 0
        self.turn_home_180_ms = 0
        self.turn_street_180_ms = 0
        self.turn_home_back_to_line = False
        self.turn_home_back_timeout_ms = 5000

        self.avoid_step = 0
        self.avoid_step_since_ms = time.ticks_ms()

        self.state_before_pause = self.STATE_AT_HOME

        #müssen noch konfiguriert werden
        self.side_obstacle_cm = 80
        self.avoid_extra_steps = 40000
        self.avoid_extra_ms = 0

        self.obstacle_side_min_samples = 3

        # Entlangphase (PASS_OBSTACLE_AGAIN): "Hindernis passiert" erst nach
        # mehreren KONSEKUTIVEN Frei-Messungen bestaetigen. Eine einzelne
        # None-Messung (kein Echo direkt neben dem Hindernis) darf das
        # Vorbeifahren NICHT vorzeitig beenden -> sonst dreht sie ins Hindernis.
        self.avoid_along_clear_needed = 5
        self._avoid_along_clear_count = 0

        self.obstacle_right_clear_count = 0
        self.obstacle_right_blocked_count = 0
        self.obstacle_left_clear_count = 0
        self.obstacle_left_blocked_count = 0
        self.obstacle_last_right_cm = None
        self.obstacle_last_left_cm = None

        self.help_buzzer_started = False
        self.line_lost_alarm_started = False
        self.drive_target = None

        # -------- zum Testen --------
        self.last_debug_ms = time.ticks_ms()
        self.debug_interval_ms = 250

        # Touchpanel-Tick waehrend der Fahrt drosseln, damit der SPI-Touch-Read
        # die PD-Regelung nicht jeden Zyklus ausbremst (enges Regel-Raster).
        self.last_touch_tick_ms = time.ticks_ms()
        self.touch_tick_interval_ms = 150

        # Der Fahr-Status wird nur EINMAL pro Fahrt aufs Display geschrieben.
        # set_status() loest sofort ein volles ILI9341-Redraw (~30-80ms) aus;
        # pro Regeltakt aufgerufen bricht das die PD-Regelung komplett ein.
        self._drive_panel_shown = False

        # Zuletzt gesehene (numerische) Linienposition. Bei kurzem Linienverlust
        # dreht die Recovery in diese Richtung fest nach, statt gerade zu coasten.
        self.last_known_position = None
        self.line_lost_recover_correction = 60

        # TCP-Bridge-Client (Web-App-Steuerung). Wird von main.py via
        # set_network_client gesetzt; None = rein lokal ueber Touchpanel.
        self.network_client = None

        # Anfahr-Rampe (exponentieller Anlauf): das Reisetempo ist self.base_speed,
        # bei jeder frischen Fahrt startet die Geschwindigkeit bei ramp_start_speed
        # und naehert sich exponentiell (Zeitkonstante ramp_tau_ms) dem Reisetempo.
        # Zeitbasiert (IIR) -> ruckfrei und robust gegen Loop-Jitter.
        self.ramp_start_speed = 20
        self.ramp_tau_ms = 500
        self._current_base = self.base_speed
        self._last_ramp_ms = time.ticks_ms()

        # Kurven-adaptives Reisetempo: self.base_speed gilt auf der Geraden,
        # in der schaerfsten Kurve wird bis auf speed_curve heruntergedrosselt.
        # Adaption neutralisiert: speed_curve == base_speed -> konstantes Tempo.
        # (Beim Tempo-Test nur EINE Variable aendern.)
        self.speed_curve = 60

        # --- Party-Modus (Easter-Egg via PIN "***") ---
        # Step-basiert: N volle Umdrehungen (360deg = 2x turn_home_180_steps),
        # damit die Tonne exakt in der Startausrichtung endet (Linie wieder da).
        # Dauer wird beim Start aus Schrittzahl x Tempo berechnet.
        self.party_full_rotations = 1
        self.party_duration_ms = 10000   # Fallback, wird in set_state neu berechnet
        self.party_speed = 65
        self.party_buzzer_started = False
        # "Shave and a haircut, two bits" - als reiner Rhythmus auch bei festem
        # Ton sofort erkennbar (aktiver Buzzer kann keine Tonhoehen).
        self.party_pattern = [
            (True, 200), (False, 110),   # Shave
            (True, 110), (False, 70),    # and
            (True, 110), (False, 110),   # a
            (True, 200), (False, 110),   # hair
            (True, 240), (False, 380),   # cut  (+ Pause)
            (True, 200), (False, 130),   # two
            (True, 260), (False, 500),   # bits (+ Pause vor Wiederholung)
        ]

    def set_state(self, new_state):
        if self.state == new_state:
            return

        print("State:", self.state, "->", new_state)
        previous_state = self.state
        self.state = new_state
        self.state_since_ms = time.ticks_ms()

        # Bridge/Web-App ueber das Erreichen eines Ziels informieren.
        # ARRIVED: STREET beim Anhalten an der Abholpos, ARRIVED: HOME wenn die
        # Ruecktour (ueber TURN_AT_HOME) im Heim-Zustand endet.
        if new_state == self.STATE_WAIT_AT_STREET:
            self._bridge_send("ARRIVED: STREET")
        if new_state == self.STATE_AT_HOME and previous_state == self.STATE_TURN_AT_HOME:
            self._bridge_send("ARRIVED: HOME")

        # Sobald ein Nicht-Fahr-Zustand einen eigenen Screen zeigt, muss der
        # Fahr-Status bei der naechsten Fahrt erneut (einmalig) gesetzt werden.
        if new_state not in (self.STATE_LINE_FOLLOWING, self.STATE_LINE_LOST):
            self._drive_panel_shown = False

        if new_state == self.STATE_LINE_FOLLOWING:
            self.last_line_seen_ms = self.state_since_ms
            self.last_left_speed = self.base_speed
            self.last_right_speed = self.base_speed

            # Anlauframpe nur bei einer FRISCHEN Fahrt neu starten, nicht wenn wir
            # nur aus einem kurzen Linienverlust zurueckkommen (sonst Dauer-Kriechen).
            if previous_state != self.STATE_LINE_LOST:
                self._current_base = self.ramp_start_speed
                self._last_ramp_ms = self.state_since_ms

        if new_state == self.STATE_LINE_LOST:
            self.line_lost_alarm_started = False

        if new_state == self.STATE_PARTY:
            self.party_buzzer_started = False
            # Dauer = N volle Umdrehungen bei Party-Tempo -> endet exakt am Start.
            if self.motors is not None:
                rotation_steps = 2 * self.turn_home_180_steps * self.party_full_rotations
                self.party_duration_ms = self.motors.steps_to_ms(
                    rotation_steps, self.party_speed
                )

        if new_state == self.STATE_OBSTACLE_WAIT:
            self._reset_obstacle_side_samples()

        if new_state == self.STATE_AT_HOME:
            self.drive_target = None

        if new_state in (self.STATE_AVOID_RIGHT, self.STATE_AVOID_LEFT):
            self.avoid_step = 0
            self.avoid_extra_ms = 0
            self.avoid_step_since_ms = self.state_since_ms
        if new_state == self.STATE_AVOID_NOT_POSSIBLE:
            self.help_buzzer_started = False
            self.help_front_clear_since_ms = None
        if new_state == self.STATE_TURN_AT_HOME:
            self.turn_home_180_ms = 0
            self.turn_home_back_to_line = False
        if new_state == self.STATE_TURN_AT_STREET:
            self.turn_street_180_ms = 0
        
        if new_state in (
            self.STATE_LINE_FOLLOWING,
            self.STATE_AT_HOME,
            self.STATE_WAIT_AT_STREET,
            self.STATE_USER_PAUSED,
            self.STATE_TURN_AT_HOME,
            self.STATE_TURN_AT_STREET,
        ):
            if self.buzzer is not None:
                self.buzzer.stop()
    
    def _next_avoid_step(self):
        self.avoid_step += 1
        self.avoid_step_since_ms = time.ticks_ms()
        self._avoid_along_clear_count = 0

    def _confirm_side_clear_along(self, still_detected):
        """Entprellt die 'Hindernis passiert'-Erkennung in der Entlangphase.

        still_detected=True (Hindernis seitlich noch da) setzt den Zaehler
        zurueck. Erst nach avoid_along_clear_needed KONSEKUTIVEN Frei-Messungen
        gilt das Hindernis als passiert -> ein einzelnes fehlendes Echo (None)
        neben dem Hindernis beendet das Vorbeifahren nicht mehr vorzeitig.
        """
        if still_detected:
            self._avoid_along_clear_count = 0
            return False
        self._avoid_along_clear_count += 1
        return self._avoid_along_clear_count >= self.avoid_along_clear_needed

    def _debug_print(self, text):
        now = time.ticks_ms()

        if time.ticks_diff(now, self.last_debug_ms) < self.debug_interval_ms:
            return

        print(text)
        self.last_debug_ms = now

    def _read_fuellstand_for_status(self):
        if self.fuellstand_sensor is None:
            return None

        self.fuellstand_sensor.run()
        fill_level = self.fuellstand_sensor.get_fuellstand_prozent()

        self._debug_print(
            "Fuellstand-Test | Abstand cm: "
            + str(self.fuellstand_sensor.last_distance_cm)
            + " | Fuellstand: "
            + str(fill_level)
            + " | Deckel offen: "
            + str(self.fuellstand_sensor.is_deckel_offen())
        )

        return fill_level

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

    def _us_debug_text(self):
        if self.obstacle_sensors is None:
            return ""

        # Fuer die Debug-Ausgabe bewusst frisch messen.
        # Achtung: Ultraschallmessungen sind blockierend und verlangsamen den Loop.
        front = self.obstacle_sensors.run_front(force=True)
        left = self.obstacle_sensors.measure_left()
        right = self.obstacle_sensors.measure_right()

        return (
            " US vorne/links/rechts cm: "
            + str(front)
            + " / "
            + str(left)
            + " / "
            + str(right)
        )


    def _debug_state(self, extra=""):
        text = "State: " + self.state + " Ziel: " + str(self.drive_target)

        if extra:
            text += " " + extra

        text += self._motor_debug_text()
        self._debug_print(text)
    
    def _reset_obstacle_side_samples(self):
        self.obstacle_right_clear_count = 0
        self.obstacle_right_blocked_count = 0
        self.obstacle_left_clear_count = 0
        self.obstacle_left_blocked_count = 0
        self.obstacle_last_right_cm = None
        self.obstacle_last_left_cm = None

    def _update_obstacle_side_samples(self):
        if self.obstacle_sensors is None:
            return

        self.obstacle_last_right_cm = self.obstacle_sensors.measure_right()
        if self.obstacle_sensors.right_is_clear():
            self.obstacle_right_clear_count += 1
        else:
            self.obstacle_right_blocked_count += 1

        self.obstacle_last_left_cm = self.obstacle_sensors.measure_left()
        if self.obstacle_sensors.left_is_clear():
            self.obstacle_left_clear_count += 1
        else:
            self.obstacle_left_blocked_count += 1

    def _right_confirmed_free(self):
        return (
            self.obstacle_right_clear_count >= self.obstacle_side_min_samples
            and self.obstacle_right_clear_count > self.obstacle_right_blocked_count
        )

    def _left_confirmed_free(self):
        return (
            self.obstacle_left_clear_count >= self.obstacle_side_min_samples
            and self.obstacle_left_clear_count > self.obstacle_left_blocked_count
        )

    def _obstacle_side_debug_text(self):
        return (
            " US rechts: "
            + str(self.obstacle_last_right_cm)
            + " frei/blockiert: "
            + str(self.obstacle_right_clear_count)
            + "/"
            + str(self.obstacle_right_blocked_count)
            + " | US links: "
            + str(self.obstacle_last_left_cm)
            + " frei/blockiert: "
            + str(self.obstacle_left_clear_count)
            + "/"
            + str(self.obstacle_left_blocked_count)
        )

    def _line_found_during_avoidance(self):
        if self.line_sensor is None:
            return False

        position = self.line_sensor.get_position(force=True)

        if position == "end_marker":
            if self.motors is not None:
                self.motors.stop()

            if self.drive_target == "home":
                self.set_state(self.STATE_TURN_AT_HOME)
            else:
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
        self.set_state(self.STATE_TURN_AT_STREET)

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

        if action == "report_damage":
            self._bridge_send("REPORT:DAMAGE")
            return

        if action == "report_hygiene":
            self._bridge_send("REPORT:HYGIENE")
            return

        if action == "eco":
            if self.touchpanel is not None:
                self.touchpanel.toggle_eco()
            return

        if action == "party":
            self.request_party()
            return

        if action == "shutdown":
            self.stop()
            return

    def request_party(self):
        # Easter-Egg: nur aus dem Leerlauf starten (braucht Platz zum Drehen).
        if self.state == self.STATE_AT_HOME:
            print("PARTY MODE! 🎉")
            self.set_state(self.STATE_PARTY)

    def _logic_party(self):
        elapsed = time.ticks_diff(time.ticks_ms(), self.state_since_ms)

        if elapsed >= self.party_duration_ms:
            if self.motors is not None:
                self.motors.stop()
            if self.buzzer is not None:
                self.buzzer.stop()
            self.set_state(self.STATE_AT_HOME)
            return

        # Zuegig auf der Stelle drehen ...
        if self.motors is not None:
            self.motors.turn_right(self.party_speed)

        # ... und den Buzzer-Jingle in Dauerschleife spielen.
        if self.buzzer is not None:
            if not self.party_buzzer_started:
                self.buzzer.play(self.party_pattern, repeat=True)
                self.party_buzzer_started = True
            self.buzzer.run()

    def set_network_client(self, client):
        """Verknuepft den TCP-Bridge-Client fuer Web-App-Steuerung/Status."""
        self.network_client = client

    def _bridge_send(self, line):
        """Sendet eine Zeile an die Bridge, sofern verbunden (fehlertolerant)."""
        if self.network_client is None:
            return
        try:
            self.network_client.send_line(line)
        except Exception as exc:
            print("Bridge send failed:", exc)

    def handle_network_command(self, cmd):
        """Von der Bridge eingehende Befehle. Sendet ACK (sonst gilt der
        Web-App-Befehl als offen) und loest die passende Aktion aus."""
        cmd = str(cmd).strip()
        print("Network-Command:", cmd)

        if cmd.startswith("ACK_RECEIVED"):
            return

        if cmd in ("CMD_GOTO_STREET", "GOTO_STREET", "goto_street", "goto_pickup"):
            self._bridge_send("ACK CMD_GOTO_STREET")
            self._bridge_send("STATUS:MANUAL_GOTO_STREET_REQUEST")
            self.request_goto_street()
            return

        if cmd in ("CMD_RETURN_HOME", "RETURN_HOME", "goto_home", "return_home"):
            self._bridge_send("ACK CMD_RETURN_HOME")
            self._bridge_send("STATUS:MANUAL_RETURN_HOME_REQUEST")
            self.request_return_home()
            return

        if cmd in ("CMD_STOP", "STOP", "stop", "pause"):
            self._bridge_send("ACK CMD_STOP")
            self.pause()
            return

        if cmd in ("CMD_RESUME", "RESUME", "resume"):
            self.resume()
            return

        print("Unbekannter Network-Command:", cmd)

    def get_network_status(self):
        """Liefert den periodischen STATUS-String fuer die Bridge. Auf die
        von Backend/Web-App bekannten Werte der Inline-Firmware gemappt."""
        s = self.state
        if s in (self.STATE_AT_HOME, self.STATE_PARTY):
            return "STANDBY"
        if s == self.STATE_OBSTACLE_WAIT:
            return "OBSTACLE"
        # Transiente Fahr-/Dreh-/Ausweich-Zustaende bleiben nach aussen "unterwegs".
        if s in (
            self.STATE_LINE_LOST,
            self.STATE_TURN_AT_HOME,
            self.STATE_TURN_AT_STREET,
            self.STATE_AVOID_RIGHT,
            self.STATE_AVOID_LEFT,
            self.STATE_AVOID_NOT_POSSIBLE,
        ):
            return "LINE_FOLLOWING"
        return s

    def run(self):
        if self.touchpanel is not None:
            # Waehrend der Fahrt den Touch-Read drosseln (er blockiert sonst die
            # Regelung); im Leerlauf jeden Zyklus, damit das Menue flott bleibt.
            driving = self.state in (
                self.STATE_LINE_FOLLOWING,
                self.STATE_LINE_LOST,
                self.STATE_TURN_AT_HOME,
                self.STATE_TURN_AT_STREET,
                self.STATE_AVOID_RIGHT,
                self.STATE_AVOID_LEFT,
                self.STATE_AVOID_NOT_POSSIBLE,
            )
            now = time.ticks_ms()
            if (not driving) or time.ticks_diff(now, self.last_touch_tick_ms) >= self.touch_tick_interval_ms:
                self.last_touch_tick_ms = now
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
        elif self.state == self.STATE_TURN_AT_STREET:
            self._logic_turn_at_street()
        elif self.state == self.STATE_MANUAL_GOTO_STREET_REQUEST:
            self._logic_manual_goto_street_request()
        elif self.state == self.STATE_MANUAL_RETURN_HOME_REQUEST:
            self._logic_manual_return_home_request()
        elif self.state == self.STATE_PARTY:
            self._logic_party()

    def _logic_at_home(self):
        if self.motors is not None:
            self.motors.stop()

        if self.buzzer is not None:
            self.buzzer.stop()

        fill_level = self._read_fuellstand_for_status()

        if self.touchpanel is not None:
            if fill_level is None:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="home",
                )
            else:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="home",
                    fill_level=fill_level,
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

        if position == "end_marker":
            self.motors.stop()

            if self.drive_target == "home":
                self.set_state(self.STATE_TURN_AT_HOME)
            else:
                self.set_state(self.STATE_WAIT_AT_STREET)

            return

        if position is None:
            self.set_state(self.STATE_LINE_LOST)
            return

        # Fahr-Status GENAU EINMAL pro Fahrt setzen. Ein set_status() pro
        # Regeltakt wuerde jedes Mal ein volles Display-Redraw ausloesen und
        # die PD-Regelung ausbremsen (Ueberschwingen -> Linie verloren).
        if not self._drive_panel_shown and self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="line_ok",
                line_ok=True,
            )
            self._drive_panel_shown = True

        now_ms = time.ticks_ms()
        self.last_line_seen_ms = now_ms
        self.last_known_position = position

        # Exponentieller Anlauf: _current_base naehert sich pro Tick dem Reisetempo
        # (self.base_speed). alpha = dt/tau ist die zeitbasierte Annaeherungsrate.
        # --- Kurven-adaptives Reisetempo mit Anlauframpe ---
        # Kurvenschaerfe aus der vorigen PD-Korrektur ableiten (grosse Korrektur =
        # Linie weit aussen = Kurve). Ziel: base_speed auf der Geraden, linear
        # heruntergedrosselt bis speed_curve in der schaerfsten Kurve.
        prev_corr = abs(self.pd_controller.last_correction)
        curve_factor = prev_corr / self.pd_controller.max_correction
        if curve_factor > 1.0:
            curve_factor = 1.0
        target_base = self.speed_curve + (self.base_speed - self.speed_curve) * (1.0 - curve_factor)

        dt_ms = time.ticks_diff(now_ms, self._last_ramp_ms)
        self._last_ramp_ms = now_ms
        if dt_ms < 0:
            dt_ms = 0
        if target_base <= self._current_base:
            # In die Kurve abbremsen: sofort (Sicherheit vor Tempo).
            self._current_base = target_base
        else:
            # Beschleunigen (Anfahrt / Kurvenausgang): exponentiell gerampt,
            # damit die Schrittmotoren nicht durchrutschen / Schritte verlieren.
            alpha = dt_ms / self.ramp_tau_ms
            if alpha > 1.0:
                alpha = 1.0
            self._current_base += (target_base - self._current_base) * alpha

        left_speed, right_speed, correction = self.pd_controller.get_motor_speeds(
            current_position=position,
            base_speed=self._current_base,
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

        # Kein set_status pro Tick: LINE_LOST flattert bei duenner Linie staendig,
        # ein Redraw je Tick wuerde die Wiedererfassung der Linie ausbremsen.
        # Der "Linie verloren"-Screen kommt erst beim echten Timeout-Alarm (unten).

        if position == "end_marker":
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
            # In Richtung der zuletzt gesehenen Linienseite fest nachdrehen,
            # damit Kurven/Luecken schnell wieder eingefangen werden. Nur wenn
            # die Linie zuletzt mittig (0) war, geradeaus mit letzter Speed.
            if self.last_known_position is not None and self.last_known_position != 0:
                sign = 1.0 if self.last_known_position > 0 else -1.0
                c = self.line_lost_recover_correction * sign
                recover_left = self._current_base - c
                recover_right = self._current_base + c
                recover_left = min(self.max_speed, max(self.min_speed, recover_left))
                recover_right = min(self.max_speed, max(self.min_speed, recover_right))
                self.motors.drive_forward_differential(recover_left, recover_right)
            else:
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
                + " Linie verloren, Recovery Richtung "
                + str(self.last_known_position)
                + self._motor_debug_text()
            )
        else:
            self.motors.stop()

            if not self.line_lost_alarm_started and self.touchpanel is not None:
                self.touchpanel.set_status(
                    status_kind="line_lost",
                    line_ok=False,
                )

            if self.buzzer is not None:
                if not self.line_lost_alarm_started:
                    self.buzzer.play(
                        [
                            (True, 200),
                            (False, 200),
                            (True, 200),
                            (False, 800),
                        ],
                        repeat=True,
                        repeat_min_ms=500,
                        repeat_max_ms=500,
                    )
                    self.line_lost_alarm_started = True

                self.buzzer.run()

            self._debug_print(
                "State: "
                + self.state
                + " Ziel: "
                + str(self.drive_target)
                + self._line_debug_text()
                + " Linie seit 10s verloren, Motoren gestoppt, Buzzer aktiv"
                + self._motor_debug_text()
            )

    def _logic_obstacle_wait(self):
        if self.motors is not None:
            self.motors.stop()
        
        if self.touchpanel is not None:
            self.touchpanel.set_status(
                status_kind="obstacle",
                obstacle_cm=0,
            )

        wait_time_ms = time.ticks_diff(time.ticks_ms(), self.state_since_ms)

        if self.obstacle_sensors is None:
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        front_distance = self.obstacle_sensors.run_front(force=True)

        if not self.obstacle_sensors.front_obstacle_detected():
            self.set_state(self.STATE_LINE_FOLLOWING)
            return

        self._update_obstacle_side_samples()

        self._debug_state(
            "Hindernis vorne: "
            + str(front_distance)
            + " cm Wartezeit ms: "
            + str(wait_time_ms)
            + self._obstacle_side_debug_text()
        )

        if wait_time_ms < self.obstacle_wait_ms:
            return

        right_free = self._right_confirmed_free()
        left_free = self._left_confirmed_free()

        print(
            "Umfahrentscheidung | rechts frei:",
            right_free,
            "Werte frei/blockiert:",
            self.obstacle_right_clear_count,
            self.obstacle_right_blocked_count,
            "| links frei:",
            left_free,
            "Werte frei/blockiert:",
            self.obstacle_left_clear_count,
            self.obstacle_left_blocked_count,
        )

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
            + " Avoid-Step: "
            + str(self.avoid_step)
            + self._line_debug_text()
            + self._us_debug_text()
            + self._motor_debug_text()
        )

        # Sicherheits-Timeout (#2): die sensor-abhaengigen Vorwaerts-Schritte
        # duerfen nicht endlos fahren (z.B. dauerhaft kein Echo neben dem
        # Hindernis). Nach avoid_side_max_ms bzw. avoid_line_search_max_ms ->
        # Nothalt + Hilfe-Zustand statt Endlosfahrt/Drehen ins Hindernis.
        if self.avoid_step in (
            self.AVOID_RIGHT_FIND_OBSTACLE,
            self.AVOID_RIGHT_PASS_OBSTACLE,
            self.AVOID_RIGHT_FIND_OBSTACLE_AGAIN,
            self.AVOID_RIGHT_PASS_OBSTACLE_AGAIN,
        ) and elapsed >= self.avoid_side_max_ms:
            self.motors.stop()
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return
        if (
            self.avoid_step == self.AVOID_RIGHT_SEARCH_LINE
            and elapsed >= self.avoid_line_search_max_ms
        ):
            self.motors.stop()
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # AVOID_RIGHT_TURN_OUT: 90 Grad nach rechts drehen
        if self.avoid_step == self.AVOID_RIGHT_TURN_OUT:
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

        # AVOID_RIGHT_FIND_OBSTACLE: Geradeaus fahren, bis das Hindernis links erkannt wird
        if self.avoid_step == self.AVOID_RIGHT_FIND_OBSTACLE:
            self.motors.forward(self.avoid_speed)

            # if self._line_found_during_avoidance():
            #     self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
            #     self.avoid_turn_90_ms = 0
            #     self.avoid_step_since_ms = time.ticks_ms()
            #     return

            if self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # AVOID_RIGHT_PASS_OBSTACLE: Weiterfahren, bis das Hindernis links nicht mehr erkannt wird
        if self.avoid_step == self.AVOID_RIGHT_PASS_OBSTACLE:
            self.motors.forward(self.avoid_speed)

            # if self._line_found_during_avoidance():
            #     self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
            #     self.avoid_turn_90_ms = 0
            #     self.avoid_step_since_ms = time.ticks_ms()
            #     return

            if not self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # AVOID_RIGHT_EXTRA_AFTER_PASS: 15000 Zusatzschritte geradeaus
        if self.avoid_step == self.AVOID_RIGHT_EXTRA_AFTER_PASS:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            # if self._line_found_during_avoidance():
            #     self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
            #     self.avoid_turn_90_ms = 0
            #     self.avoid_step_since_ms = time.ticks_ms()
            #     return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # AVOID_RIGHT_TURN_PARALLEL: 90 Grad nach links drehen
        if self.avoid_step == self.AVOID_RIGHT_TURN_PARALLEL:
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

        # AVOID_RIGHT_FIND_OBSTACLE_AGAIN: Geradeaus fahren, bis das Hindernis links wieder erkannt wird
        if self.avoid_step == self.AVOID_RIGHT_FIND_OBSTACLE_AGAIN:
            self.motors.forward(self.avoid_speed)

            # if self._line_found_during_avoidance():
            #     self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
            #     self.avoid_turn_90_ms = 0
            #     self.avoid_step_since_ms = time.ticks_ms()
            #     return

            if self._left_obstacle_detected():
                self._next_avoid_step()
            return

        # AVOID_RIGHT_PASS_OBSTACLE_AGAIN: Weiterfahren, bis das Hindernis links nicht mehr erkannt wird
        if self.avoid_step == self.AVOID_RIGHT_PASS_OBSTACLE_AGAIN:
            self.motors.forward(self.avoid_speed)

            # if self._line_found_during_avoidance():
            #     self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
            #     self.avoid_turn_90_ms = 0
            #     self.avoid_step_since_ms = time.ticks_ms()
            #     return

            # Entlangphase: erst nach mehreren konsekutiven Frei-Messungen weiter
            # (einzelnes fehlendes Echo neben dem Hindernis zaehlt nicht als "weg").
            if self._confirm_side_clear_along(self._left_obstacle_detected()):
                self._next_avoid_step()
            return

        # AVOID_RIGHT_EXTRA_AFTER_SECOND_PASS: Wieder 15000 Zusatzschritte geradeaus
        if self.avoid_step == self.AVOID_RIGHT_EXTRA_AFTER_SECOND_PASS:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            # if self._line_found_during_avoidance():
            #     self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
            #     self.avoid_turn_90_ms = 0
            #     self.avoid_step_since_ms = time.ticks_ms()
            #     return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # Schritt 8: 90 Grad nach links drehen, zurück Richtung Linie
        if self.avoid_step == self.AVOID_RIGHT_TURN_TO_LINE:
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

        # AVOID_RIGHT_SEARCH_LINE: Geradeaus fahren, bis die Linie erkannt wird
        if self.avoid_step == self.AVOID_RIGHT_SEARCH_LINE:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_RIGHT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_line_search_max_ms:
                self.motors.stop()
                self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # AVOID_RIGHT_ALIGN_ON_LINE: 90 Grad nach rechts drehen, danach wieder Linienfolge
        if self.avoid_step == self.AVOID_RIGHT_ALIGN_ON_LINE:
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
            + self._us_debug_text()
            + self._motor_debug_text()
        )

        # Sicherheits-Timeout (#2): siehe _logic_avoid_right. Nothalt + Hilfe,
        # wenn ein sensor-abhaengiger Schritt zu lange nicht bestaetigt wird.
        if self.avoid_step in (
            self.AVOID_LEFT_FIND_OBSTACLE,
            self.AVOID_LEFT_PASS_OBSTACLE,
            self.AVOID_LEFT_FIND_OBSTACLE_AGAIN,
            self.AVOID_LEFT_PASS_OBSTACLE_AGAIN,
        ) and elapsed >= self.avoid_side_max_ms:
            self.motors.stop()
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return
        if (
            self.avoid_step == self.AVOID_LEFT_SEARCH_LINE
            and elapsed >= self.avoid_line_search_max_ms
        ):
            self.motors.stop()
            self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # AVOID_LEFT_TURN_OUT: 90 Grad nach links drehen
        if self.avoid_step == self.AVOID_LEFT_TURN_OUT:
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

        # AVOID_LEFT_FIND_OBSTACLE: Geradeaus fahren, bis das Hindernis rechts erkannt wird
        if self.avoid_step == self.AVOID_LEFT_FIND_OBSTACLE:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # AVOID_LEFT_PASS_OBSTACLE: Weiterfahren, bis das Hindernis rechts nicht mehr erkannt wird
        if self.avoid_step == self.AVOID_LEFT_PASS_OBSTACLE:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if not self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # AVOID_LEFT_EXTRA_AFTER_PASS: 15000 Zusatzschritte geradeaus
        if self.avoid_step == self.AVOID_LEFT_EXTRA_AFTER_PASS:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # AVOID_LEFT_TURN_PARALLEL: 90 Grad nach rechts drehen
        if self.avoid_step == self.AVOID_LEFT_TURN_PARALLEL:
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

        # AVOID_LEFT_FIND_OBSTACLE_AGAIN: Geradeaus fahren, bis das Hindernis rechts wieder erkannt wird
        if self.avoid_step == self.AVOID_LEFT_FIND_OBSTACLE_AGAIN:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if self._right_obstacle_detected():
                self._next_avoid_step()
            return

        # AVOID_LEFT_PASS_OBSTACLE_AGAIN: Weiterfahren, bis das Hindernis rechts nicht mehr erkannt wird
        if self.avoid_step == self.AVOID_LEFT_PASS_OBSTACLE_AGAIN:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            # Entlangphase: erst nach mehreren konsekutiven Frei-Messungen weiter
            # (einzelnes fehlendes Echo neben dem Hindernis zaehlt nicht als "weg").
            if self._confirm_side_clear_along(self._right_obstacle_detected()):
                self._next_avoid_step()
            return

        # AVOID_LEFT_EXTRA_AFTER_SECOND_PASS: Wieder 15000 Zusatzschritte geradeaus
        if self.avoid_step == self.AVOID_LEFT_EXTRA_AFTER_SECOND_PASS:
            if self.avoid_extra_ms == 0:
                self.avoid_extra_ms = self.motors.steps_to_ms(
                    self.avoid_extra_steps,
                    self.avoid_speed
                )

            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_extra_ms:
                self.avoid_extra_ms = 0
                self._next_avoid_step()
            return

        # Schritt 8: 90 Grad nach rechts drehen, zurück Richtung Linie
        if self.avoid_step == self.AVOID_LEFT_TURN_TO_LINE:
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
        if self.avoid_step == self.AVOID_LEFT_SEARCH_LINE:
            self.motors.forward(self.avoid_speed)

            if self._line_found_during_avoidance():
                self.avoid_step = self.AVOID_LEFT_ALIGN_ON_LINE
                self.avoid_turn_90_ms = 0
                self.avoid_step_since_ms = time.ticks_ms()
                return

            if elapsed >= self.avoid_line_search_max_ms:
                self.motors.stop()
                self.set_state(self.STATE_AVOID_NOT_POSSIBLE)
            return

        # AVOID_LEFT_ALIGN_ON_LINE: 90 Grad nach links drehen, danach wieder Linienfolge
        if self.avoid_step == self.AVOID_LEFT_ALIGN_ON_LINE:
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

        fill_level = self._read_fuellstand_for_status()

        if self.touchpanel is not None:
            if fill_level is None:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="truck",
                    line_ok=True,
                )
            else:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="truck",
                    line_ok=True,
                    fill_level=fill_level,
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

        if self.turn_home_back_to_line:
            self.motors.backward(self.avoid_turn_speed)

            position = None
            if self.line_sensor is not None:
                position = self.line_sensor.get_position(force=True)

            self._debug_state(
                "Rueckwaerts bis Home-Marker erkannt Position: "
                + str(position)
                + " Elapsed ms: "
                + str(elapsed)
            )

            if position == "end_marker" or elapsed >= self.turn_home_back_timeout_ms:
                self.motors.stop()
                self.turn_home_180_ms = 0
                self.turn_home_back_to_line = False
                self.set_state(self.STATE_AT_HOME)
            return

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
            self.turn_home_back_to_line = True
            self.state_since_ms = time.ticks_ms()

    def _logic_turn_at_street(self):
        if self.motors is None:
            return

        if self.turn_street_180_ms == 0:
            self.turn_street_180_ms = self.motors.steps_to_ms(
                self.turn_home_180_steps,
                self.avoid_turn_speed
            )

        elapsed = time.ticks_diff(time.ticks_ms(), self.state_since_ms)

        self.motors.turn_right(self.avoid_turn_speed)

        self._debug_state(
            "180-Grad-Drehung an der Strasse Elapsed ms: "
            + str(elapsed)
            + " Zielzeit ms: "
            + str(self.turn_street_180_ms)
        )

        if elapsed >= self.turn_street_180_ms:
            self.motors.stop()
            self.turn_street_180_ms = 0
            self.set_state(self.STATE_LINE_FOLLOWING)

    def _logic_user_paused(self):
        if self.motors is not None:
            self.motors.stop()

        if self.buzzer is not None:
            self.buzzer.stop()

        self._debug_state("pausiert")
