# Sentinel Twin (Aegis)

An ESP32 rover streaming sensor telemetry over MQTT to a Raspberry Pi that stores it in SQLite, runs YOLO on a USB webcam, fuses both into alerts, and serves a live dashboard.

---

## The one idea that shapes every file

**A sensor that failed must never look like a sensor that read zero.**

Every reading carries a validity flag. Invalid readings travel as JSON `null` from firmware → MQTT → SQLite (`NULL`) → API → dashboard, where they render as grey `NO DATA` with a dashed border. They are never silently replaced with `0` or `-1`.

This sounds pedantic. It is the difference between a dashboard that says *"I cannot see the temperature"* and one that confidently says *"the temperature is fine"* while the building burns.

Three defences:

| Failure | Detected by | Latency |
|---|---|---|
| One sensor dies | validity flag → `null` | ~1 s |
| Rover stops reporting | server-side staleness timer | 5 s |
| Rover loses power | MQTT Last Will & Testament | ~22 s |

Verify it yourself: **unplug the DHT22** and watch only those two fields grey out. **Unplug the ESP32** and watch the banner go yellow, then red.

---

## Layout

```
aegis/
├── firmware/rover01/          ESP32 (Arduino)
│   ├── rover01.ino            cooperative scheduler; no delay() in loop()
│   ├── config.h               pins, thresholds, compile-time safety guards
│   ├── secrets.h              WiFi/MQTT creds  (gitignore this)
│   ├── sensors.h/.cpp         reads + validity flags + median filter
│   ├── motors.h/.cpp          LEDC PWM, interlocks, latching e-stop
│   └── net.h/.cpp             MQTT with LWT + exponential backoff
│
├── backend/                   Raspberry Pi (Python 3.11+)
│   ├── aegis/
│   │   ├── config.py          pydantic-settings; typed, env-driven
│   │   ├── db.py              SQLite + WAL; nullable sensor columns
│   │   ├── state.py           live registry; staleness detection
│   │   ├── mqtt/client.py     paho; re-subscribes on every reconnect
│   │   ├── vision/camera.py   threaded grabber; keeps newest frame only
│   │   ├── vision/detector.py YOLO; degrades honestly if unavailable
│   │   ├── fusion/rules.py    sensor × vision correlation
│   │   └── main.py            FastAPI + WebSocket + MJPEG
│   ├── tests/test_fusion.py   guards the null-discipline invariants
│   └── requirements.txt
│
├── dashboard/                 vanilla JS + Chart.js
├── deploy/                    mosquitto.conf, ACL, systemd unit
└── docs/wiring.md             READ THIS FIRST
```

---

## Install

### 1. Raspberry Pi — broker

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients

sudo cp deploy/mosquitto/aegis.conf /etc/mosquitto/conf.d/
sudo mosquitto_passwd -c /etc/mosquitto/passwd aegis     # choose a password
sudo systemctl enable --now mosquitto
sudo systemctl restart mosquitto

hostname -I        # note this IP — the ESP32 needs it
```

Give the Pi a **static IP** or a DHCP reservation. If its address changes on reboot, the rover silently stops reporting.

### 2. Raspberry Pi — backend

```bash
sudo apt install -y python3-venv python3-opencv    # distro OpenCV is faster
cd backend
python3 -m venv --system-site-packages ../.venv    # inherit python3-opencv
source ../.venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env                                          # set MQTT_PASS
```

`ultralytics` pulls in PyTorch (~2 GB). To skip vision for now, set `VISION_ENABLED=false` and omit it — the backend runs fine and reports `vision.available: false`.

```bash
uvicorn aegis.main:app --host 0.0.0.0 --port 8000
```

Open `http://<pi-ip>:8000`.

### 3. ESP32 — firmware

Arduino IDE 2.x → Boards Manager → **esp32 by Espressif** (2.x or 3.x both work).

Library Manager:
- `DHT sensor library` (Adafruit)
- `Adafruit Unified Sensor`
- `PubSubClient` (Nick O'Leary)
- `ArduinoJson` (Benoit Blanchon, **v7**)

Then:
1. Copy `firmware/rover01/` into your sketchbook.
2. Edit `secrets.h` — SSID, password, the Pi's IP, MQTT password.
   The ESP32 is **2.4 GHz only**. It cannot see a 5 GHz SSID.
3. Read **`docs/wiring.md`**. Wire the three voltage dividers.
4. Board: `ESP32 Dev Module`. Upload.

---

## Bring-up — do not skip stages

Each gate must pass before the next.

| Stage | Do | Gate |
|---|---|---|
| 0 | Read `docs/wiring.md` | dividers on ECHO, MQ-2, battery |
| 1 | Flash with sensors only, no motors | Serial shows plausible temp + distance |
| 2 | Set `secrets.h`, reflash | `mosquitto_sub -h localhost -u aegis -P <pw> -t 'aegis/#' -v` prints JSON |
| 3 | Start backend | `curl localhost:8000/api/health` → `mqtt_connected: true` |
| 4 | Open dashboard | live values; unplug DHT22 → those two fields grey out |
| 5 | **Wheels off the ground.** Wire L298N | each direction spins the right way |
| 6 | Compute + set `MOTOR_PWM_MAX` (see wiring.md §4.2) | rover drives; hand in front stops it |
| 7 | Plug in webcam | `/api/stream` shows video; boxes appear on people |
| 8 | Wire battery divider, set `BATTERY_ENABLED 1` | `battery_v` matches a multimeter ±0.1 V |

**Stage 5 is not optional.** A reversed motor lead is a two-second fix on a stand and a collision on the floor.

### `MOTOR_PWM_MAX` ships as `0`

`motors.cpp` **refuses to drive** while it is zero. This is deliberate. The L298N drops ~2 V, so:

```
motor_volts = (pack_volts − 2.0) × (MOTOR_PWM_MAX / 255)
```

A 6 V motor on an 11.1 V pack at full duty sees ~9 V and burns. Measure your pack, read the motor's rating, compute the number. Any value I could guess for you is a value that might destroy your hardware.

---

## Testing

```bash
cd backend && pytest -v
```

Ten tests, all guarding the same invariant from different angles: a `None` must never be interpreted as a safe or normal reading. Notably:

- `test_null_temperature_is_not_treated_as_normal` — DHT dead + gas alarming still raises a fire alert, marked 50 % confidence because it cannot be cross-checked.
- `test_null_battery_is_not_treated_as_empty` — an unwired divider never produces "battery critical".
- `test_stale_detections_are_not_treated_as_no_detections` — "the camera saw nobody" and "the camera is dead" are different claims.

Manual checks:

```bash
# Watch the raw bus
mosquitto_sub -h <pi> -u aegis -P <pw> -t 'aegis/#' -v

# Fake a second robot — it appears in the dashboard with zero config
mosquitto_pub -h <pi> -u aegis -P <pw> -t aegis/rover02/status \
  -r -m '{"robot_id":"rover02","online":true,"ip":"10.0.0.9"}'

# Drive
curl -X POST localhost:8000/api/robots/rover01/cmd \
  -H 'Content-Type: application/json' -d '{"cmd":"forward","speed":150}'
```

---

## Multi-robot

Topics are `aegis/<robot_id>/…` and the backend subscribes to `aegis/+/telemetry`. To add a rover: change `ROBOT_ID` in `config.h`, flash a second ESP32. It appears in the dashboard tabs automatically. No backend change.

Every DB row carries `robot_id`. Commands publish to `aegis/<id>/cmd`, so nothing cross-talks.

---

## Known limits — say these out loud before a judge finds them

- **YOLO on a Pi is not real-time.** YOLOv8n on a Pi 5 CPU is ~3–5 FPS at 640×480. `DETECT_EVERY_N_FRAMES=10` infers on 1 frame in 10. For real speed, export to NCNN (`yolo export model=yolov8n.pt format=ncnn`, ~2–3×) or add a Coral TPU.
- **Ultralytics is AGPL-3.0.** If your competition forbids AGPL, swap the model.
- **Fire and smoke are not COCO classes.** Out of the box, vision detects `person`. Real fire detection needs a custom-trained model; the sensor path handles fire today.
- **The MQ-2 is uncalibrated.** `MQ2_BASELINE` ships as `0`, so `mq2_ratio` is published as `null` and no gas alarm fires. Absolute PPM from a raw ADC read is fiction — the sensor needs 24–48 h of heater burn-in, then a clean-air baseline. The code alarms on a *relative* rise, which is the only defensible approach without a reference gas.
- **The camera does not move with the rover** — it is a USB webcam on the Pi.
- **No TLS.** `deploy/mosquitto/aegis.conf` has a commented TLS listener. Password auth over a LAN only.
- **`pulseIn()` blocks** up to 25 ms in the ultrasonic read. Tolerable at a 50 ms cadence; a production build would use an ECHO interrupt.

---

## Safety interlocks

Enforced inside `Motors`, not by callers — a caller that forgets one is a runaway robot.

| Interlock | Effect |
|---|---|
| `MOTOR_PWM_MAX == 0` | all drive refused |
| E-stop | latched; needs explicit clear |
| Battery critical | all drive refused |
| Command watchdog (teleop) | stops after 1.5 s of silence from the Pi |
| Obstacle | blocks **forward only** — reverse and turns stay legal, or the rover wedges against a wall forever |

`loop()` contains **no `delay()`**. The original firmware's `stop(); delay(200); back(); delay(400); turn(); delay(400)` left the rover blind for a full second — no sensors, no MQTT, no e-stop. At a 20 cm stop distance, that is a collision. Avoidance here is a state machine.

If the API cannot reach the broker, `POST /cmd` returns **503**, and the dashboard prints `NOT DELIVERED` in red. It never reports success for a command the rover did not receive.
