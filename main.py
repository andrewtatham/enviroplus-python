from helper.phillips_hue_wrapper import HueWrapper


    hue = HueWrapper()
    hue.connect()
    if hue.is_on:
        hue.on()
    hue.colour_loop_off()
    if hue.is_off:
        hue.off()


