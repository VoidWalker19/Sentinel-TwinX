#ifndef SENTINEL_COMMUNICATION_H
#define SENTINEL_COMMUNICATION_H

#include <WiFi.h>
#include <PubSubClient.h>

extern WiFiClient espClient;
extern PubSubClient mqtt;

extern bool wifiConnected;
extern bool mqttConnected;

extern char TOPIC_TELEMETRY[64];
extern char TOPIC_STATUS[64];
extern char TOPIC_COMMANDS[64];
extern char TOPIC_ACK[64];

// Diagnostic connection counters
extern unsigned long wifiConnCycles;
extern unsigned long mqttConnCycles;

void initCommunication();
void updateCommunication();
void setupWiFi();
bool connectMQTT();

#endif // SENTINEL_COMMUNICATION_H
