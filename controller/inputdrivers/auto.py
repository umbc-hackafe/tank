from __future__ import division, print_function
import sys, time
openni = None

def imports():
    global openni
    try:
        if not openni:
            import openni
    except ImportError:
        print("Could not import openni. Is the package installed? Are you using python2?")
        sys.exit(1)

def target_detected(src, id):
    print("Target detected (%d)" % id)

def target_lost(src, id):
    print("Target lost (%d)" % id)

def main(client, args):
    imports()

    ctx = openni.Context()
    ctx.init()

    user = openni.UserGenerator()
    user.create(ctx)

    user.register_user_cb(target_detected, target_lost)
    ctx.start_generating_all()

    while True:
        ctx.wait_and_update_all()

        target = None
        nearness = []
        for id in user.users:
            x, y, depth = tuple(user.get_com(id))

            if not sum((x, y, depth)):
                continue

            if depth > 4000:
                print("Target (%d) out of range")
                continue

            nearness.append((id, x, y, depth))

        if len(nearness) == 0: continue

        # Sort the nearest target and turn to it.
        nearness.sort(key=lambda pair: abs(pair[1]))
        target_x = nearness[0][1]

        if abs(target_x) < 50:
            print("FIRE")

        if target_x < 0:
            print("left")
        else:
            print("right")
