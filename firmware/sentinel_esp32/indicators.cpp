#include "indicators.h"
#include "config.h"
#include "logging.h"

IndicatorManager indicatorManager;

IndicatorManager::IndicatorManager() :
  _buzzerActive(false), _currentPattern(PATTERN_NONE),
  _lastToggleTime(0), _toggleCount(0), _currentState(false) {}

void IndicatorManager::init() {
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
}

void IndicatorManager::setBuzzerActive(bool active) {
  _buzzerActive = active;
  if (!active && _currentPattern == PATTERN_NONE) {
    digitalWrite(BUZZER_PIN, LOW);
  }
}

void IndicatorManager::triggerIdentify() {
  LOG_INFO("Triggered IDENTIFY pattern (non-blocking)");
  _currentPattern = PATTERN_IDENTIFY;
  _lastToggleTime = millis();
  _toggleCount = 0;
  _currentState = true;
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, LOW);
}

void IndicatorManager::triggerDispatch() {
  LOG_INFO("Triggered DISPATCH pattern (non-blocking)");
  _currentPattern = PATTERN_DISPATCH;
  _lastToggleTime = millis();
  _toggleCount = 0;
  _currentState = true;
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
}

bool IndicatorManager::isBuzzerActive() {
  return _buzzerActive;
}

const char* IndicatorManager::getPatternName() {
  switch(_currentPattern) {
    case PATTERN_IDENTIFY: return "IDENTIFY";
    case PATTERN_DISPATCH: return "DISPATCH";
    default: return _buzzerActive ? "HAZARD_ALARM" : "NONE";
  }
}

void IndicatorManager::update() {
  unsigned long now = millis();

  switch (_currentPattern) {
    case PATTERN_IDENTIFY:
      if (now - _lastToggleTime >= 150) {
        _lastToggleTime = now;
        _currentState = !_currentState;
        digitalWrite(LED_PIN, _currentState ? HIGH : LOW);
        _toggleCount++;
        if (_toggleCount >= 30) {
          _currentPattern = PATTERN_NONE;
          digitalWrite(LED_PIN, LOW);
          LOG_INFO("IDENTIFY pattern finished");
        }
      }
      break;

    case PATTERN_DISPATCH:
      if (now - _lastToggleTime >= 80) {
        _lastToggleTime = now;
        _currentState = !_currentState;
        digitalWrite(LED_PIN, _currentState ? HIGH : LOW);
        digitalWrite(BUZZER_PIN, _currentState ? HIGH : LOW);
        _toggleCount++;
        if (_toggleCount >= 8) {
          _currentPattern = PATTERN_NONE;
          digitalWrite(LED_PIN, LOW);
          digitalWrite(BUZZER_PIN, _buzzerActive ? HIGH : LOW);
          LOG_INFO("DISPATCH pattern finished");
        }
      }
      break;

    case PATTERN_NONE:
    default:
      if (_buzzerActive) {
        if (now - _lastToggleTime >= 120) {
          _lastToggleTime = now;
          _currentState = !_currentState;
          digitalWrite(BUZZER_PIN, _currentState ? HIGH : LOW);
        }
      } else {
        digitalWrite(BUZZER_PIN, LOW);
      }
      break;
  }
}
