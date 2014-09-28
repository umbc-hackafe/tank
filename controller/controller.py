#!/usr/bin/env python2
from __future__ import print_function
import sys, time, argparse, threading

mock = None

try:
    import mock
except ImportError:
    pass

try:
    import xmlrpclib as xmlrpcclient
except ImportError:
    import xmlrpc.client as xmlrpcclient

import inputdrivers

def parse(raw_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("inputdriver",
        help="Name of the preferred input method",
        choices=inputdrivers.all.keys())
    parser.add_argument("--remote", "--rpc", "-r", type=str,
            help="full URL of an RPC server",
            default="http://localhost:1411/TANK")
    parser.add_argument("--continuous", "-c", action='store_true',
            help="retry the input driver if it fails")
    if mock:
        # Only allow mocking if the library is available.
        parser.add_argument("--mock", action='store_true',
                help="mock the RPC server")

    return parser.parse_args(raw_args)

def main(args):
    if "mock" in args and args.mock:
        client = mock.MagicMock()
    else:
        client = xmlrpcclient.ServerProxy(args.remote)

    # Set up a thread to ping the RPC server constantly. If it drops for
    # more than 5 seconds, all of the motors will brake.
    def client_ping():
        while True:
            client.ping()
            time.sleep(1)

    client_pinger = threading.Thread(group=None, target=client_ping)
    client_pinger.daemon = True
    client_pinger.start()

    while True:
        if args.inputdriver in inputdrivers.all:
            #client.print("Joining client via %s" % args.inputdriver)
            inputdrivers.run(args.inputdriver, client)

        print("Lost input method. Halting tank.")
        client.halt()

        if not args.continuous:
            break
        else:
            print("Retrying input method.")

if __name__ == "__main__":
    main(parse(sys.argv[1:]))
