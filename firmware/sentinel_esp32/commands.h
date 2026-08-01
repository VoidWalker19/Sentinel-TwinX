#ifndef SENTINEL_COMMANDS_H
#define SENTINEL_COMMANDS_H

#include <Arduino.h>

void mqttCallback(char* topic, byte* payload, unsigned int length);
void handleSerialCommands();
void sendAcknowledgement(const char* cmd, const char* status, const char* msg);

String extractJsonValue(const String& json, const String& key);

#endif // SENTINEL_COMMANDS_H
