#ifndef SENTINEL_CONFIG_H
#define SENTINEL_CONFIG_H

#include <Arduino.h>
#include <Preferences.h>

// Firmware version constant
#define SENTINEL_FW_VERSION "2.0.0"

// WiFi/MQTT Defaults
#define WIFI_SSID       "ROOM-02"        // Fallback default WiFi SSID
#define WIFI_PASSWORD   "synchack26"       // Fallback default WiFi Password
#define MQTT_SERVER     "10.10.0.213"    // Fallback default MQTT Broker IP
#define MQTT_PORT       1883             // Default Mosquitto port
#define MQTT_USER       ""               // Default username (if auth is off)
#define MQTT_PASSWORD   ""               // Default password (if auth is off)
#define DEFAULT_ZONE_ID "rover"          // Fallback default Zone ID

// Pin Assignments (preserved exactly)
#define MQ2_PIN       34   // Smoke / flammable gas (ADC1)
#define MQ7_PIN       35   // Carbon monoxide (ADC1)
#define MQ135_PIN     32   // Air quality (ADC1)
#define BATTERY_PIN   36   // Battery sense (ADC1) (Default 100k/22k divider)
#define DHT_PIN       4    // DHT11 temperature & humidity (digital)
#define TRIG_PIN      5    // Ultrasonic HC-SR04 Trigger
#define ECHO_PIN      18   // Ultrasonic HC-SR04 Echo (1k/2k divider protected)
#define IR_LEFT_PIN   19   // Digital infrared obstacle left
#define IR_RIGHT_PIN  21   // Digital infrared obstacle right
#define BUZZER_PIN    23   // Alarm sound output
#define LED_PIN       2    // Onboard status LED

// L298N Motor Driver Pins
#define ENA           25   // PWM speed left side
#define IN1           26   // Left forward
#define IN2           27   // Left backward
#define ENB           13   // PWM speed right side
#define IN3           14   // Right forward
#define IN4           12   // Right backward (⚠️ Strapping Pin warning)

// Safety thresholds defaults
#define MQ2_THRESHOLD    1500   // raw ADC threshold
#define MQ7_THRESHOLD    1500
#define MQ135_THRESHOLD  1500
#define TEMP_THRESHOLD   45.0   // deg C
#define OBSTACLE_CM      20     // Collision avoidance range trigger

// Configuration structure
struct SentinelConfig {
  char wifiSSID[32];
  char wifiPass[64];
  char mqttServer[64];
  int mqttPort;
  int motorSpeed;
  float batteryDivider;
  int mq2Threshold;
  int mq7Threshold;
  int mq135Threshold;
  float tempThreshold;
  char zoneId[32];
};

class ConfigSystem {
private:
  Preferences _prefs;
  SentinelConfig _activeConfig;

public:
  void init();
  SentinelConfig& getConfig();
  void load();
  void save();
  void printConfig();
  bool updateValue(const String& key, const String& val);
  void reset();
};

extern ConfigSystem configSystem;

#endif // SENTINEL_CONFIG_H
