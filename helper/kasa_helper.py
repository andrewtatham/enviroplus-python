import pyHS100


class KasaWrapper:
    def __init__(self):
        self.heater_is_on = False

    def manage_heater(self, temperature):

        switch_off = self.heater_is_on and temperature > 18.0
        switch_on = not self.heater_is_on and temperature < 17.5

        if switch_on or switch_off:
            heater = self.get_device('Heater')
            if heater:

                if switch_on:
                    heater.turn_on()
                    self.heater_is_on = True
                if switch_off:
                    heater.turn_off()
                    self.heater_is_on = False

    def get_device(self, device_name):
        for dev in pyHS100.Discover.discover().values():
            name = dev.alias
            print(name)
            if name == device_name:
                return dev
