# Verbindungsnotizen 2026-06-19

Dieses Dokument sammelt die Erkenntnisse aus der heutigen Netzwerk- und
Pico-/TP-Link-Debuggingrunde.

## Zielbild

Fuer die echte Tonne brauchen wir drei Verbindungen:

```text
Touchpanel/Pico -> lokale UI und Hardwaresteuerung
Pico -> Backend/WebApp fuer Status und Events
WebApp/Backend -> Pico fuer Befehle
```

Der Pico muss nicht am Router haengen. USB am Mac ist nur fuer Strom, Flashen
und Debugging. Die Netzwerkverbindung soll spaeter ueber WLAN laufen.

## Pico-Erkennung am Mac

Lokale Pruefung:

- Es tauchte kein typischer Pico-Port wie `/dev/cu.usbmodem...` auf.
- `system_profiler SPUSBDataType` zeigte keinen klaren Eintrag fuer Pico,
  Raspberry, RP2040, RPI-RP2 oder MicroPython.

Interpretation:

- Der Pico wurde in diesem Moment vom Mac nicht sauber als USB-Geraet erkannt.
- Das ist unabhaengig vom Router.
- Ein nur per USB verbundener Pico erscheint nicht in der Router-Geraeteliste.
  Er erscheint dort nur, wenn Pico-WLAN-Code laeuft und er sich aktiv ins WLAN
  einwaehlt.

Naechster Pico-Check:

1. Pico abziehen.
2. Mit gedrueckter `BOOTSEL`-Taste neu einstecken.
3. Erwartet: Laufwerk `RPI-RP2` oder ein erkennbarer USB-Eintrag.
4. Fuer MicroPython-Betrieb erwartet: `/dev/cu.usbmodem...`.
5. Falls nichts erscheint: anderes Datenkabel bzw. anderen Port testen.

## Vodafone-Router-Liste

Im Vodafone-Menue waren unter anderem sichtbar:

- `espresif` mit IP `192.168.0.95`
- mehrere `unknown`-Geraete
- Mac wahrscheinlich als `unknown` mit IP `192.168.0.213`

Erkenntnisse:

- `espresif` ist sehr wahrscheinlich ein ESP32/ESP8266, nicht der Pico.
- Die `unknown`-Eintraege koennen private/randomisierte MAC-Adressen von
  Mac/Handy/Laptop sein.
- Kein Eintrag war eindeutig als Pico W erkennbar.

## TP-Link TL-WR802N V4

Das Geraet wurde ohne Verpackung bzw. ohne Wi-Fi-Info-Karte verwendet.
Auf dem Geraet stand:

- Modell: `TL-WR802N V4`
- SSID nach Reset: `TP-Link_889A`
- `HVIN` ist nur eine Hardware-/Zulassungsangabe und kein Passwort.

### Ethernet am Mac

Der TP-Link/USB-LAN-Adapter erschien am Mac als:

- Hardware/Service: `AX88179B`
- Interface: `en12`
- MAC des Adapters: `6c:1f:f7:cc:18:9d`

Der physische Link war aktiv:

```text
status: active
media: 100baseTX full-duplex
```

Bei DHCP bekam der Mac zuerst nur:

```text
169.254.78.15
```

Das ist eine selbst zugewiesene Notfall-IP und bedeutet: kein DHCP vom TP-Link
erhalten.

Manuelle Tests:

- `192.168.0.10 / 255.255.255.0`, Router `192.168.0.254`
- Versuchte Admin-Adressen:
  - `http://192.168.0.254`
  - `http://192.168.0.1`
  - `http://192.168.1.1`
  - `http://tplinkwifi.net`

Ergebnis:

- Keine stabile Admin-Verbindung ueber Ethernet.
- Ping auf `192.168.0.254`, `192.168.0.1`, `192.168.1.1` und
  `192.168.1.254` blieb ohne Antwort.
- ARP auf `192.168.0.254` ueber `en12` blieb incomplete.

Wahrscheinliche Ursache:

- Beim TL-WR802N arbeitet der Ethernet-Port nach Reset im Default-Routermodus
  vermutlich als WAN-Port.
- Der initiale Admin-Zugang ist deshalb eher ueber das Default-WLAN als ueber
  Ethernet vorgesehen.

### WLAN nach Reset

Nach Reset war `TP-Link_889A` sichtbar. Beim Verbinden wurde ein WPA2-Passwort
verlangt.

Problem:

- Auf dem Geraet war kein klarer `Wireless Password`, `PIN`, `Wi-Fi Password`
  oder `Network Key` sichtbar.
- Ohne Verpackung/Wi-Fi-Karte fehlt vermutlich genau dieser Default-Key.

Moegliche naechste Schritte:

- Herr Hellweg nach Wi-Fi-Info-Karte oder bekanntem Default-Passwort fragen.
- Falls Key rekonstruierbar: mit `TP-Link_889A` verbinden und dann
  `tplinkwifi.net`, `192.168.0.1` oder `192.168.0.254` testen.
- Alternativ TP-Link nicht weiter verwenden und direkt ueber anderes WLAN
  testen.

## Mac-Netzwerkprioritaet

Es gab eine wichtige macOS-Erkenntnis:

- Wenn USB/Ethernet-Dienste ueber Wi-Fi priorisiert sind, kann beim Einstecken
  des TP-Link das Internet ausfallen.
- Die Default-Route sollte fuer normales Arbeiten ueber Wi-Fi laufen.

Empfehlung:

```text
Systemeinstellungen -> Netzwerk -> Dienstreihenfolge
Wi-Fi ganz nach oben
USB/Ethernet darunter
```

Fuer direkte TP-Link-Admin-Tests kann Wi-Fi kurz deaktiviert werden, damit
`192.168.0.1` nicht beim Vodafone-Router landet.

## Brauchen wir TP-Link zwingend?

Nein. Der TP-Link ist nur ein moegliches Test-WLAN.

Alternativen:

- Pico W direkt ins Vodafone-2.4-GHz-WLAN.
- Pico W in einen Handy-Hotspot.
- Pico W spaeter ins FH-WLAN, wenn dieses einfache WPA2-Zugangsdaten erlaubt.
- Wenn FH-WLAN Enterprise oder Captive Portal nutzt, braucht der Pico sehr
  wahrscheinlich einen eigenen Access Point/Hotspot oder einen anderen
  Vermittlungsweg.

## Backend-Anbindung fuer echte Funktionen

Der bestehende Backend-Andockpunkt fuer echte Pico-Befehle ist bereits vorhanden:

- `POST /bins/{bin_id}/command`
- `GET /bins/{bin_id}/pending-command`
- `POST /bins/{bin_id}/ack`

Der Pico kann fuer den ersten echten Stand alle 1-2 Sekunden pollen:

```text
GET /bins/{id}/pending-command
```

und danach per ACK quittieren:

```text
POST /bins/{id}/ack
```

Das ist fuer MicroPython einfacher und robuster als sofort WebSocket/MQTT.

## Empfohlene Reihenfolge ab morgen

1. Pico lokal per USB wieder erkennbar machen.
2. Touchpanel-Code erneut flashen und seriell debuggen.
3. WLAN-Weg festlegen:
   - Vodafone 2.4 GHz,
   - Handy-Hotspot,
   - oder TP-Link, falls Zugangsdaten geklaert.
4. Pico mit Test-WLAN verbinden und IP seriell ausgeben.
5. Backend/API-Adresse im Pico setzen, z.B. aktuelle Mac-IP plus Port 8000.
6. Ersten End-to-End-Test:
   - Touchpanel: Hygienemeldung oder Schadensmeldung ausloesen.
   - Pico sendet Event ans Backend.
   - WebApp zeigt Meldung im Operator-Panel.
   - Pico zeigt Bestaetigungsscreen.
7. Danach Commands:
   - WebApp legt Command an.
   - Pico pollt Command.
   - Pico quittiert.
   - WebApp zeigt neuen Zustand.

## Minimaler Event-Vertrag fuer Touchpanel -> WebApp

Fuer die erste Integration reichen diese Events:

```text
damage_report
hygiene_report
lock
unlock
lid_open
lid_close
goto_pickup
return_home
eco_mode
power_off
```

Der wichtigste erste echte Test ist eine Meldung, weil sie ohne Motorikrisiko
sichtbar in der WebApp ankommt.
