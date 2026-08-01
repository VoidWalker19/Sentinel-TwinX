#include "commands.h"
#include "config.h"
#include "logging.h"
#include "communication.h"
#include "indicators.h"

String extractJsonValue(const String& json, const String& key) {
  String searchKey = "\"" + key + "\"";
  int keyIdx = json.indexOf(searchKey);
  if (keyIdx == -1) return "";
  
  int colonIdx = json.indexOf(':', keyIdx + searchKey.length());
  if (colonIdx == -1) return "";
  
  int valStart = colonIdx + 1;
  while (valStart < json.length() && (json[valStart] == ' ' || json[valStart] == '\t' || json[valStart] == '\r' || json[valStart] == '\n')) {
    valStart++;
  }
  
  if (valStart >= json.length()) return "";
  
  if (json[valStart] == '\"') {
    int valEnd = json.indexOf('\"', valStart + 1);
    if (valEnd == -1) return "";
    return json.substring(valStart + 1, valEnd);
  } else {
    int valEnd = valStart;
    while (valEnd < json.length() && json[valEnd] != ',' && json[valEnd] != '}' && json[valEnd] != ']' && json[valEnd] != ' ' && json[valEnd] != '\r' && json[valEnd] != '\n') {
      valEnd++;
    }
    return json.substring(valStart, valEnd);
  }
}

void sendAcknowledgement(const char* cmd, const char* status, const char* msg) {
  if (!mqtt.connected()) {
    LOG_INFO("Ack (Serial only) - cmd: %s, status: %s, msg: %s", cmd, status, msg);
    return;
  }
  
  char ackPayload[256];
  snprintf(ackPayload, sizeof(ackPayload),
    "{\"zone\":\"%s\",\"cmd\":\"%s\",\"status\":\"%s\",\"msg\":\"%s\",\"fw_ver\":\"%s\"}",
    configSystem.getConfig().zoneId, cmd, status, msg, SENTINEL_FW_VERSION);
    
  bool published = mqtt.publish(TOPIC_ACK, ackPayload);
  if (published) {
    LOG_INFO("Published ACK to %s: %s", TOPIC_ACK, ackPayload);
  } else {
    LOG_ERROR("Failed to publish ACK to %s", TOPIC_ACK);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  char msg[256];
  int len = min((unsigned int)255, length);
  memcpy(msg, payload, len);
  msg[len] = '\0';

  LOG_INFO("MQTT command on [%s]: %s", topic, msg);
  String payloadStr = String(msg);
  
  String cmd = extractJsonValue(payloadStr, "cmd");
  if (cmd == "") {
    cmd = extractJsonValue(payloadStr, "type");
  }
  
  if (cmd == "") {
    if (payloadStr.indexOf("\"buzzer_on\"") >= 0) cmd = "buzzer_on";
    else if (payloadStr.indexOf("\"buzzer_off\"") >= 0) cmd = "buzzer_off";
    else if (payloadStr.indexOf("\"identify\"") >= 0) cmd = "identify";
    else if (payloadStr.indexOf("\"rover_dispatched\"") >= 0) cmd = "rover_dispatched";
    else if (payloadStr.indexOf("\"set_config\"") >= 0) cmd = "set_config";
  }

  if (cmd == "buzzer_on") {
    indicatorManager.setBuzzerActive(true);
    sendAcknowledgement("buzzer_on", "ACK", "Buzzer activated");
  }
  else if (cmd == "buzzer_off") {
    indicatorManager.setBuzzerActive(false);
    sendAcknowledgement("buzzer_off", "ACK", "Buzzer deactivated");
  }
  else if (cmd == "identify") {
    indicatorManager.triggerIdentify();
    sendAcknowledgement("identify", "ACK", "Identify pattern started");
  }
  else if (cmd == "rover_dispatched") {
    indicatorManager.triggerDispatch();
    sendAcknowledgement("rover_dispatched", "ACK", "Rover dispatch sound and LED pattern active");
  }
  else if (cmd == "set_config") {
    String key = extractJsonValue(payloadStr, "key");
    String val = extractJsonValue(payloadStr, "value");
    
    if (key == "" || val == "") {
      int keyIdx = payloadStr.indexOf("\"key\":\"");
      int valIdx = payloadStr.indexOf("\"value\":\"");
      if (keyIdx >= 0 && valIdx >= 0) {
        int keyEnd = payloadStr.indexOf("\"", keyIdx + 7);
        int valEnd = payloadStr.indexOf("\"", valIdx + 9);
        if (keyEnd > keyIdx && valEnd > valIdx) {
          key = payloadStr.substring(keyIdx + 7, keyEnd);
          val = payloadStr.substring(valIdx + 9, valEnd);
        }
      }
    }

    if (key != "" && val != "") {
      if (configSystem.updateValue(key, val)) {
        char responseMsg[128];
        snprintf(responseMsg, sizeof(responseMsg), "Config saved: %s = %s", key.c_str(), val.c_str());
        sendAcknowledgement("set_config", "ACK", responseMsg);
        
        if (key == "zone_id") {
          initCommunication();
        }
      } else {
        char responseMsg[128];
        snprintf(responseMsg, sizeof(responseMsg), "Failed to save: invalid key '%s'", key.c_str());
        sendAcknowledgement("set_config", "ERROR", responseMsg);
      }
    } else {
      sendAcknowledgement("set_config", "ERROR", "Missing key or value fields");
    }
  } else {
    sendAcknowledgement(cmd.c_str(), "ERROR", "Unknown command");
  }
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("SET ")) {
      int eq = cmd.indexOf('=');
      if (eq > 4) {
        String key = cmd.substring(4, eq);
        String val = cmd.substring(eq + 1);
        key.trim(); val.trim();
        if (configSystem.updateValue(key, val)) {
          LOG_INFO("Config parameter saved over Serial: %s = %s", key.c_str(), val.c_str());
          configSystem.printConfig();
          
          if (key == "zone_id") {
            initCommunication();
          }
        } else {
          LOG_WARN("Serial Config update failed: Invalid key '%s'", key.c_str());
        }
      }
    } else if (cmd == "GET") {
      configSystem.printConfig();
    } else if (cmd == "RESET_CONFIG") {
      configSystem.reset();
      LOG_INFO("Config cleared. Please issue 'RESTART'.");
    } else if (cmd == "RESTART") {
      LOG_INFO("Rebooting ESP32 module.");
      delay(500);
      ESP.restart();
    } else {
      LOG_INFO("Available serial console commands: GET, SET key=val, RESET_CONFIG, RESTART");
    }
  }
}
