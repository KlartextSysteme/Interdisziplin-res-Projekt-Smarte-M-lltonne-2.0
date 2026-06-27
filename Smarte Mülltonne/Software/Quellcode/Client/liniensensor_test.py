"""
Standalone-Test fuer das Liniensensor-Array (OHNE Motoren).

Zweck: Vorzeichen-Kette der Linienverfolgung aufgebockt pruefen.
Es werden NUR der Multiplexer und der Liniensensor benutzt, keine
Stepper, keine Netzwerk-Logik. Damit laesst sich gefahrlos pruefen,
ob die Sensor-Reihenfolge und die Position zur Hardware passen.

Bedienung:
- Datei auf den Pico laden und ausfuehren (z.B. ueber Thonny).
- Schwarzen Linienstreifen unter das Array halten und nach
  LINKS / MITTE / RECHTS schieben.
- Im Log pruefen, ob Position und die "Wuerde-fahren"-Anzeige
  zur Streifenposition passen (siehe Erwartung unten).

Erwartung (Code-Konvention, weights=(2,1,0,-1,-2), C0..C4 rechts->links):
- Streifen RECHTS  -> Position POSITIV  -> Tonne wuerde nach RECHTS lenken
                      (rechte Kette schneller)
- Streifen MITTE   -> Position ~ 0       -> geradeaus
- Streifen LINKS   -> Position NEGATIV   -> Tonne wuerde nach LINKS lenken
                      (linke Kette schneller)

Stimmt das NICHT mit der echten Streifenposition ueberein, ist die
Sensor-Reihenfolge andersrum verdrahtet -> weights umdrehen auf
(-2,-1,0,1,2) in main.py.
"""

from time import sleep_ms

from liniensensor import Liniensensor
from multiplexer import Multiplexer
from PDcontroller import PDController

# Gleiche Pins wie in main.py
MUX_S0_PIN = 2
MUX_S1_PIN = 3
MUX_S2_PIN = 4
MUX_S3_PIN = 5
MUX_SIGNAL_PIN = 28

# Gleiche Fahr-Parameter wie der echte Controller, nur zur Anzeige
BASE_SPEED = 45
MIN_SPEED = 0
MAX_SPEED = 95


def side_label(position):
    if position is None:
        return "KEINE LINIE"
    if position == "street":
        return "STRASSE (alle 5)"
    if position > 0.2:
        return "Linie RECHTS"
    if position < -0.2:
        return "Linie LINKS"
    return "Linie MITTE"


def steer_label(left_speed, right_speed):
    if right_speed > left_speed + 1:
        return "wuerde nach RECHTS lenken (rechte Kette schneller)"
    if left_speed > right_speed + 1:
        return "wuerde nach LINKS lenken (linke Kette schneller)"
    return "wuerde GERADEAUS fahren"


def main():
    mux = Multiplexer(
        s0_pin=MUX_S0_PIN,
        s1_pin=MUX_S1_PIN,
        s2_pin=MUX_S2_PIN,
        s3_pin=MUX_S3_PIN,
        signal_pin=MUX_SIGNAL_PIN,
    )

    line_sensor = Liniensensor(
        multiplexer=mux,
        channels=(0, 1, 2, 3, 4),
        weights=(2, 1, 0, -1, -2),
        line_detected_value=1,
        samples_per_read=1,
        sample_delay_us=0,
        read_delay_us=300,
    )

    pd = PDController()

    print("Liniensensor-Test gestartet. Motoren sind AUS.")
    print("Streifen unter das Array halten und LINKS/MITTE/RECHTS schieben.")
    print("Spaltenkopf: [C0 C1 C2 C3 C4]  C0 = rechts, C4 = links")
    print("-" * 60)

    while True:
        values = line_sensor.read_values(force=True)
        position = line_sensor.get_position()

        # Was der echte Regler aus dieser Position machen wuerde:
        left_speed, right_speed, correction = pd.get_motor_speeds(
            current_position=position,
            base_speed=BASE_SPEED,
            min_speed=MIN_SPEED,
            max_speed=MAX_SPEED,
        )

        print(
            "Sensoren " + str(values)
            + " | Position: " + str(position)
            + " | " + side_label(position)
            + " | Korrektur: " + str(round(correction, 1))
            + " | L/R: " + str(round(left_speed, 1)) + "/" + str(round(right_speed, 1))
            + " | " + steer_label(left_speed, right_speed)
        )

        sleep_ms(200)


if __name__ == "__main__":
    main()
