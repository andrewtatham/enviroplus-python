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

tz = pytz.timezone("Europe/London")
is_linux = platform.platform().startswith('Linux')


def _get_cron_trigger_for_datetime(dt):
    return CronTrigger(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute, second=dt.second)


class MuteFilter(object):
    def filter(self, record):
        return False


def get_target_lux():
    now = datetime.datetime.now(tz)
    if now.hour <= 6:
        return 1
    elif now.hour <= 17:
        return 400
    elif now.hour <= 20:
        return 25
    else:
        return 1


class MyScheduler:
    def __init__(self):
        self._scheduler = BlockingScheduler()
        self._hue = HueWrapper()
        self._enviro = EnviroWrapper()
        self._kasa = KasaWrapper()
        self._bright = 0
        self._init()
        self._jobs_list = [
            self._manage_heater,
            self._manage_lights,
        ]
        self._jobs_cycle = itertools.cycle(self._jobs_list)

    def _init(self):
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("apscheduler.scheduler").addFilter(MuteFilter())

        self._hue.connect()

        self._scheduler.add_job(func=self._get_sunset_sunrise, trigger=at_midnight)
        self._scheduler.add_job(func=self._get_sunset_sunrise)

        self._scheduler.add_job(self._manage_next, trigger=every_thirty_seconds)
        self._scheduler.add_job(self._manage_all)

    def start(self):
        self._scheduler.print_jobs()
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown()
        # if self._hue:
        #     self._hue.off()

    def _manage_all(self):
        for job in self._jobs_list:
            job()
            time.sleep(5)

    def _manage_next(self):
        job = next(self._jobs_cycle)
        job()

    def _manage_lights(self):
        actual_lux = self._enviro.get_lux()
        logging.info('light: {}'.format(actual_lux))
        if self._hue.is_on:
            target_lux = get_target_lux()
            lux_delta = target_lux - actual_lux
            lux_delta = max(-128, min(lux_delta, 128))
            self._bright = self._bright + lux_delta
            self._bright = max(0, min(self._bright, 254))
            logging.info('target: {} actual: {} delta: {} brightness: {}'.format(
                target_lux, actual_lux, lux_delta, self._bright))
            # if self._bright == 0 and lux_delta < 0:
            #     self._hue.off()
            # else:
            self._hue.do_whatever(bright=self._bright)

    def _manage_heater(self):
        now = datetime.datetime.now()
        weekday = now.weekday()
        hour = now.hour
        month = now.month

        in_work_hours = 0 <= weekday <= 4 and 6 <= hour <= 14
        # in_work_hours = False

        is_winter = month <= 3 or month >= 10
        is_early_morning = 0 <= hour <= 8
        is_morning = 0 <= hour <= 12

        logging.info('weekday: {} hour: {} in_work_hours: {}'.format(weekday, hour, in_work_hours))

        temperature = self._enviro.get_temperature()
        logging.info('temperature: {}'.format(temperature))

        target_temperature = 15.0
        if is_winter:
            target_temperature += 1
        if is_early_morning:
            target_temperature += 1
        if is_morning:
            target_temperature += 1

        switch_off = temperature > target_temperature
        switch_on = temperature < target_temperature - 1 and in_work_hours

        if switch_on:
            logging.info('Switching heater on')
            self._kasa.switch_on()
        elif switch_off:
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
