#!/usr/bin/env python3

import time
import colorsys
import os
import sys
from statistics import mean

import ST7735

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559

    ltr559 = LTR559()
except ImportError:
    import ltr559

from bme280 import BME280
from subprocess import PIPE, Popen
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from fonts.ttf import RobotoMedium as UserFont
import logging


class EnviroWrapper:
    def __init__(self):

        # BME280 temperature/pressure/humidity sensor
        self.bme280 = BME280()

        # Create ST7735 LCD display class
        self.st7735 = ST7735.ST7735(
            port=0,
            cs=1,
            dc=9,
            backlight=12,
            rotation=270,
            spi_speed_hz=10000000
        )

        # Initialize display
        self.st7735.begin()

        self.WIDTH = self.st7735.width
        self.HEIGHT = self.st7735.height

        # Set up canvas and font
        self.img = Image.new('RGB', (self.WIDTH, self.HEIGHT), color=(0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.font_size = 20
        self.font = ImageFont.truetype(UserFont, self.font_size)

        self.message = ""

        # The position of the top bar
        self.top_pos = 25

        # Tuning factor for compensation. Decrease this number to adjust the
        # displayed temperature down, and increase to adjust up
        self.factor = 1.2

        # Create a values dict to store the data
        self.variables = ["temperature",
                          "light"]

        self.values = {}
        for v in self.variables:
            self.values[v] = [1] * self.WIDTH

        self.cpu_temps = [get_cpu_temperature()] * 5

    # Displays data and text on the 0.96" LCD
    def display_text(self, variable, data, unit):
        # Maintain length of list
        self.values[variable] = self.values[variable][1:] + [data]
        # Scale the values for the variable between 0 and 1
        vmin = min(self.values[variable])
        vmax = max(self.values[variable])
        colours = [(v - vmin + 1) / (vmax - vmin + 1) for v in self.values[variable]]
        # Format the variable name and value
        self.message = "{}: {:.1f} {}".format(variable[:4], data, unit)
        logging.info(self.message)
        self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), (255, 255, 255))
        for i in range(len(colours)):
            # Convert the values to colours from red to blue
            colour = (1.0 - colours[i]) * 0.6
            r, g, b = [int(x * 255.0) for x in colorsys.hsv_to_rgb(colour, 1.0, 1.0)]
            # Draw a 1-pixel wide rectangle of colour
            self.draw.rectangle((i, self.top_pos, i + 1, self.HEIGHT), (r, g, b))
            # Draw a line graph in black
            line_y = self.HEIGHT - (self.top_pos + (colours[i] * (self.HEIGHT - self.top_pos))) + self.top_pos
            self.draw.rectangle((i, line_y, i + 1, line_y + 1), (0, 0, 0))
        # Write the text at the top in black
        self.draw.text((0, 0), self.message, font=self.font, fill=(0, 0, 0))
        self.st7735.display(self.img)

    def get_lux(self):
        unit = "Lux"
        data = ltr559.get_lux()
        self.display_text("light", data, unit)
        return data

    def get_temperature(self):
        # variable = "temperature"
        unit = "C"
        cpu_temp = get_cpu_temperature()
        # Smooth out with some averaging to decrease jitter
        cpu_temps = self.cpu_temps[1:] + [cpu_temp]
        avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
        raw_temp = self.bme280.get_temperature()
        cpu_adjustment = - ((avg_cpu_temp - raw_temp) / self.factor)
        data = raw_temp + cpu_adjustment
        self.display_text("temperature", data, unit)
        message = "raw: {: .1f} cpu: {: .1f} adjustment: {: .1f} calc: {: .1f} ".format(raw_temp,
                                                                                        avg_cpu_temp,
                                                                                        cpu_adjustment,
                                                                                        data)
        logging.info(message)
        return data


def get_cpu_temperature():
    # Get the temperature of the CPU for compensation
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
    output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])
