#include "teensy3/WProgram.h"
#include "teensy3/core_pins.h"
#include "teensy3/usb_serial.h"

#define serialbuffer 10

// SERIAL COMMAND THINGS
#define SET_SPEED_COMMAND 's'
#define FREEWHEEL_COMMAND 'f'
#define BRAKE_COMMAND 'b'
#define RESUME_SPEED_COMMAND 'r'
#define PING 'p'

#define LEFT_TREAD_ID 'l'
#define RIGHT_TREAD_ID 'r'
#define TURRET_ID 't'
#define GUN_ID 'g'

// the number of cycles to go through
// before adding one to the ramp counter
#define TICKS_PER_RAMP 10000
#define TICKS_PER_PING 5000000

//create straight buffer for storing serial data
char serialdata[serialbuffer] = {};
long serialend = 0;

struct motor {
    int pinA;
    int pinB;
    int pinEnA;
    int pinEnB;
    int setSpeed;
    int setDir;
    int curSpeed;
    int curDir;
    int freewheel;
};

struct motor treadr = {.pinA=3,  .pinB=4,  .pinEnA=7,  .pinEnB=8,  .setSpeed=0, .setDir=0, .curSpeed=0, .curDir=0, .freewheel=0};
struct motor treadl = {.pinA=5,  .pinB=6,  .pinEnA=9,  .pinEnB=10, .setSpeed=0, .setDir=0, .curSpeed=0, .curDir=0, .freewheel=0};
struct motor turret = {.pinA=11, .pinB=12, .pinEnA=0,  .pinEnB=0,  .setSpeed=0, .setDir=0, .curSpeed=0, .curDir=0, .freewheel=0};

void setSpeed(motor *motor, int speed, int dir) {
    motor->setSpeed = speed;
    motor->setDir = dir;
}

void update(motor *motor) {
    if (motor->curDir != motor->setDir) {
        if (motor->curSpeed > 0) {
            motor->curSpeed--;
        }
        if (motor->curSpeed == 0) {
            motor->curDir = motor->setDir;
        }
    } else {
        if (motor->curSpeed < motor->setSpeed) {
            motor->curSpeed++;
        } else if (motor->curSpeed > motor->setSpeed) {
            motor->curSpeed--;
        }
    }
    
    if (motor->curDir) {
        analogWrite(motor->pinB, motor->curSpeed);
        analogWrite(motor->pinA, 0);
    } else {
        analogWrite(motor->pinA, motor->curSpeed);
        analogWrite(motor->pinB, 0);
    }
    digitalWriteFast(motor->pinEnA, !motor->freewheel);
    digitalWriteFast(motor->pinEnB, !motor->freewheel);
}

void initialize() {
    pinMode(treadr.pinA, OUTPUT);
    pinMode(treadr.pinB, OUTPUT);
    pinMode(treadr.pinEnA, OUTPUT);
    pinMode(treadr.pinEnB, OUTPUT);
    
    pinMode(treadl.pinA, OUTPUT);
    pinMode(treadl.pinB, OUTPUT);
    pinMode(treadl.pinEnA, OUTPUT);
    pinMode(treadl.pinEnB, OUTPUT);
    
    pinMode(turret.pinA, OUTPUT);
    pinMode(turret.pinB, OUTPUT);
    pinMode(turret.pinEnA, OUTPUT);
    pinMode(turret.pinEnB, OUTPUT);
}

extern "C" int main(void) {
  initialize();

  Serial.begin(9600);
  
  int rampTicks = 0;
  int pingTicks = 0;
  
  while (1==1) {
    rampTicks++;
    pingTicks++;

    if (rampTicks == TICKS_PER_RAMP) {
        update(&treadr);
        update(&treadl);
        update(&turret);
        rampTicks = 0;
    } 
    if (pingTicks == TICKS_PER_PING) {
        treadr.setSpeed = 0;
        treadr.curSpeed = 0;
        treadr.freewheel = 0;
        treadl.setSpeed = 0;
        treadl.curSpeed = 0;
        treadl.freewheel = 0;
        turret.setSpeed = 0;
        turret.curSpeed = 0;
        turret.freewheel = 0;
    }

    if (Serial.available()) {
      int data = Serial.read();
      if (data == 0xCA) {
        serialend = 0;
      }
      else {
        serialdata[serialend] = data;
        serialend++;
      }
    }

    if (serialend >= 4 && serialdata[0] == 0xFE) {
      int cmd = serialdata[1];
      int motor = serialdata[2];
      int data = serialdata[3];
      int dir = serialdata[4];

      switch(cmd) {
	case SET_SPEED_COMMAND:
            switch(motor) {
                case RIGHT_TREAD_ID:
                    setSpeed(&treadr, data, dir);
                    break;
                case LEFT_TREAD_ID:
                    setSpeed(&treadl, data, dir);
                    break;
                case TURRET_ID:
                    setSpeed(&turret, data, dir);
                    break;
                default:
                    setSpeed(&treadr, data, dir);
                    break;
            }
            pingTicks = 0;
            break;
        case PING:
            pingTicks = 0;
            break;
      }
    }
  }
}

