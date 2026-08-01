#ifndef SENTINEL_SENSORS_H
#define SENTINEL_SENSORS_H

#include <Arduino.h>
#include "DHT.h"

class SensorManager {
private:
  float _mq2Filtered;
  float _mq7Filtered;
  float _mq135Filtered;
  const float EMA_ALPHA = 0.15; // Smooths ADC jitter, ignores high frequency noise

  unsigned long _lastReadTime;
  const unsigned long READ_INTERVAL_MS = 100;

  float _batteryV;
  int _batteryPct;
  unsigned long _lastBatteryTime;
  const unsigned long BATTERY_INTERVAL_MS = 5000;

  // Sensor health monitoring variables
  bool _dhtHealthy;
  bool _sonarHealthy;

public:
  SensorManager();
  void init();
  void update();
  
  int getMQ2();
  int getMQ7();
  int getMQ135();
  float getBatteryVoltage();
  int getBatteryPercentage();
  bool isDHTHealthy();
  bool isSonarHealthy();
  void setSonarHealthy(bool healthy);
  
  // Health status description
  const char* getHealthStatus();

private:
  void readBattery();
};

extern SensorManager sensorManager;
extern DHT dht;

long readDistanceCM();

#endif // SENTINEL_SENSORS_H
