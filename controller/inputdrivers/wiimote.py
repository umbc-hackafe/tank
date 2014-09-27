import sys, time
cwiid = None

def imports():
    global cwiid
    try:
        import cwiid
    except ImportError:
        print("Could not import cwiid. Is the package installed? Are you using python2?")
        sys.exit(1)

def get_wiimote():
    print("Press 1+2 on your Wiimote to connect...")
    wm = None
    while(wm == None):
        try:
            wm = cwiid.Wiimote()

        except RuntimeError as e:
            print(e)
            print("Trying again...")

    print("Connected!")
    wm.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_ACC | cwiid.RPT_EXT
    wm.rumble = True
    time.sleep(0.25)
    wm.rumble = False
    time.sleep(0.25)
    wm.led = 1

    return wm

def main(args):
    imports()

    wm = get_wiimote()

    position = (0, 0)

    print("Press Home to exit.")
    while True:
        if (wm.state['buttons'] & cwiid.BTN_HOME) > 0:
            break

        # Print nunchuck values if appropriate.
        if 'nunchuk' in wm.state \
                and wm.state['nunchuk']['buttons'] & cwiid.NUNCHUK_BTN_Z > 0:
            joystick = wm.state['nunchuk']['stick']
            move = joystick[0] - 118, joystick[1] - 132
            position = position[0] + move[0], position[1] + move[1]

        print(position)

    wm.led = 15
    wm.rumble = True
    time.sleep(0.25)
    wm.led = 0
    wm.rumble = False
