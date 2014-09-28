#!/usr/bin/env python2

import sys, time, argparse, threading
try:
    import xmlrpclib as xmlrpcclient
except ImportError:
    import xmlrpc.client as xmlrpcclient

import inputdrivers

def parse(raw_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("inputdriver", choices=inputdrivers.all.keys())
    parser.add_argument("--remote", "--rpc", "-r", type=str,
            default="http://localhost:1411/TANK")
    return parser.parse_args(raw_args)

def main(args):
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

    if args.inputdriver in inputdrivers.all:
        inputdrivers.run(args.inputdriver, client)

if __name__ == "__main__":
    main(parse(sys.argv[1:]))
