import colorsys
import datetime
import itertools
import random

rgb_black = (0, 0, 0)
day_factor = 1.0
brightness = 255
is_on = True


def red():
    return 0.0, 1.0, brightness


def blue():
    return 1.0 / 3.0, 1.0, brightness


def green():
    return 2.0 / 3.0, 1.0, brightness


def white():
    return 0.0, 0.0, brightness


def get_random_hsv():
    h = random.uniform(0.0, 1.0)
    s = 1.0
    v = brightness
    # print('get_random_hsv: h {} s {} v {}'.format(h, s, v))
    return h, s, v


def get_random_rgb():
    return hsv_to_rgb(get_random_hsv())


def h_delta(hsv, hue_delta):
    h, s, v = hsv
    h = (h + hue_delta) % 1.0
    # print('h_delta: h {} s {} v {}'.format(h, s, v))
    return h, s, v


def hsv_to_rgb(hsv):
    # print('hsv_to_rgb: h {} s {} v {}'.format(*hsv))
    h = _limit(0.0, hsv[0], 1.0)
    s = _limit(0.0, hsv[1], 1.0)
    v = _limit(0, int(hsv[2]), 255)
    rgb = colorsys.hsv_to_rgb(h, s, v)
    r = int(rgb[0])
    g = int(rgb[1])
    b = int(rgb[2])
    print('hsv_to_rgb: h {} s {} v {} => r {} g {} b {}'.format(h, s, v, r, g, b))
    return r, g, b


def _limit(min_val, val, max_val):
    if val < min_val or val > max_val:
        print('_limit: Value out of range! val: {} min: {} max: {}'.format(val, min_val, max_val))
    return max(min_val, min(val, max_val))


def get_day_factor(from_dt, now_dt, to_dt, increasing):
    if increasing and now_dt >= to_dt or not increasing and now_dt <= from_dt:
        return 1.0
    elif increasing and now_dt <= from_dt or not increasing and now_dt >= to_dt:
        return 0.0
    else:
        x = now_dt - from_dt
        y = to_dt - from_dt
        day_factor = x.total_seconds() / y.total_seconds()
        if increasing:
            return day_factor
        else:
            return 1.0 - day_factor


def set_day_factor(_day_factor):
    global day_factor, brightness
    day_factor = _limit(0.0, _day_factor, 1.0)
    brightness = _limit(0, int(8 + 64 * day_factor), 255)
    print('brightness: {}'.format(brightness))


class ColourTheme(object):
    def get_next_colour_hsv(self):
        pass


class ColourLoop(ColourTheme):
    def __init__(self, colours):
        self._colours = itertools.cycle(colours)

    def get_next_colour_hsv(self, hsv=None):
        next_colour = next(self._colours)
        return next_colour()


class RedGreenBlue(ColourLoop):
    def __init__(self):
        super(RedGreenBlue, self).__init__([
            red,
            green,
            blue
        ])


class RedWhiteBlue(ColourLoop):
    def __init__(self):
        super(RedWhiteBlue, self).__init__([
            red,
            white,
            blue
        ])


class Rainbow(ColourTheme):
    def __init__(self):
        self._hsv_delta = None
        while not self._hsv_delta:
            self._hsv_delta = random.uniform(-0.05, 0.05)

    def get_next_colour_hsv(self, hsv=None):
        if hsv:
            return h_delta(hsv, self._hsv_delta)
        else:
            return get_random_hsv()


themes = itertools.cycle([
    RedGreenBlue(),
    RedWhiteBlue(),
    Rainbow()
])

current_theme = None


def next_theme():
    global current_theme
    current_theme = next(themes)


next_theme()


def get_next_colour_hsv(hsv=None):
    return current_theme.get_next_colour_hsv(hsv)


if __name__ == '__main__':
    from_dt = datetime.datetime(2019, 3, 15, 6, 0)
    to_dt = datetime.datetime(2019, 3, 15, 9, 0)
    range_minutes = int((to_dt - from_dt).seconds / 60)
    step_minutes = 15

    date_generated = (from_dt + datetime.timedelta(minutes=mins) for mins in
                      range(-30, range_minutes + 30, step_minutes))

    for now_dt in date_generated:
        sunrise = get_day_factor(from_dt, now_dt, to_dt, True)
        sunset = get_day_factor(from_dt, now_dt, to_dt, False)
        print("{} {} {}".format(now_dt, sunrise, sunset))
        set_day_factor(sunrise)
        set_day_factor(sunset)
