#!/usr/bin/env python3
import argparse
from xmlrpc import server as xrpcserve
import serial
import sys

DEFAULT_SERIAL = "/dev/ttyACM0"

SET_SPEED_COMMAND = "s"
FREEWHEEL_COMMAND = "f"
BRAKE_COMMAND = "b"
RESUME_SPEED_COMMAND = "r"

LEFT_TREAD_ID = "l"
RIGHT_TREAD_ID = "r"
TURRET_ID = "t"

def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument("--serial-port", "-s", help="The path to the serial port to connect to", type=str, nargs="?",
                      default=DEFAULT_SERIAL)
  parser.add_argument("--port", "-p", help="Port for the RPC Server", type=int, nargs="?", default=1411)
  args = parser.parse_args()

  server = xrpcserve.SimpleXMLRPCServer(("localhost", args.port), requestHandler=RequestHandler, allow_none=True)
  server.register_introspection_functions()

  with TankSerial(args.serial_port) as tank:
    server.register_function(print)
    server.register_instance(tank, allow_dotted_names=True)
    server.serve_forever()

class RequestHandler(xrpcserve.SimpleXMLRPCRequestHandler):
  rpc_paths = ("/TANK",)

class TankSerial(object):

  def __init__(self, serial_port):
    self.serial = serial.Serial(serial_port, 19200)
    self.left_tread = Motor(LEFT_TREAD_ID, self.serial)
    self.right_tread = Motor(RIGHT_TREAD_ID, self.serial)
    self.turret = Motor(TURRET_ID, self.serial)

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    if self.serial.isOpen():
      self.serial.close()

  def drive(self, speed, steer):
    speed = min(max(-1, speed), 1)
    
    left_motor = min(max(speed + 2 * steer, -1), 1)
    right_motor = min(max(speed + -2 * steer, -1), 1)
    self.left_tread.set_speed(left_motor)
    self.right_tread.set_speed(right_motor)
    
class Motor(object):
  def __init__(self, serial_id, serial):
    self.serial_id = serial_id
    self.serial = serial

  def set_speed(self, speed):
    speed = min(max(-1, speed), 1)
    speed = int(speed * (2**15 - 1))
    command = bytearray(SET_SPEED_COMMAND + self.serial_id, encoding="utf-8") + speed.to_bytes(2, "little", signed=True)
    self.serial.write(command)
    print("Set Speed of motor", self.serial_id, "to:", speed)

  def freewheel(self):
    command = bytearray(FREEWHEEL_COMMAND + self.serial_id, encoding="utf-8")
    self.serial.write(command)
    print("Now freewheeling on motor", self.serial_id)

  def brake(self):
    command = bytearray(BRAKE_COMMAND + self.serial_id, encoding="utf-8")
    self.serial.write(command)
    print("Now braking on motor", self.serial_id)
    
  def resume(self):
    command = bytearray(RESUME_SPEED_COMMAND + self.serial_id, encoding="utf-8")
    self.serial.write(command)
    print("Resuming old speed on motor", self.serial_id)
    

if __name__ == "__main__":
  main(sys.argv)
