from __future__ import division
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

REST = (117, 130)
MIN = (22, 33)
MAX = (215, 227)
THRESHOLD = 10
GRANULARITY = 5

def main(client, args):
    imports()

    wm = get_wiimote()

    position = (0, 0)

    print("Press Home to exit.")
    last = None

    while True:
        if (wm.state['buttons'] & cwiid.BTN_HOME) > 0:
            break

        # Print nunchuck values if appropriate.
        if 'nunchuk' in wm.state:
            position = wm.state['nunchuk']['stick']
            x, y = position
            if abs(x - REST[0]) > THRESHOLD:
                steer = max(min((x - REST[0]) / (MAX[0] - REST[0]), 1), -1)
            else:
                steer = 0

            if abs(y - REST[1]) > THRESHOLD:
                speed = max(min((y - REST[1]) / (MAX[1] - REST[1]), 1), -1)
            else:
                speed = 0

            movement = (steer, speed)

        if movement != last:
            print(movement)
            last = movement

    wm.led = 15
    wm.rumble = True
    time.sleep(0.25)
    wm.led = 0
    wm.rumble = False
