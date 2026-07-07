from machine import ADC, Pin

# Referenzspannung des ADC beim Raspberry Pi Pico
ADC_REF_VOLTAGE = 3.3
ADC_MAX_VALUE = 65535

class Akkustandsueberwachung:
    """
    Misst die Akkuspannung ueber einen Spannungsteiler und rechnet sie linear
    in einen Akkustand von 0 bis 100 Prozent um.
    """

    def __init__(
        self,
        adc_pin,
        r1_ohm,
        r2_ohm,
        min_voltage,
        max_voltage,
        adc_ref_voltage=ADC_REF_VOLTAGE,
        adc_max_value=ADC_MAX_VALUE,
    ):
        self.adc = ADC(Pin(adc_pin))
        self.r1_ohm = r1_ohm
        self.r2_ohm = r2_ohm
        self.min_voltage = min_voltage
        self.max_voltage = max_voltage
        self.adc_ref_voltage = adc_ref_voltage
        self.adc_max_value = adc_max_value
        self.divider_factor = (self.r1_ohm + self.r2_ohm) / self.r2_ohm

    def _clamp(self, value, low, high):
        if value < low:
            return low
        if value > high:
            return high
        return value

    def read_adc_raw(self):
        return self.adc.read_u16()

    def read_adc_voltage(self):
        raw = self.read_adc_raw()
        voltage_adc = raw * self.adc_ref_voltage / self.adc_max_value
        return raw, voltage_adc

    def read_battery_voltage(self):
        raw, voltage_adc = self.read_adc_voltage()
        voltage_battery = voltage_adc * self.divider_factor
        return raw, voltage_adc, voltage_battery

    def voltage_to_percent(self, voltage_battery):
        span = self.max_voltage - self.min_voltage
        if span <= 0:
            return 0

        percent = (voltage_battery - self.min_voltage) * 100 / span
        return int(round(self._clamp(percent, 0, 100)))

    def read_percent(self):
        _raw, _voltage_adc, voltage_battery = self.read_battery_voltage()
        return self.voltage_to_percent(voltage_battery)

    def read_status(self):
        raw, voltage_adc, voltage_battery = self.read_battery_voltage()
        return {
            "raw": raw,
            "adc_voltage": voltage_adc,
            "battery_voltage": voltage_battery,
            "battery_percent": self.voltage_to_percent(voltage_battery),
        }
