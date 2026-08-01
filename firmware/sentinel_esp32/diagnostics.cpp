#include "diagnostics.h"
#include "config.h"
#include "logging.h"
#include "sensors.h"
#include "communication.h"
#include "indicators.h"

unsigned int loopHz = 0;
static unsigned long loopCount = 0;
static unsigned long lastHzCheck = 0;

static unsigned long lastSensorRead = 0;
static const unsigned long SENSOR_INTERVAL_MS = 1000;

static unsigned long lastHeartbeat = 0;
static const unsigned long HEARTBEAT_MS = 30000;

static unsigned long ledOffTime = 0;

void initDiagnostics() {
  loopCount = 0;
  lastHzCheck = millis();
  lastSensorRead = millis();
  lastHeartbeat = millis();
}

void updateDiagnostics() {
  unsigned long now = millis();

  loopCount++;
  if (now - lastHzCheck >= 1000) {
    loopHz = loopCount;
    loopCount = 0;
    lastHzCheck = now;
  }

  if (ledOffTime > 0 && now >= ledOffTime) {
    digitalWrite(LED_PIN, LOW);
    ledOffTime = 0;
  }

  if (now - lastSensorRead >= SENSOR_INTERVAL_MS) {
    lastSensorRead = now;

    int mq2 = sensorManager.getMQ2();
    int mq7 = sensorManager.getMQ7();
    int mq135 = sensorManager.getMQ135();

    float temp = dht.readTemperature();
    float hum  = dht.readHumidity();

    long distance = readDistanceCM();
    bool irLeft  = (digitalRead(IR_LEFT_PIN) == LOW);
    bool irRight = (digitalRead(IR_RIGHT_PIN) == LOW);

    SentinelConfig& cfg = configSystem.getConfig();
    bool fireRisk = (mq2 > cfg.mq2Threshold) ||
                    (mq7 > cfg.mq7Threshold) ||
                    (mq135 > cfg.mq135Threshold) ||
                    (!isnan(temp) && temp > cfg.tempThreshold);

    bool obstacle = (distance > 0 && distance < OBSTACLE_CM) || irLeft || irRight;

    indicatorManager.setBuzzerActive(fireRisk);

    int smokePpm = map(mq2, 0, 4095, 0, 1000);
    smokePpm = constrain(smokePpm, 0, 1000);

    char json[380];
    if (isnan(temp) || isnan(hum)) {
      snprintf(json, sizeof(json),
        "{\"zone\":\"%s\",\"temp\":null,\"smoke\":%d,\"hum\":null,"
        "\"blocked\":%s,\"uptime\":%lu,\"rssi\":%d,\"mq7\":%d,\"mq135\":%d,"
        "\"battery_v\":%.2f,\"battery_pct\":%d,\"loop_hz\":%u}",
        cfg.zoneId, smokePpm, obstacle ? "true" : "false",
        now / 1000, wifiConnected ? WiFi.RSSI() : 0, mq7, mq135,
        sensorManager.getBatteryVoltage(), sensorManager.getBatteryPercentage(), loopHz
      );
    } else {
      snprintf(json, sizeof(json),
        "{\"zone\":\"%s\",\"temp\":%.1f,\"smoke\":%d,\"hum\":%.1f,"
        "\"blocked\":%s,\"uptime\":%lu,\"rssi\":%d,\"mq7\":%d,\"mq135\":%d,"
        "\"battery_v\":%.2f,\"battery_pct\":%d,\"loop_hz\":%u}",
        cfg.zoneId, temp, smokePpm, hum, obstacle ? "true" : "false",
        now / 1000, wifiConnected ? WiFi.RSSI() : 0, mq7, mq135,
        sensorManager.getBatteryVoltage(), sensorManager.getBatteryPercentage(), loopHz
      );
    }

    Serial.println(json);

    if (mqtt.connected()) {
      bool published = mqtt.publish(TOPIC_TELEMETRY, json);
      if (!published) {
        LOG_ERROR("MQTT telemetry publish failed.");
      } else {
        if (strcmp(indicatorManager.getPatternName(), "NONE") == 0) {
          digitalWrite(LED_PIN, HIGH);
          ledOffTime = now + 20;
        }
      }
    }
  }

  if (now - lastHeartbeat >= HEARTBEAT_MS) {
    lastHeartbeat = now;

    SentinelConfig& cfg = configSystem.getConfig();

    if (mqtt.connected()) {
      char status_json[320];
      snprintf(status_json, sizeof(status_json),
        "{\"zone\":\"%s\",\"online\":true,\"ip\":\"%s\","
        "\"rssi\":%d,\"uptime\":%lu,\"free_heap\":%u,\"buzzer\":%s,"
        "\"battery_v\":%.2f,\"battery_pct\":%d,\"loop_hz\":%u,"
        "\"wifi_cycles\":%lu,\"mqtt_cycles\":%lu,\"fw_ver\":\"%s\",\"health\":\"%s\"}",
        cfg.zoneId, WiFi.localIP().toString().c_str(), WiFi.RSSI(),
        now / 1000, ESP.getFreeHeap(), indicatorManager.isBuzzerActive() ? "true" : "false",
        sensorManager.getBatteryVoltage(), sensorManager.getBatteryPercentage(), loopHz,
        wifiConnCycles, mqttConnCycles, SENTINEL_FW_VERSION, sensorManager.getHealthStatus()
      );
      mqtt.publish(TOPIC_STATUS, status_json, true);
    }

    LOG_INFO("Heartbeat report: WiFi=%s MQTT=%s heap=%u RSSI=%d LoopHz=%u Health=%s",
      wifiConnected ? "OK" : "DISCONNECTED",
      mqtt.connected() ? "OK" : "DISCONNECTED",
      ESP.getFreeHeap(),
      wifiConnected ? WiFi.RSSI() : 0,
      loopHz,
      sensorManager.getHealthStatus()
    );
  }
}
