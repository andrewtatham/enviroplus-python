import logging

import pyHS100


class KasaWrapper:
    def __init__(self):
        self.heater_is_on = False

    def get_device(self, device_name):
        devices = pyHS100.Discover.discover().values()
        for dev in devices:
            if dev.alias == device_name:
                return dev
        logging.info('Could not find {}'.format(device_name))
        for dev in devices:
            logging.info(dev.alias)

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
