from machine import ADC, Pin
from time import sleep


# Spannungsteiler an GP27 / ADC1
BATTERY_ADC_PIN = 27

# Widerstandswerte des Spannungsteilers in Ohm anpassen:
# Batterie-Plus -> R1 -> GP27 -> R2 -> GND
R1_OHM = 100000
R2_OHM = 33000

# Referenzspannung des ADC beim Raspberry Pi Pico
ADC_REF_VOLTAGE = 3.3
ADC_MAX_VALUE = 65535


adc_battery = ADC(Pin(BATTERY_ADC_PIN))


def read_adc_raw():
    return adc_battery.read_u16()


def read_adc_voltage():
    raw = read_adc_raw()
    voltage_adc = raw * ADC_REF_VOLTAGE / ADC_MAX_VALUE
    return raw, voltage_adc


def read_battery_voltage():
    raw, voltage_adc = read_adc_voltage()
    divider_factor = (R1_OHM + R2_OHM) / R2_OHM
    voltage_battery = voltage_adc * divider_factor
    return raw, voltage_adc, voltage_battery


print("Starte Batterie-ADC-Test an GP27...")
print("R1:", R1_OHM, "Ohm")
print("R2:", R2_OHM, "Ohm")
print("-------------------")

while True:
    adc_raw, adc_voltage, battery_voltage = read_battery_voltage()

    print("ADC-Rohwert:", adc_raw)
    print("Spannung an GP27:", round(adc_voltage, 3), "V")
    print("Batteriespannung:", round(battery_voltage, 3), "V")
    print("-------------------")

    sleep(1)


#ADC-Rohwert: 38569
#Spannung an GP27: 1.942 V
#Batteriespannung: 7.827 V