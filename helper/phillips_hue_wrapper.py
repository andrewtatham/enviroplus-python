import pprint
import random
import time
from itertools import cycle

from phue import Bridge

from helper import colour_helper


class HueWrapper(object):
    def __init__(self, bridge_ip='192.168.1.73', light_configs=None, profiles=None):
        if not light_configs:
            light_configs = [
                {'name': 'Hue color spot 1', 'is_colour': True},
                {'name': 'Hue color spot 2', 'is_colour': True},
                {'name': 'Hue color spot 3', 'is_colour': True},
                {'name': 'DEATH STAR', 'is_colour': True},
                {'name': 'Right Colour Strip', 'is_colour': True},
                {'name': 'Right White Strip', 'is_colour': False},
                {'name': 'Left Colour Strip', 'is_colour': True},
                {'name': 'Left White Strip', 'is_colour': False},
            ]
        if not profiles:
            normal_mode = {
                'name': 'normal',
                'profile_state': {},
                'lights': {
                    'Hue color spot 1': {'is_on': False, 'light_state': {}, 'func': None},
                    'Hue color spot 2': {'is_on': False, 'light_state': {}, 'func': None},
                    'Hue color spot 3': {'is_on': False, 'light_state': {}, 'func': None},
                    'DEATH STAR': {'is_on': False, 'light_state': {}, 'func': None},
                    'Right Colour Strip': {'is_on': False, 'light_state': {}, 'func': None},
                    'Right White Strip': {'is_on': True, 'light_state': {}, 'func': self._normal_func},
                    'Left Colour Strip': {'is_on': False, 'light_state': {}, 'func': None},
                    'Left White Strip': {'is_on': True, 'light_state': {}, 'func': self._normal_func},
                }
            }
            colour_mode = {
                'name': 'colour',
                'profile_state': {},
                'lights': {
                    'Hue color spot 1': {'is_on': True, 'light_state': {}, 'func': self._colour_func},
                    'Hue color spot 2': {'is_on': True, 'light_state': {}, 'func': self._colour_func},
                    'Hue color spot 3': {'is_on': True, 'light_state': {}, 'func': self._colour_func},
                    'DEATH STAR': {'is_on': True, 'light_state': {}, 'func': self._colour_func},
                    'Right Colour Strip': {'is_on': True, 'light_state': {}, 'func': self._colour_func},
                    'Right White Strip': {'is_on': False, 'light_state': {}, 'func': None},
                    'Left Colour Strip': {'is_on': True, 'light_state': {}, 'func': self._colour_func},
                    'Left White Strip': {'is_on': False, 'light_state': {}, 'func': None},
                }
            }
            profiles = [
                normal_mode,
                # colour_mode,
            ]

        self.light_configs = light_configs
        self.profiles = cycle(profiles)
        self.profile = next(self.profiles)
        self.bridge_ip = bridge_ip
        self.b = None
        self.lights = []

    def connect(self):
        self.b = Bridge(self.bridge_ip)
        self.b.connect()
        pprint.pprint(self.b.get_api())
        for actual_light in self.b.lights:
            name = actual_light.name
            for light_config in self.light_configs:
                if light_config['name'] == name:
                    name += " *"
                    actual_light.is_colour = light_config['is_colour']
                    self.lights.append(actual_light)
            print(name)
        if self.lights:
            print("connected")
            for actual_light in self.lights:
                pprint.pprint(actual_light.__dict__)

    def on(self):
        for light in self.lights:
            light.on = True

    def colour_temperature(self, temp):
        # (white only) 154 is the coolest, 500 is the warmest
        for light in self.lights:
            light.colortemp = temp

    def xy(self, x, y):
        #  co-ordinates in CIE 1931 space
        for light in self.lights:
            if light.is_colour:
                light.xy = (x, y)

    def random_colour(self):
        for light in self.lights:
            if light.is_colour:
                light.xy = [random.random(), random.random()]

    def hue(self, hue, sat=254):
        # hue' parameter has the range 0-65535 so represents approximately 182*degrees
        # sat is 0-254?
        for light in self.lights:
            light.hue = hue
            light.saturation = sat

    def brightness(self, bright):
        # // brightness between 0-254 (NB 0 is not off!)
        for light in self.lights:
            light.bri = bright

    def colour_loop_off(self):
        for light in self.lights:
            if light.is_colour:
                light.effect = "none"

    def colour_loop_on(self):
        for light in self.lights:
            if light.is_colour:
                light.effect = "colorloop"

    def flash_once(self):
        for light in self.lights:
            light.alert = "select"

    def flash_multiple(self):
        for light in self.lights:
            light.alert = "lselect"

    def flash_off(self):
        for light in self.lights:
            light.alert = None

    def off(self):
        for light in self.lights:
            light.on = False

    @property
    def is_on(self):
        on = False
        for light in self.lights:
            on = on or light.on
        return on

    @property
    def is_off(self):
        return not self.is_on

    def set_hsv(self, h, s, v):
        h = int(h * 65535)
        s = int(s * 255)
        v = int(v * 255)
        print((h, s, v))
        for light in self.lights:
            if light.is_colour:
                light.hue = h
                light.sat = s
                light.bri = v

    def quick_transitions(self):
        for light in self.lights:
            light.transitiontime = 0

    def sleep(self, seconds):
        time.sleep(seconds)

    def next_profile(self):
        self.profile = next(self.profiles)

    def do_whatever(self):
        if self.is_on:
            for light in self.lights:
                light_profile = self.profile['lights'][light.name]
                profile_state = self.profile['profile_state']
                if light_profile:
                    if light_profile['is_on'] != light.on:
                        light.on = light_profile['is_on']
                    light_func = light_profile['func']
                    light_state = light_profile['light_state']
                    if light_func:
                        light_func(light=light, light_state=light_state, profile_state=profile_state)

    def _normal_func(self, light, **kwargs):
        # (white only) 154 is the coolest, 500 is the warmest
        ct = 500 + int(colour_helper.day_factor * (154 - 500))
        # // brightness between 0-254 (NB 0 is not off!)
        brightness = int(colour_helper.day_factor * 254)

        light.colortemp = ct
        light.brightness = brightness
        pass

    def _colour_func(self, light, **kwargs):
        # hue' parameter has the range 0-65535 so represents approximately 182*degrees
        hue = int(colour_helper.day_factor * 65535)
        sat = 254
        # // brightness between 0-254 (NB 0 is not off!)
        brightness = int(colour_helper.day_factor * 254)
        light.hue = hue
        light.saturation = sat
        light.brightness = brightness


if __name__ == '__main__':
    hue = HueWrapper()
    hue.connect()

    hue.on()
    hue.brightness(254)

    hue.colour_temperature(154)
    hue.sleep(5)
    hue.colour_temperature(500)
    hue.sleep(5)
    hue.colour_temperature(154)
    hue.sleep(5)

    # for _ in range(5):
    #     hue.random_colour()
    #     hue.sleep(1)
    #
    # hue.colour_loop_on()
    # hue.sleep(10)
    # hue.colour_loop_off()
    # hue.sleep(10)
    hue.off()
