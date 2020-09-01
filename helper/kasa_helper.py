import pyHS100


class KasaWrapper:
    def __init__(self):
        self.heater_is_on = False

    def get_device(self, device_name):
        for dev in pyHS100.Discover.discover().values():
            name = dev.alias
            print(name)
            if name == device_name:
                return dev

    def switch_off(self):
        if self.heater_is_on:
            heater = self.get_device('Heater')
            if heater:
                heater.turn_off()
                self.heater_is_on = False

    def switch_on(self):
        if not self.heater_is_on:
            heater = self.get_device('Heater')
            if heater:
                heater.turn_on()
                self.heater_is_on = True
