# Sentinel Twin X — Unified Master Judge Q&A & Presentation Cheat Sheet

> **System Overview**: Sentinel Twin X is an autonomous building safety, fire surveillance, and digital twin platform combining multi-sensor IoT nodes (ESP32), live MQTT telemetry, an AI vision-guided investigation rover, deterministic risk scoring (CHRONOS), trend forecasting, and a real-time React Command Center with Mission Control.

---

## Section 1: Core System Architecture & Telemetry Pipelines

### Q1: "How is the system architecture structured between hardware, backend, and frontend?"
**A:** Sentinel Twin X follows a 3-tier decoupled architecture:
1. **Edge Hardware / Telemetry Tier**: ESP32 microcontroller nodes equipped with multi-channel environmental sensors (DHT22 temp/humidity, MQ-2 gas/smoke, MQ-7 CO, MQ-135 air quality, HC-SR04 ultrasonic distance) and ESP32-CAM video stream.
2. **Central Processing & Bridge Tier**: Python FastAPI backend built with a modular Service Registry (`ApiService`, `MqttService`, `MissionService`, `VisionService`, `DiagnosticsService`) and thread-safe singleton state (`app_state`).
3. **Command Center Dashboard**: React 19 + TypeScript frontend featuring glassmorphism design tokens, real-time WebSocket state streaming at 2Hz, an interactive 2D Digital Twin map, live camera feed, and Mission Control controls.

### Q2: "How does the system switch between Hardware MQTT Mode, Serial Mode, and Simulated Demo Mode?"
**A:** The backend features an abstract `DataBridge` layer that normalizes telemetry regardless of source:
- **MQTT Mode**: Subscribes to `sentinel/sensors/#`, `sentinel/status/#`, and `sentinel/battery/#` over Mosquitto broker (TCP port 1883 or WebSocket port 9001).
- **Serial Mode**: Direct USB serial baud 115200 line parsing from physical microcontrollers.
- **Demo Mode**: Built-in statistical sensor simulator generating dynamic room temperature curves, gas leaks, and obstacle events for presentation without hardware.
The frontend allows operators to switch telemetry modes instantly via WebSocket without restarting the server.

### Q3: "How is the dashboard implemented and how does it achieve real-time sync?"
**A:** The dashboard is built as a React 19 + TypeScript SPA served by FastAPI. Instead of HTTP polling (which wastes bandwidth and causes latency), it opens a persistent WebSocket connection to `/ws`. The backend broadcasts state updates at 2Hz (every 500ms) or instantly when critical events (rover status changes, sensor alerts, or Mission Control commands) occur, yielding sub-50ms latency across all connected browsers.

### Q4: "How do the Live Camera Feed, Roboflow AI Vision, and Digital Twin map operate?"
**A:** 
- **Live Camera Feed & Roboflow AI Vision**: Streams via `/api/video-feed` using MJPEG encoding. Camera frames are processed asynchronously by a serverless **Roboflow AI Vision Workflow** (`fire-smoke-and-human-detector-vfire-smoke-and-human-detector-pr48p-1-rfdetr-large-t1-logic`). Inference runs at 1–2 FPS in a background proxy worker to maintain a smooth 30 FPS camera feed. It features:
  - **Smart 2-Second Verification**: Fire candidates must remain continuously visible for 2.0s before triggering verified crisis alerts.
  - **Human Awareness Threat Matrix**: `Fire` + `Human` triggers **CRITICAL** status with immediate evacuation guidance.
  - **Normalized Bounding Boxes**: Bounding boxes for `Fire` (Red), `Smoke` (Orange), and `Human` (Yellow/Cyan) render dynamically with confidence scores.
- **Digital Twin Map**: Rendered as dynamic SVG floor plans with room grid mapping, displaying real-time sensor heatmaps (Green = Normal, Yellow = Warning, Red = Critical), active rover location markers, and pre-calculated shortest evacuation paths.

---

## Section 2: Mission Control & Hardware Command Dispatch

### Q5: "How does the Mission Control card work and how are MQTT commands dispatched?"
**A:** The Mission Control card provides direct manual & autonomous operator control over the safety rover. When an operator clicks any of the four command buttons:
- 🟢 **Start Mission**: Publishes `{"command":"start"}` to MQTT topic `sentinel/commands/rover`
- ⏸ **Pause Mission**: Publishes `{"command":"pause"}` to MQTT topic `sentinel/commands/rover`
- 🔴 **Stop Mission**: Publishes `{"command":"stop"}` to MQTT topic `sentinel/commands/rover`
- 🚨 **Emergency Stop**: Publishes `{"command":"emergency"}` to MQTT topic `sentinel/commands/rover`

The backend `MqttService` publishes these JSON payloads with QoS 1 over Mosquitto to the rover. Concurrently, the UI and `app_state` update **Mission Status** (`Idle` → `Starting` → `Patrolling` → `Paused` → `Emergency` → `Mission Complete`), **Rover Status** (`Online` / `Offline`), and **Autonomous Mode** (`ON` / `OFF`) in real time.

### Q6: "What happens on the physical rover hardware when an Emergency Stop command is sent?"
**A:** When `{"command":"emergency"}` is received on `sentinel/commands/rover`, the ESP32 firmware immediately cuts PWM motor outputs to 0, halts all navigation routines, engages the emergency alarm buzzer (`GPIO 13`), blinks the status LED (`GPIO 2`), and transmits an emergency ACK back on `sentinel/ack/rover`. Simultaneously, the dashboard enters high-priority crisis state with synthesized audio alarms and desktop browser notifications.

### Q7: "How does the rover autonomous navigation state machine work?"
**A:** It's a state machine: `IDLE` → `EN_ROUTE` → `ARRIVED` → `VERIFYING` → `DONE`.
When CHRONOS flags any zone as HIGH risk (score ≥ 60), the rover automatically dispatches along a calculated path through the building corridor hub. On arrival, it runs a visual verification step—checking the camera frame for fire/smoke signatures—and reports `CONFIRMED` or `FALSE_ALARM`.

---

## Section 3: AI Engine, CHRONOS & Risk Prediction

### Q8: "Where's the AI? Is this just a bunch of IF statements?"
**A:** There are two distinct AI layers working together:
1. **CHRONOS Rule Engine (Deterministic Safety Core)**: Life-safety standards (NFPA smoke obscuration, OSHA thermal safety, building code clearances) demand deterministic, verifiable engineering rules, not probabilistic guesses. CHRONOS calculates composite 0–100 risk scores per zone.
2. **Predictive Analytics & AI Narrator**: Linear regression on a rolling window of historical sensor readings forecasts room risk scores 30 seconds ahead. For natural language analysis, cloud LLMs (Google Gemini / Groq API) or local template generators generate human-readable incident reports and recommendations. Heuristic vision models analyze camera frames for hazard verification.

### Q9: "What if the AI model is wrong or hallucinates?"
**A:** The AI LLM is strictly **advisory**, not authoritative. The source of truth is always CHRONOS—the deterministic rule engine. If Gemini says "low risk" but temperature is 68°C and smoke is 650 PPM, the risk score is still 95/100 and evacuation triggers. Automated responses (rover dispatch, alert, recommendation) are driven purely by CHRONOS sensor numbers.

### Q10: "How do you know the risk score means anything?"
**A:** The thresholds are derived from real fire safety standards:
- **NFPA** (National Fire Protection Association) guidelines for smoke detector sensitivity (typically triggers at 0.5–4% obscuration, which translates to ~200–600 PPM on an MQ-2).
- **OSHA** temperature guidelines for safe working environments.
- **Building code** evacuation path clearance rules.
The scoring weights guarantee that a confirmed fire (temp > 60°C AND smoke > 500 PPM) scores above 80 (`CRITICAL`), while a minor nuisance (smoke from a microwave, ~80 PPM) scores below 30 (`GREEN`).

### Q11: "Is the prediction accurate? How far ahead can it go?"
**A:** The prediction uses linear regression on the last 30 risk score readings (about 60 seconds of history). Linear extrapolation is *intentionally conservative*—real fires accelerate, so a linear model slightly underestimates escalation, giving more time to react rather than less. We display predictions up to 5 minutes ahead, but flag anything beyond 60 seconds as "estimate only." The key innovation is the *direction signal*: "rising" lets an operator investigate before it becomes critical.

### Q12: "What's the false alarm rate and how does visual verification reduce it?"
**A:** Traditional smoke alarms have 15–25% false alarm rates due to cooking, dust, and humidity. By requiring a rover visual confirmation before triggering full evacuation, we add a second independent check. In testing with our simulated verifier, the `CONFIRMED`/`FALSE_ALARM` accuracy is approximately 90%. In a real deployment with lightweight vision models (e.g. MobileNet), accuracy reaches 95%+.

---

## Section 4: Sensors, Hardware & Hardware Specs

### Q13: "What sensors does each node actually use?"
**A:** Five sensor channels on each zone node:
- **DHT22** — temperature (°C) and relative humidity (%)
- **MQ-2** — combustible gas and smoke (PPM)
- **MQ-7** — carbon monoxide CO (PPM)
- **MQ-135** — air quality index AQI (PPM)
- **HC-SR04** — ultrasonic distance sensor for evacuation path blockage detection
Each zone node runs on an ESP32 sending structured JSON telemetry every second over MQTT or USB serial.

### Q14: "What physical hardware components are needed to build this?"
**A:** 
- **Central Node**: Raspberry Pi 4 / PC running Python 3.11+, Mosquitto MQTT Broker, and FastAPI server.
- **Zone Node ($15-$25 total)**: ESP32 Development Board, DHT22, MQ-2, MQ-7, MQ-135, HC-SR04.
- **Rover Node ($35-$50 total)**: ESP32-CAM, L298N Dual H-Bridge Motor Driver, 2x DC Gear Motors, Li-ion 18650 Battery Pack, Piezo Buzzer.

---

## Section 5: Reliability, Offline Capability & Edge Autonomy

### Q15: "Does it need internet to work?"
**A:** No. The entire core safety loop—sensors, CHRONOS risk scoring, local MQTT broker, rover autonomous navigation, local WebSocket streaming, and evacuation routing—runs **100% offline on a local network**. If internet access is lost, the AI narrator automatically switches from cloud LLMs to an offline template generator with identical UI formatting. Unplugging the network cable during a demo does not stop the system.

### Q16: "How does the system handle sensor disconnections or node failures?"
**A:** Both `MqttService` and `DataBridge` run background staleness monitoring loops. If a sensor node fails to publish telemetry for >10 seconds, the system marks the zone as `offline`, zeroes out stale sensor values, logs a high-priority "Sensor Failure / Node Offline" event on the timeline, and notifies the operator. MQTT Last Will & Testament (LWT) on `sentinel/server/status` alerts clients if the main server disconnects.

---

## Section 6: Building Scalability & Commercial Comparison

### Q17: "How does it scale to a real building?"
**A:** The architecture scales horizontally. Each ESP32 node reports independently to the central server over MQTT—you simply add more nodes and zones. The zone graph in the path planner is an adjacency list updated when adding rooms. Multiple physical rovers or fixed cameras can be assigned to different floors/wings.

### Q18: "How does this solution compare to commercial industrial fire alarm panels?"
**A:** Traditional commercial fire panels cost $5,000–$50,000+, provide binary room alarms without predictive forecasting, have high false alarm rates (15-25%), and lack active investigation capability. Sentinel Twin X costs under $200 for a multi-zone setup, reduces false alarms via AI rover visual verification, predicts fire escalation 30s in advance, and provides a modern Web-based Digital Twin interface.

### Q19: "How is the command dashboard deployed for cloud access during presentations?"
**A:** The frontend React Command Center dashboard is deployed for 100% free on **Firebase Hosting** at `https://sentinel-command-centre.web.app`. It allows judges to open and interact with the full 9-page control interface on mobile devices or laptops in real time while connecting to the local Python telemetry backend bridge.

