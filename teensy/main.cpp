#include "WProgram.h"

#define bufferlength 10000
#define serialbuffer 1000

// SERIAL COMMAND THINGS
#define SET_SPEED_COMMAND 's'
#define FREEWHEEL_COMMAND 'f'
#define BRAKE_COMMAND 'b'
#define RESUME_SPEED_COMMAND 'r'

#define LEFT_TREAD_ID 'l'
#define RIGHT_TREAD_ID 'r'
#define TURRET_ID 't'
#define GUN_ID 'g'

#define PYROELECTRIC_SENSOR 'p'
#define INFARED_SENSOR 'i'

// PIN DEFINES
#define PIN_TREAD_R1 3
#define PIN_TREAD_R2 4
#define PIN_EN_R1 7
#define PIN_EN_R2 8

#define PIN_TREAD_L1 5
#define PIN_TREAD_L2 6
#define PIN_EN_L1 9
#define PIN_EN_L2 10

#define PIN_TURRET1 11
#define PIN_TURRET2 12

// INTERNAL LIBRARY DEFINES
#define TREAD_R 0
#define TREAD_L 1
#define TURRET 2
#define GUN 3

#define FORWARD 0
#define REVERSE 1

// OTHER DATA-Y THINGS
#define PWM_MAX 255

// hopefully
#define ACTIVE LOW
#define INACTIVE HIGH

// the number of cycles to go through
// before adding one to the ramp counter
#define TICKS_PER_RAMP 1000000

//create ring buffer for storing light values
char ringbuffer[bufferlength] = {};
long bufferstart = 0;
long bufferend = 0;

//create straight buffer for storing serial data
char serialdata[serialbuffer] = {};
long serialend = 0;

int packetPos = 0;
int numLen = 6;
int currentByte = 0;

int lastSpeedL = 0;
int lastSpeedR = 0;

int targetSpeedL = 0;
int targetSpeedR = 0;

int curSpeedL = 0;
int curSpeedR = 0;

int dirL = 0;
int dirR = 0;

int directionL = 0;
int directionR = 0;

int reverseAt0R = 0;
int reverseAt0L = 0;

int rampTicks = 0;

int stopped = 0;

void sendNum(int data) {
  ringbuffer[bufferend] = data;
  bufferend++;
  if (bufferend == bufferlength) {
    bufferend = 0;
  }
}

int getMotorId(int motorChar) {
  switch(motorChar) {
  case LEFT_TREAD_ID:
    return TREAD_L;

  case RIGHT_TREAD_ID:
    return TREAD_R;

  case TURRET_ID:
    return TURRET;

  case GUN_ID:
    return GUN;
  }
}

void setSpeed(int motor, int speed, int reverse) {
  int pinA = 0;
  int pinB = 0;
  int pinEnA = 0;
  int pinEnB = 0;

  int pwmPin = 0;
  int lowPin = 0;

  switch(motor) {
    case TREAD_R:
      pinA = PIN_TREAD_R1;
      pinB = PIN_TREAD_R2;
      pinEnA = PIN_EN_R1;
      pinEnB = PIN_EN_R2;
      break;

    case TREAD_L:
      pinA = PIN_TREAD_L1;
      pinB = PIN_TREAD_L2;
      pinEnA = PIN_EN_L1;
      pinEnB = PIN_EN_L2;
      break;

    case TURRET:
      pinA = PIN_TURRET1;
      pinB = PIN_TURRET2;
      if (speed)
        speed = PWM_MAX;
      else
        speed = 0;
      break;

    default:
      return;
  }

  if (speed == 0) {
    analogWrite(pinA, 0);
    analogWrite(pinB, 0);
    digitalWriteFast(pinEnA, HIGH);
    digitalWriteFast(pinEnB, HIGH);
  } else {
    if (reverse) {
      pwmPin = pinB;
      lowPin = pinA;
    } else {
      pwmPin = pinA;
      lowPin = pinB;
    }
    int pinA = 0;
    int pinB = 0;
    int pinEnA = 0;
    int pinEnB = 0;

    switch(motor) {
      case TREAD_R:
        pinA = PIN_TREAD_R1;
        pinB = PIN_TREAD_R2;
        pinEnA = PIN_EN_R1;
        pinEnB = PIN_EN_R2;
    }
    analogWrite(pwmPin, speed);
      analogWrite(lowPin, 0);
      digitalWriteFast(pinEnA, LOW);
      digitalWriteFast(pinEnB, LOW);
  }
}

void initialize() {
  pinMode(PIN_TREAD_R1, OUTPUT);
  pinMode(PIN_TREAD_R2, OUTPUT);
  pinMode(PIN_TREAD_L1, OUTPUT);
  pinMode(PIN_TREAD_L2, OUTPUT);

  pinMode(PIN_EN_R1, OUTPUT);
  pinMode(PIN_EN_R1, OUTPUT);
  pinMode(PIN_EN_L1, OUTPUT);
  pinMode(PIN_EN_L2, OUTPUT);

  pinMode(PIN_TURRET1, OUTPUT);
  pinMode(PIN_TURRET2, OUTPUT);

  setSpeed(TREAD_R, 0, FORWARD);
  setSpeed(TREAD_L, 0, FORWARD);
  setSpeed(TURRET, 0, FORWARD);
}

extern "C" int main(void) {
  initialize();

  Serial.begin(9600);

  while (1==1) {
    rampTicks++;

    if (!stopped && rampTicks == TICKS_PER_RAMP) {
      rampTicks = 0;
      if (curSpeedL < targetSpeedL)
	curSpeedL++;

      if (curSpeedL > targetSpeedL)
	curSpeedL--;

      if (curSpeedL == 0 && reverseAt0L) {
	directionL = !directionL;
	targetSpeedL = reverseAt0L;
	reverseAt0L = 0;
      }

      if (curSpeedR < targetSpeedR)
	curSpeedR++;

      if (curSpeedR > targetSpeedR)
	curSpeedR--;

      if (curSpeedR == 0 && reverseAt0R) {
	directionR = !directionR;
	targetSpeedR = reverseAt0R;
	reverseAt0R = 0;
      }

      setSpeed(TREAD_L, curSpeedL, directionL);
      setSpeed(TREAD_R, curSpeedR, directionR);
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
      int dir = FORWARD;

      switch(cmd) {
	case SET_SPEED_COMMAND:
	  if (data < 0) {
	    data = -data;
	    dir = REVERSE;
	  }
	  // set the crap to make it reverse maybe
	  // blah blah blah
	  //setSpeed(getMotorId(motor), data * 2, dir);
	  break;

	// this sets enable off and leaves speed
	case FREEWHEEL_COMMAND:
	  // write INACTIVE to EN pins
	  // ramp to zero
	  break;

	// this sets speed to zero immediately
	case BRAKE_COMMAND:
	  // set speed to zero
	  // set target speed to zero
	  // write ACTIVE to EN pins
	  break;

	// this sets the speed to whatever it was
	// before BRAKE or FREEWHEEL commands
	case RESUME_SPEED_COMMAND:
	  // set target speed to last speed
	  // write to EN pin
	  break;
      }
    }
  }
}

