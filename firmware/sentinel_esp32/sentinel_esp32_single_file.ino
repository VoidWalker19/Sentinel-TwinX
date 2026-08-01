/*
 * ==========================================================================
 *  SENTINEL TWIN X  -  ESP32 Microcontroller Single-File Firmware
 *  Full telemetry, multi-sensor fusion, and MQTT remote motor control.
 *
 *  Hardware Pinout:
 *    - MQ2 (Smoke/Gas)  : Pin 34 (Analog)
 *    - MQ7 (CO Gas)     : Pin 35 (Analog)
 *    - MQ135 (Air Qual) : Pin 32 (Analog)
 *    - DHT11 (Temp/Hum) : Pin 4
 *    - HC-SR04 Trig     : Pin 5
 *    - HC-SR04 Echo     : Pin 18
 *    - Buzzer           : Pin 23
 *    - L298N Motors     : ENA=25, IN1=26, IN2=27, ENB=13, IN3=14, IN4=12
 *
 *  Board: ESP32 Dev Module
 *  Dependencies: WiFi.h, PubSubClient.h, DHT.h
 * ==========================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include <math.h>

const char* ssid = "ROOM-02";
const char* password = "synchack26";
const char* mqtt_server = "10.10.0.213";

WiFiClient espClient;
PubSubClient client(espClient);

// Sensor Pins
#define MQ2_PIN 34
#define MQ7_PIN 35
#define MQ135_PIN 32

#define DHT_PIN 4
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

#define TRIG_PIN 5
#define ECHO_PIN 18

#define BUZZER_PIN 23

// Motor Driver Pins (L298N)
#define ENA 25
#define IN1 26
#define IN2 27

#define ENB 13
#define IN3 14
#define IN4 12

#define TEMP_THRESHOLD 45.0

#define MQ2_MAX_PPM 1000.0
#define MQ7_MAX_PPM 100.0
#define MQ135_MAX_PPM 2000.0

#define MQ2_ALERT_PERCENT 70
#define MQ7_ALERT_PERCENT 70
#define MQ135_ALERT_PERCENT 70

#define OBSTACLE_CM 25

int motorSpeed = 200;

float MQ2_R0 = 2.73;
float MQ7_R0 = 1.35;
float MQ135_R0 = 2.25;

// Function Declarations
long readDistanceCM();
void buzzerAlert();
void moveForward();
void moveBackward();
void turnLeft();
void turnRight();
void stopMotors();

float calculateRs(int rawValue) {
  if (rawValue <= 0) return 999999;
  float voltage = rawValue * 3.3 / 4095.0;
  if (voltage >= 3.29) return 999999;
  float RL = 10.0;
  return RL * (3.3 - voltage) / voltage;
}

float calculateMQ2PPM(float rs) {
  float ratio = rs / MQ2_R0;
  float ppm = 1000.0 * pow(ratio, -1.5);
  return constrain(ppm, 0, MQ2_MAX_PPM);
}

float calculateMQ7PPM(float rs) {
  float ratio = rs / MQ7_R0;
  float ppm = 100.0 * pow(ratio, -1.5);
  return constrain(ppm, 0, MQ7_MAX_PPM);
}

float calculateMQ135PPM(float rs) {
  float ratio = rs / MQ135_R0;
  float ppm = 400.0 * pow(ratio, -2.3);
  return constrain(ppm, 0, MQ135_MAX_PPM);
}

int ppmToPercentage(float ppm, float maxPPM) {
  int percentage = (ppm / maxPPM) * 100;
  return constrain(percentage, 0, 100);
}

// MQTT Callback Handler for UI Remote Commands
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("Command received [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  if (message.indexOf("Forward") >= 0 || message.indexOf("forward") >= 0) {
    moveForward();
  } else if (message.indexOf("Backward") >= 0 || message.indexOf("backward") >= 0) {
    moveBackward();
  } else if (message.indexOf("Left") >= 0 || message.indexOf("left") >= 0) {
    turnLeft();
  } else if (message.indexOf("Right") >= 0 || message.indexOf("right") >= 0) {
    turnRight();
  } else if (message.indexOf("Stop") >= 0 || message.indexOf("stop") >= 0) {
    stopMotors();
  } else if (message.indexOf("Return Home") >= 0) {
    stopMotors();
  }
}

void setupWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi Connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting MQTT...");
    if (client.connect("SentinelTwinESP32")) {
      Serial.println("Connected to Sentinel Twin Broker");
      // Subscribe to command channels from Command Center UI
      client.subscribe("sentinel/commands");
      client.subscribe("sentinel/commands/#");
      client.subscribe("sentinel/rover/cmd");
    } else {
      Serial.print("Failed: ");
      Serial.println(client.state());
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  setupWiFi();

  client.setServer(mqtt_server, 1883);
  client.setCallback(mqttCallback);

  pinMode(MQ2_PIN, INPUT);
  pinMode(MQ7_PIN, INPUT);
  pinMode(MQ135_PIN, INPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin();

  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  stopMotors();

  Serial.println("Sentinel Twin ESP32 Node Initialized");
  delay(2000);
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  int mq2Raw = analogRead(MQ2_PIN);
  int mq7Raw = analogRead(MQ7_PIN);
  int mq135Raw = analogRead(MQ135_PIN);

  float mq2Rs = calculateRs(mq2Raw);
  float mq7Rs = calculateRs(mq7Raw);
  float mq135Rs = calculateRs(mq135Raw);

  float mq2PPM = calculateMQ2PPM(mq2Rs);
  float mq7PPM = calculateMQ7PPM(mq7Rs);
  float mq135PPM = calculateMQ135PPM(mq135Rs);

  int mq2Percentage = ppmToPercentage(mq2PPM, MQ2_MAX_PPM);
  int mq7Percentage = ppmToPercentage(mq7PPM, MQ7_MAX_PPM);
  int mq135Percentage = ppmToPercentage(mq135PPM, MQ135_MAX_PPM);

  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp)) temp = -1;
  if (isnan(hum)) hum = -1;

  long distance = readDistanceCM();

  bool mq2Alert = mq2Percentage > MQ2_ALERT_PERCENT;
  bool mq7Alert = mq7Percentage > MQ7_ALERT_PERCENT;
  bool mq135Alert = mq135Percentage > MQ135_ALERT_PERCENT;
  bool tempAlert = temp > TEMP_THRESHOLD;

  bool fireRisk = mq2Alert || mq7Alert || mq135Alert || tempAlert;
  bool obstacle = distance > 0 && distance < OBSTACLE_CM;

  if (fireRisk) {
    buzzerAlert();
  } else {
    digitalWrite(BUZZER_PIN, LOW);
  }

  if (obstacle) {
    stopMotors();
    delay(200);
    moveBackward();
    delay(400);
    turnRight();
    delay(400);
    stopMotors();
  }

  // Build JSON Payload for Sentinel Twin Backend
  String payload = "{";
  payload += "\"zone\":\"chem_lab\",";
  payload += "\"mq2\":" + String(mq2Percentage) + ",";
  payload += "\"mq7\":" + String(mq7Percentage) + ",";
  payload += "\"mq135\":" + String(mq135Percentage) + ",";
  payload += "\"mq2_ppm\":" + String(mq2PPM, 2) + ",";
  payload += "\"mq7_ppm\":" + String(mq7PPM, 2) + ",";
  payload += "\"mq135_ppm\":" + String(mq135PPM, 2) + ",";
  payload += "\"temp\":" + String(temp, 1) + ",";
  payload += "\"hum\":" + String(hum, 1) + ",";
  payload += "\"distance\":" + String(distance) + ",";
  payload += "\"fire\":" + String(fireRisk ? "true" : "false") + ",";
  payload += "\"obstacle\":" + String(obstacle ? "true" : "false") + ",";
  payload += "\"blocked\":" + String(obstacle ? "true" : "false");
  payload += "}";

  bool published = client.publish("sentinel/sensors", payload.c_str());

  // Also publish to status topic for health monitoring
  String statusPayload = "{\"online\":true,\"ip\":\"" + WiFi.localIP().toString() + "\",\"rssi\":" + String(WiFi.RSSI()) + "}";
  client.publish("sentinel/status/chem_lab", statusPayload.c_str());

  Serial.println("==============================");
  Serial.print("MQ2        : "); Serial.print(mq2Percentage); Serial.print(" % | "); Serial.print(mq2PPM); Serial.println(" ppm");
  Serial.print("MQ7 CO     : "); Serial.print(mq7Percentage); Serial.print(" % | "); Serial.print(mq7PPM); Serial.println(" ppm");
  Serial.print("MQ135      : "); Serial.print(mq135Percentage); Serial.print(" % | "); Serial.print(mq135PPM); Serial.println(" ppm");
  Serial.print("Temperature: "); Serial.print(temp); Serial.println(" C");
  Serial.print("Humidity   : "); Serial.print(hum); Serial.println(" %");
  Serial.print("Distance   : "); Serial.print(distance); Serial.println(" cm");
  Serial.print("Fire Risk  : "); Serial.println(fireRisk ? "YES" : "NO");
  Serial.print("Obstacle   : "); Serial.println(obstacle ? "YES" : "NO");
  Serial.print("MQTT Publish: "); Serial.println(published ? "SUCCESS" : "FAILED");
  Serial.println("==============================");

  delay(1000);
}

long readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

void buzzerAlert() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
  delay(100);
}

void moveForward() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  analogWrite(ENA, motorSpeed); analogWrite(ENB, motorSpeed);
}

void moveBackward() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  analogWrite(ENA, motorSpeed); analogWrite(ENB, motorSpeed);
}

void turnLeft() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  analogWrite(ENA, motorSpeed); analogWrite(ENB, motorSpeed);
}

void turnRight() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  analogWrite(ENA, motorSpeed); analogWrite(ENB, motorSpeed);
}

void stopMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  analogWrite(ENA, 0); analogWrite(ENB, 0);
}
