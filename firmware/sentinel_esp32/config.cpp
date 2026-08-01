#include "config.h"
#include "logging.h"

ConfigSystem configSystem;

void ConfigSystem::init() {
  _prefs.begin("sentinel", false);
  load();
}

SentinelConfig& ConfigSystem::getConfig() {
  return _activeConfig;
}

void ConfigSystem::load() {
  _prefs.getString("wifi_ssid", WIFI_SSID).toCharArray(_activeConfig.wifiSSID, 32);
  _prefs.getString("wifi_pass", WIFI_PASSWORD).toCharArray(_activeConfig.wifiPass, 64);
  _prefs.getString("mqtt_server", MQTT_SERVER).toCharArray(_activeConfig.mqttServer, 64);
  _activeConfig.mqttPort = _prefs.getInt("mqtt_port", MQTT_PORT);
  _activeConfig.motorSpeed = _prefs.getInt("motor_speed", 180);
  _activeConfig.batteryDivider = _prefs.getFloat("bat_divider", 5.545);
  _activeConfig.mq2Threshold = _prefs.getInt("mq2_thresh", MQ2_THRESHOLD);
  _activeConfig.mq7Threshold = _prefs.getInt("mq7_thresh", MQ7_THRESHOLD);
  _activeConfig.mq135Threshold = _prefs.getInt("mq135_thresh", MQ135_THRESHOLD);
  _activeConfig.tempThreshold = _prefs.getFloat("temp_thresh", TEMP_THRESHOLD);
  _prefs.getString("zone_id", DEFAULT_ZONE_ID).toCharArray(_activeConfig.zoneId, 32);
}

void ConfigSystem::save() {
  _prefs.putString("wifi_ssid", _activeConfig.wifiSSID);
  _prefs.putString("wifi_pass", _activeConfig.wifiPass);
  _prefs.putString("mqtt_server", _activeConfig.mqttServer);
  _prefs.putInt("mqtt_port", _activeConfig.mqttPort);
  _prefs.putInt("motor_speed", _activeConfig.motorSpeed);
  _prefs.putFloat("bat_divider", _activeConfig.batteryDivider);
  _prefs.putInt("mq2_thresh", _activeConfig.mq2Threshold);
  _prefs.putInt("mq7_thresh", _activeConfig.mq7Threshold);
  _prefs.putInt("mq135_thresh", _activeConfig.mq135Threshold);
  _prefs.putFloat("temp_thresh", _activeConfig.tempThreshold);
  _prefs.putString("zone_id", _activeConfig.zoneId);
}

void ConfigSystem::printConfig() {
  Serial.println(F("# --- CURRENT CONFIGURATION ---"));
  Serial.printf("# firmware_ver:   %s\n", SENTINEL_FW_VERSION);
  Serial.printf("# wifi_ssid:      %s\n", _activeConfig.wifiSSID);
  Serial.printf("# wifi_pass:      ******\n");
  Serial.printf("# mqtt_server:    %s\n", _activeConfig.mqttServer);
  Serial.printf("# mqtt_port:      %d\n", _activeConfig.mqttPort);
  Serial.printf("# motor_speed:    %d\n", _activeConfig.motorSpeed);
  Serial.printf("# bat_divider:    %.3f\n", _activeConfig.batteryDivider);
  Serial.printf("# mq2_thresh:     %d\n", _activeConfig.mq2Threshold);
  Serial.printf("# mq7_thresh:     %d\n", _activeConfig.mq7Threshold);
  Serial.printf("# mq135_thresh:   %d\n", _activeConfig.mq135Threshold);
  Serial.printf("# temp_thresh:    %.1f\n", _activeConfig.tempThreshold);
  Serial.printf("# zone_id:        %s\n", _activeConfig.zoneId);
  Serial.println(F("# ------------------------------"));

  if (IN4 == 12) {
    LOG_WARN("Strapping Pin Warning: Motor Pin IN4 is assigned to GPIO12. This may cause boot failures if driven HIGH at startup.");
  }
}

bool ConfigSystem::updateValue(const String& key, const String& val) {
  if (key == "wifi_ssid") {
    val.toCharArray(_activeConfig.wifiSSID, 32);
  } else if (key == "wifi_pass") {
    val.toCharArray(_activeConfig.wifiPass, 64);
  } else if (key == "mqtt_server") {
    val.toCharArray(_activeConfig.mqttServer, 64);
  } else if (key == "mqtt_port") {
    _activeConfig.mqttPort = val.toInt();
  } else if (key == "motor_speed") {
    _activeConfig.motorSpeed = constrain(val.toInt(), 0, 255);
  } else if (key == "bat_divider") {
    _activeConfig.batteryDivider = val.toFloat();
  } else if (key == "mq2_thresh") {
    _activeConfig.mq2Threshold = val.toInt();
  } else if (key == "mq7_thresh") {
    _activeConfig.mq7Threshold = val.toInt();
  } else if (key == "mq135_thresh") {
    _activeConfig.mq135Threshold = val.toInt();
  } else if (key == "temp_thresh") {
    _activeConfig.tempThreshold = val.toFloat();
  } else if (key == "zone_id") {
    val.toCharArray(_activeConfig.zoneId, 32);
  } else {
    return false;
  }
  save();
  return true;
}

void ConfigSystem::reset() {
  _prefs.clear();
  load();
  LOG_INFO("Config reset to defaults.");
}
