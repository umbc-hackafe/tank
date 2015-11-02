#!/usr/bin/env python3
import argparse
import collections
import os
import random
import serial
import sys
import threading
import time
from xmlrpc import server as xrpcserve

DEFAULT_SERIAL = "/dev/ttyACM0"

SENTINEL = b"\xCA\xFE"

SET_SPEED_COMMAND = SENTINEL + b"s"
FREEWHEEL_COMMAND = SENTINEL + b"f"
BRAKE_COMMAND = SENTINEL + b"b"
RESUME_SPEED_COMMAND = SENTINEL + b"r"

LEFT_TREAD_ID = b"r"
RIGHT_TREAD_ID = b"l"
TURRET_ID = b"t"
GUN_ID = b"g"

PYROELECTRIC_SENSOR = b"p"
INFARED_SENSOR = b"i"

# Board pin number, NOT BCM ID
GUN_PIN = 3

gpio_setup = False

def setup_gpio():
  import RPi.GPIO as gpio
  gpio.setmode(gpio.BOARD)
  gpio.setwarnings(False)
  # Don't shoot as soon as we set this up!
  gpio.setup(GUN_PIN, gpio.OUT, initial=gpio.HIGH)

  global gpio_setup
  gpio_setup = True

def monkeypatch_serial():
  class FakeSerial:
    def __init__(self, *args, **kwargs):
      pass

    def isOpen(self):
      return True

    def close(self):
      pass

    def read(self, num):
      while True:
        time.sleep(3600)
      return None

    def write(self, message):
      print(str(message))

  serial.Serial = FakeSerial

def clamp(num, minimum, maximum):
  return min(max(num, minimum), maximum)

def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument("--serial-port", "-s", help="The path to the serial port to connect to", type=str, nargs="?",
                      default=DEFAULT_SERIAL)
  parser.add_argument("--port", "-p", help="Port for the RPC Server", type=int, nargs="?", default=1411)
  parser.add_argument("--audio", "-a", help="Should audio be played by this instance.", action="store_true")
  parser.add_argument("--no-ping", "-n", action="store_false")
  parser.add_argument("--dummy-serial", "-d", action="store_true")
  parser.add_argument("--no-gpio", "-g", action="store_true")
  args = parser.parse_args()

  if args.dummy_serial:
    monkeypatch_serial()

  server = xrpcserve.SimpleXMLRPCServer(("localhost", args.port), requestHandler=RequestHandler, allow_none=True)
  server.register_introspection_functions()

  if not args.no_gpio:
    setup_gpio()

  with TankSerial(args.serial_port) as tank:
    # Handle the pinging
    if args.no_ping:
      ping_event = threading.Event()
      def ping():
        ping_event.set()
        tank.ping()

      server.register_function(ping)
      rpc_timeout_thread = threading.Thread(target=rpc_timeout, args=(ping_event, tank), daemon=True)
      rpc_timeout_thread.start()
    else:
      def ping():
        pass
      server.register_function(ping)

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
    if not event.wait(timeout=1.0) and tank.is_active():
      tank.halt()
    else:
      event.clear()


class TankSerial(object):

  def __init__(self, serial_port):
    while True:
      try:
        self.serial = serial.Serial(serial_port, 19200)
        break
      except:
        print("Serial port not found... trying again in 5s.")
        time.sleep(5)

    self.serial_lock = threading.Lock()
#    self.serial.write = print
    self.left_tread = Motor(LEFT_TREAD_ID, self.serial, self.serial_lock)
    self.right_tread = Motor(RIGHT_TREAD_ID, self.serial, self.serial_lock)
    self.turret = Motor(TURRET_ID, self.serial, self.serial_lock)
    self.gun = Motor(GUN_ID, self.serial, self.serial_lock)

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

  def ping(self):
    with self.serial_lock:
      command = SENTINEL + b"pppp"
      self.serial.write(command)

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

  def fire(self, stop=False, continuous=False):
    if gpio_setup:
      if stop:
        gpio.output(GUN_PIN, gpio.HIGH)
      else:
        gpio.output(GUN_PIN, gpio.LOW)
        if not continuous:
          time.sleep(.1)
          gpio.output(GUN_PIN, gpio.HIGH)
    else:
      print("Not firing -- no GPIO")

  def drive(self, speed, steer):
    #####################################
    ### DIFFERENTIAL DRIVE KINEMATICS ###
    #####################################
    #
    # [[x]    [[(r * φ_1) / 2 + (r * φ_2) / 2]
    #  [θ]] =  [(r * φ_1) / 2l - (r * φ_2) / 2l]]
    #
    # - x: the linear velocity (use m/s)
    # - θ: the rotational velocity (use radians/s)
    # - r: the radius of the wheel (use m)
    # - φ: the rotational velocty of the wheel (use radians/s)
    #    - φ_1 is the left wheel
    #    - φ_2 is the right wheel
    # - l: the distance between the wheels (use m)
    #
    # - r * φ_n is the linear velocity of the wheel on the surface, assuming φ_n is using
    #   radians.
    #
    #
    # Not knowing r, l, or the min/max values of φ, we cannot do calculations to drive at
    # *specific* linear or rotational velocities.
    #
    # However, we can instead use normalized values. We assume that the wheel speed must
    # be between -1 and 1, where -1 is full reverse, and 1 is full forward. So we will
    # replace r * φ_1 with 'a', and r * φ_2 with 'b', where -1 <= a,b <= 1. We can then
    # solve for normalized x and θ, and get: -1 <= x-θ <= 1, -1 <= x+θ <= 1. These
    # inequalities form a diamond around the origin, which outlines the set of possible
    # combinations of linear and rotational velocity which are acheiveable. (Equivalently,
    # |x|+|θ|<=1)
    #
    # The inverse kinematics of differential drive is just the solution for r * φ_n for
    # each wheel, or in our case (without measurements), the solution for a and b, is:
    #
    # r/2 * [[φ_1]    [[(x + l * θ) / 2]
    #        [φ_2]] =  [(x - l * θ) / 2]]
    #
    # [[φ_1]    [[(x + l * θ) / r]
    #  [φ_2]] =  [(x - l * θ) / r]]
    #
    # [[a]    [[x + θ]
    #  [b]] =  [x - θ]]
    #
    #
    # So to drive our tank with a certain forward/turn ammount, we first need to limit the
    # speed and steer to sum and subtract within [1,-1], then combine them to get the
    # motor drive speeds. -- Halariously, we apparently got this right the first time.
    #
    # If we knew either the radius of the driving wheels, tread separation, and how motor
    # power level affected rotational velocity, or just how motor power level affected
    # linear tread velocity, then we could use that here to try to rotate or move at
    # specific speeds instead of just proportions of maximum velocity.

    divisor = abs(speed) + abs(steer) if abs(speed) + abs(steer) > 1.0 else 1.0

    left_motor = clamp((speed + steer) / divisor, -1, 1)
    right_motor = clamp((speed - steer) / divisor, -1, 1)
    self.left_tread.set_speed(left_motor)
    self.right_tread.set_speed(right_motor)

  def spin(self, speed):
    speed = min(max(-1, speed), 1)
    self.turret.set_speed(speed)

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
  def __init__(self, serial_id, serial, serial_lock):
    self.serial_id = serial_id
    self.serial = serial
    self.serial_lock = serial_lock

  def set_speed(self, speed):
    speed = min(max(-1, speed), 1)
    direction = 0 if speed >= 0 else 1
    speed = int(abs(speed) * (2**8 - 1))
    command = SET_SPEED_COMMAND + self.serial_id + speed.to_bytes(1, "big") + direction.to_bytes(1, "big")

    assert(len(command) == 6)
    with self.serial_lock:
      self.serial.write(command)
    print("Set Speed of motor", self.serial_id, "to:", speed)

  def freewheel(self):
    command = FREEWHEEL_COMMAND + self.serial_id + b"\x00"
    assert(len(command) == 5)
    with self.serial_lock:
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
    with self.serial_lock:
      self.serial.write(command)
    print("Resuming old speed on motor", self.serial_id)


if __name__ == "__main__":
  main(sys.argv)
