#ifndef SENTINEL_MOTORS_H
#define SENTINEL_MOTORS_H

#include <Arduino.h>

class MotorController {
private:
  int _currentSpeedL;
  int _currentSpeedR;
  int _targetSpeedL;
  int _targetSpeedR;
  bool _targetDirL;  // true = forward, false = backward
  bool _targetDirR;
  bool _currentDirL;
  bool _currentDirR;

  unsigned long _lastRampTime;
  const unsigned long RAMP_INTERVAL_MS = 5; // Ticks speed changes every 5ms
  const int RAMP_STEP = 8;                  // Rate of ramp (8 units per 5ms)

public:
  MotorController();
  void init();
  void setDirectionAndSpeed(bool dirL, bool dirR, int speedL, int speedR);
  void update();
  void stopImmediate();
  
  int getCurrentSpeedL();
  int getCurrentSpeedR();
  bool getTargetDirL();
  bool getTargetDirR();
};

extern MotorController motorController;

#endif // SENTINEL_MOTORS_H
