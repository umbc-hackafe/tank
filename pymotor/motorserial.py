#!/usr/bin/env python3
import argparse
import collections
import os
import random
import serial
import sys
import threading
from xmlrpc import server as xrpcserve

DEFAULT_SERIAL = "/dev/ttyACM0"

SENTINEL = b"\xCA\xFE"

SET_SPEED_COMMAND = SENTINEL + b"s"
FREEWHEEL_COMMAND = SENTINEL + b"f"
BRAKE_COMMAND = SENTINEL + b"b"
RESUME_SPEED_COMMAND = SENTINEL + b"r"

LEFT_TREAD_ID = b"\x00"
RIGHT_TREAD_ID = b"\x01"
TURRET_ID = b"\x02"
GUN_ID = b"\x03"

PYROELECTRIC_SENSOR = b"p"
INFARED_SENSOR = b"i"

def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument("--serial-port", "-s", help="The path to the serial port to connect to", type=str, nargs="?",
                      default=DEFAULT_SERIAL)
  parser.add_argument("--port", "-p", help="Port for the RPC Server", type=int, nargs="?", default=1411)
  parser.add_argument("--audio", "-a", help="Should audio be played by this instance.", action="store_true")
  parser.add_argument("--no-ping", "-n", action="store_false")
  args = parser.parse_args()

  server = xrpcserve.SimpleXMLRPCServer(("localhost", args.port), requestHandler=RequestHandler, allow_none=True)
  server.register_introspection_functions()

  with TankSerial(args.serial_port) as tank:
    # Handle the pinging
    if args.no_ping:
      ping_event = threading.Event()
      def ping():
        ping_event.set()
      server.register_function(ping)
      rpc_timeout_thread = threading.Thread(target=rpc_timeout, args=(ping_event, tank), daemon=True)
      rpc_timeout_thread.start()

    server.register_function(print)

    # Register everything from the tank
    server.register_instance(tank, allow_dotted_names=True)

    # Run Audio
    audio_handler = AudioHandler(args.audio)
    server.register_function(audio_handler.play_sound)
    
    server.serve_forever()


class AudioHandler(object):
  files = {
    "attack": ["audio/Turret_turret_deploy_{}.wav".format(i) for i in range(1, 7)],
    "search": ["audio/Turret_turret_autosearch_{}.wav".format(i) for i in range(1, 7)],
    "alarm": ["audio/Turret_alarm.wav " * 6],
  }

  def __init__(self, active):
    self.active = active

  def play_sound(self, category):
    if not self.active:
      return
    sound = random.choice(self.files[category])
    os.system("aplay {} &".format(sound))


class RequestHandler(xrpcserve.SimpleXMLRPCRequestHandler):
  rpc_paths = ("/TANK",)


def rpc_timeout(event, tank):
  while tank.is_active():
    if not event.wait(timeout=5.0) and tank.is_active():
      tank.halt()
    else:
      event.clear()
  

class TankSerial(object):

  def __init__(self, serial_port):
    self.serial = serial.Serial(serial_port, 19200)
#    self.serial.write = print
    self.left_tread = Motor(LEFT_TREAD_ID, self.serial)
    self.right_tread = Motor(RIGHT_TREAD_ID, self.serial)
    self.turret = Motor(TURRET_ID, self.serial)
    self.gun = Motor(GUN_ID, self.serial)

    self.pyro_sensors = collections.defaultdict(threading.Event)
    self.pyro_lock = threading.Lock()
    self.ir_sensors = collections.defaultdict(threading.Event)
    self.ir_lock = threading.Lock()
    self.sensor_monitor_thread = threading.Thread(target=self.sensor_monitor, daemon=True)
    self.sensor_monitor_thread.start()

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    if self.serial.isOpen():
      self.serial.close()

  def is_active(self):
    return self.serial.isOpen()

  def sensor_monitor(self):
    while self.serial.isOpen():
      sensor_type, identifier = self.serial.read(2).decode("utf-8")

      if sensor_type == PYROELECTRIC_SENSOR:
        value = bool(self.serial.read(1)[0])
        with self.pyro_lock:
          if value:
            self.pyro_sensors[identifier].set()
          else:
            self.pyro_sensors[identifier].clear()
      elif sensor_type == INFARED_SENSOR:
        value = bool(self.serial.read(1)[0])
        with self.ir_lock:
          if value:
            self.ir_sensors[identifier].set()
          else:
            self.ir_sensors[identifier].clear()
      else:
        print("Invalid sensor type:", sensor_type)

  def drive(self, speed, steer):
    speed = min(max(-1, speed), 1)
    
    left_motor = min(max(speed + steer, -1), 1)
    right_motor = min(max(speed - steer, -1), 1)
    self.left_tread.set_speed(left_motor)
    self.right_tread.set_speed(right_motor)

  def center_turret(self):
    with self.ir_lock:
      event = self.ir_sensors['c']

    if not event.is_set():
      self.turret.set_speed(1)
      event.wait(20.0)
      self.turret.brake()

  def halt(self):
    self.left_tread.brake()
    self.right_tread.brake()
    self.turret.brake()
    self.gun.brake()
    

class Motor(object):
  def __init__(self, serial_id, serial):
    self.serial_id = serial_id
    self.serial = serial

  def set_speed(self, speed):
    speed = min(max(-1, speed), 1)
    speed = int(speed * (2**7 - 1))
    command = SET_SPEED_COMMAND + self.serial_id + speed.to_bytes(1, "big", signed=True)
    assert(len(command) == 5)
    self.serial.write(command)
    print("Set Speed of motor", self.serial_id, "to:", speed)

  def freewheel(self):
    command = FREEWHEEL_COMMAND + self.serial_id + b"\x00"
    assert(len(command) == 5)
    self.serial.write(command)
    print("Now freewheeling on motor", self.serial_id)

  def brake(self):
    command = BRAKE_COMMAND + self.serial_id + b"\x00"
    assert(len(command) == 5)
    self.serial.write(command)
    print("Now braking on motor", self.serial_id)
    
  def resume(self):
    command = RESUME_SPEED_COMMAND + self.serial_id + b"\x00"
    assert(len(command) == 5)
    self.serial.write(command)
    print("Resuming old speed on motor", self.serial_id)
    

if __name__ == "__main__":
  main(sys.argv)
