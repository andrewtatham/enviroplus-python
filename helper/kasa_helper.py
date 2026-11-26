import logging

import pyHS100


class KasaWrapper:
    def get_device(self, device_name):
        devices = pyHS100.Discover.discover().values()
        for dev in devices:
            if dev.alias == device_name:
                return dev
        logging.info('Could not find {}'.format(device_name))
        for dev in devices:
            logging.info(dev.alias)

    def is_on(self):
        heater = self.get_device('Heater')
        if heater:
            return heater.is_on
        return False

    def switch_off(self):
        """Return False if the heater could not be found."""
        heater = self.get_device('Heater')
        if heater:
            heater.turn_off()
            return True
        return False

    def switch_on(self):
        heater = self.get_device('Heater')
        if heater:
            heater.turn_on()
