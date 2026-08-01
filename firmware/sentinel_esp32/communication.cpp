#include "communication.h"
#include "config.h"
#include "logging.h"
#include "commands.h"
#include "sensors.h"

WiFiClient espClient;
PubSubClient mqtt(espClient);

bool wifiConnected = false;
bool mqttConnected = false;

char TOPIC_TELEMETRY[64];
char TOPIC_STATUS[64];
char TOPIC_COMMANDS[64];
char TOPIC_ACK[64];

unsigned long wifiConnCycles = 0;
unsigned long mqttConnCycles = 0;

static unsigned long lastWifiCheck = 0;
static const unsigned long WIFI_CHECK_MS = 10000;

static unsigned long lastMqttAttempt = 0;
static unsigned long mqttReconnectDelay = 1000;
static const unsigned long MQTT_RECONNECT_MAX = 30000;

void initCommunication() {
  SentinelConfig& cfg = configSystem.getConfig();
  
  snprintf(TOPIC_TELEMETRY, sizeof(TOPIC_TELEMETRY), "sentinel/sensors/%s", cfg.zoneId);
  snprintf(TOPIC_STATUS, sizeof(TOPIC_STATUS), "sentinel/status/%s", cfg.zoneId);
  snprintf(TOPIC_COMMANDS, sizeof(TOPIC_COMMANDS), "sentinel/commands/%s", cfg.zoneId);
  snprintf(TOPIC_ACK, sizeof(TOPIC_ACK), "sentinel/ack/%s", cfg.zoneId);

  mqtt.setServer(cfg.mqttServer, cfg.mqttPort);
  mqtt.setCallback(mqttCallback);
  mqtt.setKeepAlive(15);
  mqtt.setBufferSize(512);

  setupWiFi();
  if (wifiConnected) {
    connectMQTT();
  }
}

void setupWiFi() {
  SentinelConfig& cfg = configSystem.getConfig();
  LOG_INFO("Connecting to WiFi SSID: %s", cfg.wifiSSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(cfg.wifiSSID, cfg.wifiPass);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 10) {
    delay(500);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    wifiConnCycles++;
    LOG_INFO("WiFi connected. IP: %s, RSSI: %d dBm", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    wifiConnected = false;
    LOG_WARN("WiFi connection timeout. Entering non-blocking background connection mode.");
  }
}

bool connectMQTT() {
  if (!wifiConnected || WiFi.status() != WL_CONNECTED) return false;

  SentinelConfig& cfg = configSystem.getConfig();
  String clientId = "sentinel-esp32-";
  clientId += cfg.zoneId;

  char lwt_topic[64];
  snprintf(lwt_topic, sizeof(lwt_topic), "sentinel/status/%s", cfg.zoneId);
  char lwt_msg[128];
  snprintf(lwt_msg, sizeof(lwt_msg), "{\"zone\":\"%s\",\"online\":false,\"battery_pct\":%d,\"fw_ver\":\"%s\"}", 
           cfg.zoneId, sensorManager.getBatteryPercentage(), SENTINEL_FW_VERSION);

  bool connected;
  if (strlen(MQTT_USER) > 0) {
    connected = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD,
                             lwt_topic, 1, true, lwt_msg);
  } else {
    connected = mqtt.connect(clientId.c_str(),
                             lwt_topic, 1, true, lwt_msg);
  }

  if (connected) {
    mqttConnected = true;
    mqttConnCycles++;
    mqttReconnectDelay = 1000;

    LOG_INFO("MQTT broker connected: %s:%d", cfg.mqttServer, cfg.mqttPort);
    mqtt.subscribe(TOPIC_COMMANDS);
    LOG_INFO("Subscribed to command channel: %s", TOPIC_COMMANDS);

    char online_msg[256];
    snprintf(online_msg, sizeof(online_msg),
      "{\"zone\":\"%s\",\"online\":true,\"ip\":\"%s\",\"rssi\":%d,"
      "\"battery_v\":%.2f,\"battery_pct\":%d,\"fw_ver\":\"%s\",\"health\":\"OK\"}",
      cfg.zoneId, WiFi.localIP().toString().c_str(), WiFi.RSSI(),
      sensorManager.getBatteryVoltage(), sensorManager.getBatteryPercentage(), SENTINEL_FW_VERSION);
    mqtt.publish(lwt_topic, online_msg, true);

    return true;
  } else {
    mqttConnected = false;
    LOG_WARN("MQTT connect failed (rc=%d). Reconnect backoff active.", mqtt.state());
    return false;
  }
}

void updateCommunication() {
  unsigned long now = millis();

  if (now - lastWifiCheck >= WIFI_CHECK_MS) {
    lastWifiCheck = now;
    if (WiFi.status() == WL_CONNECTED) {
      if (!wifiConnected) {
        wifiConnected = true;
        wifiConnCycles++;
        LOG_INFO("WiFi connection re-established. RSSI: %d dBm", WiFi.RSSI());
      }
    } else {
      if (wifiConnected) {
        wifiConnected = false;
        mqttConnected = false;
        LOG_WARN("WiFi connection dropped.");
      }
      WiFi.begin(configSystem.getConfig().wifiSSID, configSystem.getConfig().wifiPass);
    }
  }

  if (wifiConnected && !mqtt.connected()) {
    mqttConnected = false;
    if (now - lastMqttAttempt >= mqttReconnectDelay) {
      lastMqttAttempt = now;
      if (!connectMQTT()) {
        mqttReconnectDelay = min(mqttReconnectDelay * 2, MQTT_RECONNECT_MAX);
      }
    }
  }

  if (mqtt.connected()) {
    mqttConnected = true;
    mqtt.loop();
  } else {
    mqttConnected = false;
  }
}
