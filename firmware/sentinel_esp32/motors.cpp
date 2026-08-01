#include "motors.h"
#include "config.h"

MotorController motorController;

MotorController::MotorController() :
  _currentSpeedL(0), _currentSpeedR(0), _targetSpeedL(0), _targetSpeedR(0),
  _targetDirL(true), _targetDirR(true), _currentDirL(true), _currentDirR(true),
  _lastRampTime(0) {}

void MotorController::init() {
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  stopImmediate();
}

void MotorController::setDirectionAndSpeed(bool dirL, bool dirR, int speedL, int speedR) {
  _targetDirL = dirL;
  _targetDirR = dirR;
  _targetSpeedL = speedL;
  _targetSpeedR = speedR;
}

void MotorController::update() {
  unsigned long now = millis();
  if (now - _lastRampTime >= RAMP_INTERVAL_MS) {
    _lastRampTime = now;

    // Left Motor (A) Protection
    if (_currentDirL != _targetDirL && _currentSpeedL > 0) {
      _currentSpeedL = max(_currentSpeedL - RAMP_STEP, 0);
    } else {
      if (_currentSpeedL == 0) {
        _currentDirL = _targetDirL;
        digitalWrite(IN1, _currentDirL ? HIGH : LOW);
        digitalWrite(IN2, _currentDirL ? LOW : HIGH);
      }
      if (_currentSpeedL < _targetSpeedL) {
        _currentSpeedL = min(_currentSpeedL + RAMP_STEP, _targetSpeedL);
      } else if (_currentSpeedL > _targetSpeedL) {
        _currentSpeedL = max(_currentSpeedL - RAMP_STEP, _targetSpeedL);
      }
    }

    // Right Motor (B) Protection
    if (_currentDirR != _targetDirR && _currentSpeedR > 0) {
      _currentSpeedR = max(_currentSpeedR - RAMP_STEP, 0);
    } else {
      if (_currentSpeedR == 0) {
        _currentDirR = _targetDirR;
        digitalWrite(IN3, _currentDirR ? HIGH : LOW);
        digitalWrite(IN4, _currentDirR ? LOW : HIGH);
      }
      if (_currentSpeedR < _targetSpeedR) {
        _currentSpeedR = min(_currentSpeedR + RAMP_STEP, _targetSpeedR);
      } else if (_currentSpeedR > _targetSpeedR) {
        _currentSpeedR = max(_currentSpeedR - RAMP_STEP, _targetSpeedR);
      }
    }

    analogWrite(ENA, _currentSpeedL);
    analogWrite(ENB, _currentSpeedR);
  }
}

void MotorController::stopImmediate() {
  _targetSpeedL = 0;
  _targetSpeedR = 0;
  _currentSpeedL = 0;
  _currentSpeedR = 0;
  _currentDirL = _targetDirL = true;
  _currentDirR = _targetDirR = true;
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  analogWrite(ENA, 0); analogWrite(ENB, 0);
}

int MotorController::getCurrentSpeedL() { return _currentSpeedL; }
int MotorController::getCurrentSpeedR() { return _currentSpeedR; }
bool MotorController::getTargetDirL() { return _targetDirL; }
bool MotorController::getTargetDirR() { return _targetDirR; }
