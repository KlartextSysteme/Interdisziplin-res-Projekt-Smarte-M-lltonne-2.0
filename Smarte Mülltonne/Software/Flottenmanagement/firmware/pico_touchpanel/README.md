# Pico Touchpanel Firmware

MicroPython firmware draft for the smart-bin touch display.

## Hardware

- Raspberry Pi Pico W
- ILI9341 2.8 inch SPI display
- Target UI: landscape `320 x 240`

Known working display wiring from the first hardware test:

| Signal | Pico GPIO |
|---|---:|
| SCK | GP18 |
| MOSI | GP19 |
| CS | GP17 |
| DC | GP20 |
| RST | GP21 |

## Files

- `main.py` starts the UI.
- `display.py` contains the minimal ILI9341 drawing driver.
- `ui.py` contains the screen state machine and wireframe implementation.
- `config.py` contains pins, display rotation and backend placeholders.

## First Test

Copy all `.py` files to the Pico W and run `main.py`.

If the UI is rotated or mirrored, change `DISPLAY_ROTATION` in `config.py`.
Likely values to try: `0x28`, `0x48`, `0x88`, `0xE8`.

Touch is not connected yet in this draft. For a first screen test, call
`ui.handle_touch(x, y)` from the REPL after `main.py` has drawn the UI.
