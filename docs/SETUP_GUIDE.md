# Sentinel Twin — MQTT Setup Guide
## ESP32 + Raspberry Pi 3 Integration

This guide walks you through connecting real ESP32 sensor hardware to the
Sentinel Twin dashboard via MQTT, using a Raspberry Pi 3 as the message broker.

---

## Architecture

```
┌─────────────────┐     WiFi/MQTT      ┌─────────────────┐     WiFi/MQTT     ┌─────────────────┐
│   ESP32 Board   │ ─────────────────► │  Raspberry Pi 3 │ ◄───────────────── │  Your PC        │
│                 │  Publishes sensor   │  (Mosquitto)    │  Server subscribes │  (Dashboard)    │
│  DHT22 + MQ-2   │  data every 1s     │  MQTT Broker    │  to sensor topics  │  FastAPI + UI   │
│  + HC-SR04      │                    │  Port 1883      │                    │  Port 8000      │
└─────────────────┘                    └─────────────────┘                    └─────────────────┘
```

---

## Prerequisites

| Item | Purpose |
|------|---------|
| ESP32 Dev Module | Reads sensors, publishes over MQTT |
| Raspberry Pi 3 (any model) | Runs Mosquitto MQTT broker |
| DHT22 sensor | Temperature + humidity |
| MQ-2 sensor | Smoke / gas detection |
| HC-SR04 ultrasonic | Path blockage detection |
| Breadboard + jumper wires | Connections |
| 4.7kΩ resistor | DHT22 pull-up |
| 1kΩ + 2kΩ resistors | HC-SR04 ECHO voltage divider |
| 10kΩ + 20kΩ resistors | MQ-2 AOUT voltage divider |
| USB cable for ESP32 | Flashing firmware |
| WiFi network (2.4 GHz) | ESP32 only supports 2.4 GHz |

---

## Step 1: Set Up the Raspberry Pi Broker

### Option A: Automated (Recommended)

Copy the `mqtt_package/raspberry_pi_setup/` folder to your Raspberry Pi and run:

```bash
# Copy files to Pi (from your PC)
scp -r mqtt_package/raspberry_pi_setup/ pi@<PI_IP>:~/sentinel_mqtt/

# SSH into the Pi
ssh pi@<PI_IP>

# Run the setup script
cd ~/sentinel_mqtt
sudo bash setup_broker.sh
```

The script will:
1. Install Mosquitto broker + clients
2. Copy the Sentinel Twin config
3. Enable and start the service
4. Print your Pi's IP address (you'll need this)

### Option B: Manual

```bash
# On the Raspberry Pi:
sudo apt update
sudo apt install -y mosquitto mosquitto-clients

# Create config
sudo nano /etc/mosquitto/conf.d/sentinel.conf
```

Paste this config:
```
listener 1883
protocol mqtt
allow_anonymous true
persistence true
persistence_location /var/lib/mosquitto/
```

Then restart:
```bash
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
```

### Verify the Broker

```bash
# Note your Pi's IP
hostname -I
# Example output: 192.168.1.42

# Test pub/sub in two terminals:
# Terminal 1 (subscribe):
mosquitto_sub -t "sentinel/#" -v

# Terminal 2 (publish):
mosquitto_pub -t "sentinel/test" -m '{"test":"hello"}'
```

You should see the message appear in Terminal 1.

---

## Step 2: Wire the ESP32 Sensors

> ⚠️ **CRITICAL: Read the voltage divider warnings below. Connecting 5V signals directly to the ESP32 WILL damage it.**

### Wiring Diagram

```
ESP32 Dev Module
┌─────────────────────┐
│                     │
│  GPIO4  ◄──────────── DHT22 DATA (+ 4.7kΩ pull-up to 3.3V)
│  GPIO34 ◄──────────── MQ-2 AOUT (through 10k/20k divider!)
│  GPIO5  ──────────►── HC-SR04 TRIG
│  GPIO18 ◄──────────── HC-SR04 ECHO (through 1k/2k divider!)
│  GPIO23 ──────────►── Buzzer + (optional)
│  GPIO2  ──────────►── Onboard LED (status)
│                     │
│  3.3V   ──────────►── DHT22 VCC
│  5V/VIN ──────────►── MQ-2 VCC, HC-SR04 VCC
│  GND    ──────────►── All sensor GNDs (common ground!)
└─────────────────────┘
```

### Required Voltage Dividers

**HC-SR04 ECHO → GPIO18** (5V → 3.3V):
```
HC-SR04 ECHO ──── R1 (1kΩ) ────┬──── GPIO18
                                │
                              R2 (2kΩ)
                                │
                               GND
```

**MQ-2 AOUT → GPIO34** (5V → 3.3V):
```
MQ-2 AOUT ──── R1 (10kΩ) ────┬──── GPIO34
                              │
                            R2 (20kΩ)
                              │
                             GND
```

---

## Step 3: Flash the ESP32 Firmware

### Install Arduino IDE

1. Download [Arduino IDE 2.x](https://www.arduino.cc/en/software)
2. Go to **Boards Manager** → Search "esp32" → Install **esp32 by Espressif**

### Install Libraries

In **Library Manager** (Ctrl+Shift+I), install:
- `DHT sensor library` (by Adafruit)
- `Adafruit Unified Sensor`
- `PubSubClient` (by Nick O'Leary)

### Configure Credentials and Zone ID

Open `mqtt_package/esp32_firmware/esp32_firmware.ino` and update the WiFi credentials, MQTT server details, and the zone ID directly inside the file:

```cpp
// ─── WiFi & MQTT Credentials ────────────────────────────────────────────────
#define WIFI_SSID       "YourWiFiSSID"
#define WIFI_PASSWORD   "YourWiFiPassword"
#define MQTT_SERVER     "192.168.1.42"  // Your Pi's IP from Step 1
#define MQTT_PORT       1883

// ─── Zone Identity ──────────────────────────────────────────────────────────
const char* ZONE_ID = "chem_lab";  // Change to your zone
```

Valid zone IDs:
`chem_lab`, `corridor`, `server`, `classroom_a`, `classroom_b`,
`reception`, `office`, `storage`, `exit_a`, `exit_b`

### Flash

1. Board: **ESP32 Dev Module**
2. Port: Select your ESP32's COM port
3. Upload Speed: **921600**
4. Click **Upload**

### Verify on Serial Monitor

Open Serial Monitor at **115200 baud**. You should see:

```
# Sentinel Twin v2 — ESP32 Sensor Node (MQTT Mode)
# Zone: chem_lab
# Warming up MQ-2 sensor (20s)...
# WiFi connected! IP: 192.168.1.50  RSSI: -45 dBm
# MQTT connected to 192.168.1.42:1883
# Subscribed to: sentinel/commands/chem_lab
# Ready. Publishing sensor data...
{"zone":"chem_lab","temp":26.3,"smoke":42,"hum":58.1,"blocked":false,"uptime":21,"rssi":-45}
```

### Verify on the Pi

On the Raspberry Pi:
```bash
mosquitto_sub -t "sentinel/sensors/#" -v
```

You should see JSON messages arriving every second.

---

## Step 4: Configure the Sentinel Twin Server

### Install the MQTT dependency

```bash
cd "Sentinel Twin"
pip install paho-mqtt>=2.0.0
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

### Update .env

Edit `.env` in the Sentinel Twin folder:

```env
SENTINEL_MODE=mqtt
MQTT_BROKER=192.168.1.42    # Your Pi's IP
MQTT_PORT=1883
MQTT_USER=                  # Leave empty for anonymous
MQTT_PASS=
```

### Start the Server

```bash
# Option 1: Using .env config
python run.py --mqtt

# Option 2: Specify broker on command line
python run.py --mqtt --broker 192.168.1.42

# Option 3: Run on a custom port
python run.py --mqtt --broker 192.168.1.42 --web-port 8080
```

You should see:
```
  +------------------------------------------------------+
  |      SENTINEL TWIN v2 -- SyncHack 2026               |
  |    Interactive AI-Controllable Command Dashboard     |
  +------------------------------------------------------+
  |  Mode : MQTT Broker @ 192.168.1.42:1883              |
  |  UI   : http://localhost:8000                        |
  +------------------------------------------------------+

  [MQTT] Connecting to broker at 192.168.1.42...
  [MQTT] Ensure Mosquitto is running on the Raspberry Pi
  [MQTT] Ensure ESP32 is flashed with sentinel_mqtt firmware
```

### Open the Dashboard

Navigate to `http://localhost:8000`. You should see:
- **MQTT pill** in the header showing `MQTT ● 1 ESP32` (green)
- **Live sensor data** from your ESP32 in the zone cards
- All other zones filled by the simulator
- The CHRONOS risk engine, predictor, and AI agent working on real data

---

## Step 5: Test the Full Pipeline

### Trigger a Real Alert

1. Hold a lighter (unlit!) near the MQ-2 sensor — the gas fumes will spike the smoke reading
2. Or breathe warm air on the DHT22 to raise the temperature
3. Watch the dashboard go from green → yellow → orange → red as thresholds are crossed
4. The AI agent will generate an incident report
5. The rover simulation will dispatch to investigate

### Test Blockage Detection

1. Place your hand within 50cm of the HC-SR04 sensor
2. The `blocked` field will switch to `true`
3. The dashboard will show the exit as blocked

### Test MQTT Commands

When the dashboard triggers an alarm (via the AI agent or manual button):
- The server publishes `{"cmd":"buzzer_on"}` to `sentinel/commands/<zone>`
- The ESP32 activates its buzzer pin (GPIO23)

### Test Failover

1. Unplug the ESP32 — within ~22 seconds the broker fires the LWT
2. The dashboard shows "ESP32 Offline" in the MQTT pill
3. The zone falls back to simulator data
4. Plug the ESP32 back in — it reconnects automatically

---

## Troubleshooting

### ESP32 won't connect to WiFi
- Make sure you're using a **2.4 GHz** SSID (ESP32 doesn't support 5 GHz)
- Check SSID/password in `esp32_firmware.ino`
- Try moving closer to the router

### ESP32 can't reach MQTT broker
- Verify the Pi's IP: `hostname -I` on the Pi
- Check Mosquitto is running: `sudo systemctl status mosquitto`
- Test from the Pi itself: `mosquitto_pub -t test -m hello`
- Check firewall: `sudo ufw allow 1883` (if ufw is enabled)
- Make sure ESP32 and Pi are on the same network

### No data on dashboard
- Check mode is set: `SENTINEL_MODE=mqtt` in `.env`
- Check broker IP matches: `MQTT_BROKER=<pi-ip>` in `.env`
- Run `python run.py --mqtt` (not `--sim`)
- Check server logs for connection errors

### DHT22 reading errors
- Check the 4.7kΩ pull-up resistor between DATA and 3.3V
- Make sure VCC is 3.3V (not 5V)
- Try DHT11 — change `#define DHT_TYPE DHT11` in firmware

### MQ-2 reads zero or max
- The MQ-2 needs 20 seconds of heater warmup (firmware does this automatically)
- For accurate readings, burn in the sensor for 24-48 hours
- Check the voltage divider (GPIO34 should see 0-3.3V, not 0-5V)

---

## Running Everything on the Raspberry Pi

If you want to run the full stack on the Pi (no separate PC needed):

```bash
# On the Pi:
cd ~/sentinel_twin

# Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set MQTT to localhost since broker is on the same machine
export MQTT_BROKER=127.0.0.1

# Start the server
python run.py --mqtt --broker 127.0.0.1

# Access from any device on the network:
# http://<pi-ip>:8000
```

Note: Change `host="127.0.0.1"` to `host="0.0.0.0"` in `run.py` line with
`uvicorn.run(...)` to allow access from other devices on the network.
