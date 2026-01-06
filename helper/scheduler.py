import itertools

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from astral import Astral

from helper import colour_helper
from helper.enviro_helper import EnviroWrapper
from helper.kasa_helper import KasaWrapper
from helper.phillips_hue_wrapper import HueWrapper
import colorsys
import datetime
import logging
import platform
import pprint
import time

import colour
import pytz

at_midnight = CronTrigger(hour=0)
on_the_hour = CronTrigger(minute=0)
on_the_minute = CronTrigger(minute="1-59", second=0)
every_second = CronTrigger(second="*")
before_morning = CronTrigger(hour=5, minute=59)
at_morning = CronTrigger(hour=6)
at_bedtime = CronTrigger(hour=23)
every_fifteen_minutes = CronTrigger(minute="*/15")
every_five_minutes = CronTrigger(minute="*/5")
every_even_minute = CronTrigger(minute="*/2")
every_odd_minute = CronTrigger(minute="1-59/2")
every_minute = CronTrigger(minute="*")
every_thirty_seconds = CronTrigger(second="*/30")
every_fifteen_seconds = CronTrigger(second="*/15")

heater_trigger = every_minute
lights_trigger = every_minute

tz = pytz.timezone("Europe/London")
is_linux = platform.platform().startswith('Linux')


def _get_cron_trigger_for_datetime(dt):
    return CronTrigger(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute, second=dt.second)


class MuteFilter(object):
    def filter(self, record):
        return False


class MyScheduler:
    def __init__(self):
        self._scheduler = BlockingScheduler()
        self._hue = HueWrapper()
        self._enviro = EnviroWrapper()
        self._kasa = KasaWrapper()
        self._bright = 0
        self._init()

        self.heater_on_for = 0
        self.heater_off_for = 0

        self.switch_on = False

    def _init(self):
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("apscheduler.scheduler").addFilter(MuteFilter())

        self._hue.connect()

        self._scheduler.add_job(func=self._get_sunset_sunrise, trigger=at_midnight)
        self._scheduler.add_job(func=self._get_sunset_sunrise)

        self._scheduler.add_job(self._manage_heater)
        self._scheduler.add_job(self._manage_lights)
        self._scheduler.add_job(self._manage_heater, trigger=heater_trigger)
        self._scheduler.add_job(self._manage_lights, trigger=lights_trigger)

    def start(self):
        self._scheduler.print_jobs()
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown()
        # if self._hue:
        #     self._hue.off()

    def _manage_lights(self):
        if self._hue.is_on:
            self._hue.do_whatever()

    def _manage_heater(self):
        now = datetime.datetime.now()
        weekday = now.weekday()
        hour = now.hour
        mins = now.minute
        month = now.month

        logging.info('month: {}'.format(month))
        logging.info('weekday: {}'.format(weekday))
        logging.info('hour: {}'.format(hour))
        logging.info('mins: {}'.format(mins))

        monday = 0
        tuesday = 1
        wednesday = 2
        thursday = 3
        friday = 4

        is_monday_or_tuesday = weekday == monday or weekday == tuesday

        holiday_from = datetime.datetime(year=2025, month=12, day=19, hour=17, minute=00)
        holiday_to = datetime.datetime(year=2026, month=1, day=5, hour=8, minute=00)
        on_holiday = holiday_from < now < holiday_to
        logging.info('on_holiday: {}'.format(on_holiday))

        is_spring = 3 <= month <= 5
        is_summer = 6 <= month <= 8
        is_autumn = 9 <= month <= 10
        is_winter = month >= 11 or month <= 2

        logging.info('is_spring: {}'.format(is_spring))
        logging.info('is_summer: {}'.format(is_summer))
        logging.info('is_autumn: {}'.format(is_autumn))
        logging.info('is_winter: {}'.format(is_winter))

        # Mon to Fri 8:00 to 16:45
        # in mon/tue 7:00

        in_work_hours = not on_holiday \
                        and monday <= weekday <= friday \
                        and (8 <= hour or is_monday_or_tuesday and hour == 7) \
                        and (hour < 16 or hour == 16 and mins <= 45)

        is_morning = 0 <= hour <= 12
        is_early_morning = 0 <= hour <= 10

        logging.info('weekday: {} hour: {}'.format(weekday, hour))
        logging.info('in_work_hours: {}'.format(in_work_hours))

        temperature = self._enviro.get_temperature()
        logging.info('temperature: {}'.format(temperature))

        duty_cycle = 10
        if is_spring:
            duty_cycle = 20

        if is_spring:
            on_below = 18.0
            off_above = 20.0
        elif is_summer:
            on_below = 10.0
            off_above = 15.0
        elif is_autumn:
            on_below = 17.0
            off_above = 20.0
        elif is_winter:
            on_below = 22.0
            off_above = 24.0
        else:
            on_below = 10.0
            off_above = 15.0

        if is_winter:
            if is_early_morning:
                off_above += 1
            if is_morning:
                off_above += 1

        logging.info('on_below: {}'.format(on_below))
        logging.info('off_above: {}'.format(off_above))

        is_on = self._kasa.is_on()
        logging.info('is_on: {0}'.format(is_on))
        if is_on:
            self.heater_on_for += 1
            self.heater_off_for = 0
        else:
            self.heater_on_for = 0
            self.heater_off_for += 1

        logging.info('heater_on_for: {0}'.format(self.heater_on_for))
        logging.info('heater_off_for: {0}'.format(self.heater_off_for))

        cooler_thx = temperature > off_above or (in_work_hours and self.heater_on_for > duty_cycle)
        warmer_plz = in_work_hours and temperature < on_below

        if cooler_thx:
            logging.info('cooler_thx')
            self.switch_on = False
        elif warmer_plz:
            logging.info('warmer_plz')
            if self.heater_off_for > 1:
                logging.info('Duty cycle on')
                self.switch_on = True

        logging.info('switch_on: {0}'.format(self.switch_on))

        if self.switch_on:
            logging.info('Switching heater on')
            self._kasa.switch_on()
        elif cooler_thx:
            logging.info('Switching heater off')
            self._kasa.switch_off()

    def _get_sunset_sunrise(self):
        a = Astral()
        leeds = a['Leeds']
        today = datetime.date.today()
        self._today_sun_data = leeds.sun(date=today, local=True)
        self.timezone = leeds.timezone
        logging.info(pprint.pformat(self._today_sun_data))

        self.dawn = self._today_sun_data['dawn']
        self.sunrise = self._today_sun_data['sunrise']
        self.sunset = self._today_sun_data['sunset']
        self.dusk = self._today_sun_data['dusk']

        at_dawn = _get_cron_trigger_for_datetime(self.dawn)
        at_sunrise = _get_cron_trigger_for_datetime(self.sunrise)
        at_sunset = _get_cron_trigger_for_datetime(self.sunset)
        at_dusk = _get_cron_trigger_for_datetime(self.dusk)

        during_sunrise = IntervalTrigger(seconds=5, start_date=self.dawn, end_date=self.sunrise)
        during_sunset = IntervalTrigger(seconds=5, start_date=self.sunset, end_date=self.dusk)

        self._scheduler.add_job(func=self._at_dawn, trigger=at_dawn)
        self._scheduler.add_job(func=self._during_sunrise, trigger=during_sunrise)
        self._scheduler.add_job(func=self._at_sunrise, trigger=at_sunrise)

        self._scheduler.add_job(func=self._at_sunset, trigger=at_sunset)
        self._scheduler.add_job(func=self._during_sunset, trigger=during_sunset)
        self._scheduler.add_job(func=self._at_dusk, trigger=at_dusk)

        now = datetime.datetime.now(tz)
        if now <= self.dawn:
            day_factor = 0.0
        elif self.dawn < now <= self.sunrise:
            day_factor = colour_helper.get_day_factor(self.dawn, now, self.sunrise, True)
        elif self.sunrise < now <= self.sunset:
            day_factor = 1.0
        elif self.sunset < now <= self.dusk:
            day_factor = colour_helper.get_day_factor(self.sunset, now, self.dusk, False)
        elif now < self.dusk:
            day_factor = 0.0
        else:
            day_factor = 0.25

        self._set_day_factor(day_factor)

    def _at_dawn(self):
        day_factor = 0.0
        self._set_day_factor(day_factor)
        logging.info('dawn')

    def _at_sunrise(self):
        day_factor = 1.0
        self._set_day_factor(day_factor)
        logging.info('sunrise')

    def _at_sunset(self):
        day_factor = 1.0
        self._set_day_factor(day_factor)
        logging.info('sunset')

    def _at_dusk(self):
        day_factor = 0.0
        self._set_day_factor(day_factor)
        logging.info('dusk')

    def _during_sunrise(self):
        day_factor = colour_helper.get_day_factor(self.dawn, datetime.datetime.now(tz), self.sunrise, True)
        self._set_day_factor(day_factor)

    def _during_sunset(self):
        day_factor = colour_helper.get_day_factor(self.sunset, datetime.datetime.now(tz), self.dusk, False)
        self._set_day_factor(day_factor)

    def _set_day_factor(self, day_factor):
        logging.info('day factor: {}'.format(day_factor))
        colour_helper.set_day_factor(day_factor)
