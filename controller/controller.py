#!/usr/bin/env python2

import sys, argparse
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

    if args.inputdriver in inputdrivers.all:
        inputdrivers.run(args.inputdriver, client)

if __name__ == "__main__":
    main(parse(sys.argv[1:]))
