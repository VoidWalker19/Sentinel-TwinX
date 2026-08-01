# Sentinel Twin X — ESP32 Modular Firmware

This folder contains the upgraded modular C++ firmware for the Sentinel Twin X autonomous patrol rover and stationary sensor nodes.

## Architecture

The firmware is split into clean, modular components:
1. `sentinel_esp32.ino`: Main sketch orchestrating initialization and non-blocking scheduling loops.
2. `config.h` / `config.cpp`: Static hardware pin layouts and runtime configuration loaded/saved via the ESP32 `Preferences` API.
3. `logging.h` / `logging.cpp`: Elapsed-boot-time stamped serial logger with log level severities (`INFO`, `WARN`, `ERROR`, `DEBUG`).
4. `sensors.h` / `sensors.cpp`: Handles ADC sensor polling with Exponential Moving Average (EMA) filters, non-blocking HC-SR04 sonar pinging, and digital DHT temperature/humidity sensors.
5. `motors.h` / `motors.cpp`: Integrates soft-start ramp rate protection for the L298N H-bridge driver.
6. `indicators.h` / `indicators.cpp`: Completely non-blocking LED and Buzzer beeping state machines.
7. `communication.h` / `communication.cpp`: Non-blocking WiFi link monitoring and exponential backoff MQTT brokers linkage.
8. `commands.h` / `commands.cpp`: CLI serial parser and JSON command acknowledgements.
9. `diagnostics.h` / `diagnostics.cpp`: Tracks loop frequency (Hz), system heap, dropouts, and publishes periodic telemetry (1Hz) and heartbeats (30s).

---

## Pin Assignments

Pin mappings are preserved exactly as hardware assignments:

| Peripheral | ESP32 GPIO | Description |
|---|---|---|
| MQ-2 | GPIO34 | Smoke / Flammable Gas (ADC1) |
| MQ-7 | GPIO35 | Carbon Monoxide (ADC1) |
| MQ-135 | GPIO32 | Air Quality Index (ADC1) |
| Battery Sense | GPIO36 | Pack Voltage Divider (ADC1) |
| DHT11 / DHT22 | GPIO4 | Digital Temperature & Humidity |
| HC-SR04 Trigger | GPIO5 | Ultrasonic Trigger Output |
| HC-SR04 Echo | GPIO18 | Ultrasonic Echo Input (protected) |
| IR Obstacle Left | GPIO19 | Digital Left Collision Detector |
| IR Obstacle Right | GPIO21 | Digital Right Collision Detector |
| Buzzer Output | GPIO23 | Active Alarm Buzzer |
| Status Onboard LED | GPIO2 | System Indicator LED |
| L298N ENA | GPIO25 | Left Motor PWM Speed |
| L298N IN1 | GPIO26 | Left Motor Forward Polarity |
| L298N IN2 | GPIO27 | Left Motor Reverse Polarity |
| L298N ENB | GPIO13 | Right Motor PWM Speed |
| L298N IN3 | GPIO14 | Right Motor Forward Polarity |
| L298N IN4 | GPIO12 | Right Motor Reverse Polarity (strapping pin) |

---

## Dynamic Configuration & Commands

### Serial Console (115200 baud)
The firmware provides a CLI interface on the Serial monitor:
- `GET`: Prints the active configuration.
- `SET <key>=<value>`: Modifies a configuration parameter. Examples:
  - `SET wifi_ssid=MySSID`
  - `SET motor_speed=200`
  - `SET zone_id=chem_lab`
- `RESET_CONFIG`: Wipes Preferences and restores compiled defaults.
- `RESTART`: Reboots the ESP32 module.

### MQTT Commands
Subscribed to: `sentinel/commands/<zoneId>`
Commands contain a `"cmd"` or `"type"` string:
- `{"cmd": "buzzer_on"}`: Forces buzzer alarm active.
- `{"cmd": "buzzer_off"}`: Deactivates buzzer alarm.
- `{"cmd": "identify"}`: Blinks status LED 15 times (non-blocking).
- `{"cmd": "rover_dispatched"}`: Drives buzzer beep patterns and LED flashes (non-blocking).
- `{"cmd": "set_config", "key": "<key_name>", "value": "<new_value>"}`: Saves a config value dynamically.

### MQTT Acknowledgments
Published to: `sentinel/ack/<zoneId>`
Format:
```json
{
  "zone": "rover",
  "cmd": "buzzer_on",
  "status": "ACK",
  "msg": "Buzzer activated",
  "fw_ver": "2.0.0"
}
```

---

## Compilation Requirements

1. **Hardware Core:** Install `ESP32 Dev Module` support in the Arduino IDE boards manager.
2. **Required Libraries:**
   - `PubSubClient` (by Nick O'Leary)
   - `DHT sensor library` (by Adafruit)
   - `Adafruit Unified Sensor` (by Adafruit)
