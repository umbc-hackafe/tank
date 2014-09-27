#!/usr/bin/env python2

import sys, argparse

import inputdrivers

def parse(raw_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("inputdriver", choices=inputdrivers.all.keys())
    return parser.parse_args(raw_args)

def main(args):
    if args.inputdriver in inputdrivers.all:
        inputdrivers.run(args.inputdriver)

if __name__ == "__main__":
    main(parse(sys.argv[1:]))
