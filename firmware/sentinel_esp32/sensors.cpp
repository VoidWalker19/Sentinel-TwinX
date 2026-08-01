#include "sensors.h"
#include "config.h"
#include "logging.h"

DHT dht(DHT_PIN, DHT_TYPE);
SensorManager sensorManager;

SensorManager::SensorManager() :
  _mq2Filtered(0.0), _mq7Filtered(0.0), _mq135Filtered(0.0),
  _lastReadTime(0), _batteryV(0.0), _batteryPct(0), _lastBatteryTime(0),
  _dhtHealthy(true), _sonarHealthy(true) {}

void SensorManager::init() {
  pinMode(MQ2_PIN, INPUT);
  pinMode(MQ7_PIN, INPUT);
  pinMode(MQ135_PIN, INPUT);
  pinMode(BATTERY_PIN, INPUT);
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Seed EMA filters with raw readings
  _mq2Filtered = analogRead(MQ2_PIN);
  _mq7Filtered = analogRead(MQ7_PIN);
  _mq135Filtered = analogRead(MQ135_PIN);

  dht.begin();
}

void SensorManager::update() {
  unsigned long now = millis();
  
  // Update EMA filtered gas sensors
  if (now - _lastReadTime >= READ_INTERVAL_MS) {
    _lastReadTime = now;
    int mq2Raw = analogRead(MQ2_PIN);
    int mq7Raw = analogRead(MQ7_PIN);
    int mq135Raw = analogRead(MQ135_PIN);

    _mq2Filtered = (EMA_ALPHA * mq2Raw) + ((1.0 - EMA_ALPHA) * _mq2Filtered);
    _mq7Filtered = (EMA_ALPHA * mq7Raw) + ((1.0 - EMA_ALPHA) * _mq7Filtered);
    _mq135Filtered = (EMA_ALPHA * mq135Raw) + ((1.0 - EMA_ALPHA) * _mq135Filtered);
  }

  // Update battery level
  if (now - _lastBatteryTime >= BATTERY_INTERVAL_MS || _lastBatteryTime == 0) {
    _lastBatteryTime = now;
    readBattery();
  }

  // Check DHT health state
  float t = dht.readTemperature();
  if (isnan(t)) {
    if (_dhtHealthy) {
      _dhtHealthy = false;
      LOG_ERROR("DHT11 sensor reporting NaN values. Check connection.");
    }
  } else {
    _dhtHealthy = true;
  }
}

int SensorManager::getMQ2() { return (int)_mq2Filtered; }
int SensorManager::getMQ7() { return (int)_mq7Filtered; }
int SensorManager::getMQ135() { return (int)_mq135Filtered; }
float SensorManager::getBatteryVoltage() { return _batteryV; }
int SensorManager::getBatteryPercentage() { return _batteryPct; }
bool SensorManager::isDHTHealthy() { return _dhtHealthy; }
bool SensorManager::isSonarHealthy() { return _sonarHealthy; }
void SensorManager::setSonarHealthy(bool healthy) { _sonarHealthy = healthy; }

const char* SensorManager::getHealthStatus() {
  if (!_dhtHealthy && !_sonarHealthy) return "CRITICAL_SENSOR_FAULT";
  if (!_dhtHealthy) return "DHT_FAULT";
  if (!_sonarHealthy) return "ULTRASONIC_FAULT";
  if (_batteryPct < 20) return "LOW_BATTERY";
  return "OK";
}

void SensorManager::readBattery() {
  int raw = analogRead(BATTERY_PIN);
  float pinV = (raw / 4095.0) * 3.3;
  float divRatio = configSystem.getConfig().batteryDivider;
  _batteryV = pinV * divRatio;

  // Detect cells dynamically or default: divider > 6.0 is typically a 3S pack
  int cells = (divRatio > 6.0) ? 3 : 2;
  float minV = cells * 3.2; // 3.2V per cell minimum
  float maxV = cells * 4.2; // 4.2V per cell full charge
  _batteryPct = (int)(((_batteryV - minV) / (maxV - minV)) * 100.0);
  _batteryPct = constrain(_batteryPct, 0, 100);

  if (_batteryPct < 20) {
    LOG_WARN("Low Battery Warning: %.2fV (%d%%)", _batteryV, _batteryPct);
  }
}

static int consecutiveSonarFailures = 0;

long readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 8000);
  if (duration == 0) {
    consecutiveSonarFailures++;
    if (consecutiveSonarFailures >= 10) {
      if (sensorManager.isSonarHealthy()) {
        sensorManager.setSonarHealthy(false);
        LOG_WARN("HC-SR04 ultrasonic sensor reporting 0us duration (disconnected or out-of-range)");
      }
    }
    return -1;
  }
  
  consecutiveSonarFailures = 0;
  sensorManager.setSonarHealthy(true);
  return duration * 0.034 / 2;
}
