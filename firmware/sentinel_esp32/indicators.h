#ifndef SENTINEL_INDICATORS_H
#define SENTINEL_INDICATORS_H

#include <Arduino.h>

enum IndicatorPattern {
  PATTERN_NONE,
  PATTERN_IDENTIFY,
  PATTERN_DISPATCH
};

class IndicatorManager {
private:
  bool _buzzerActive; // Hazard alarm buzzer status
  
  IndicatorPattern _currentPattern;
  unsigned long _lastToggleTime;
  int _toggleCount;
  bool _currentState;

public:
  IndicatorManager();
  void init();
  void update();
  
  void setBuzzerActive(bool active);
  void triggerIdentify();
  void triggerDispatch();
  
  bool isBuzzerActive();
  const char* getPatternName();
};

extern IndicatorManager indicatorManager;

#endif // SENTINEL_INDICATORS_H
