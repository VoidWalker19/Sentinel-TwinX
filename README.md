# Sentinel Twin X (Version 2) — README

> **AI Powered Autonomous School Safety Digital Twin**  
> Professional Modular Architecture Upgrade (Phase 2 Completed)

---

## Phase 2 Modular Architecture Upgrade

We have refactored the legacy school codebase into a modular, commercial-grade safety digital twin platform:
- **Phase 2A (ESP32 Firmware):** Implemented heartbeats, diagnostics, and non-blocking motor control.
- **Phase 2B (MQTT):** Structured topic hierarchy supporting heartbeat streams and command ack routing.
- **Phase 2C (Modular Services):** Built clean OOP service class hierarchies for cameras, vision, databases, and missions.
- **Phase 2D & 2E (Mission & Navigation):** Decoupled high-level mission preemption states from raw motor steering.
- **Phase 2F & 2G (Camera & CV):** Integrated OpenCV background safety audits (fire and intrusion detection) on camera feeds.
- **Phase 2H (Gemini AI Assistant):** Connected the digital twin chat copilot to live, non-hallucinating telemetry.
- **Phase 2I & 2J (Convex & Dashboard):** Built async database syncing queues mirroring all 7 telemetry collections to a 9-page control dashboard.

For detailed design notes and hardware preservation rules, check [CHANGELOG.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/CHANGELOG.md).

---

## Key Rebuild Features in v3

- 🔒 **Cybersecurity & Device Authentication** — MQTT broker integration supports mandatory username/password client credentials, preventing IoT device spoofing or malicious sensor override injection.
- ⚙️ **Unified Building Configuration** — Single configuration file `config/building.json` holds all floor layout mappings, network pin maps, motor PWM limits, Dijkstra graph topology, and risk thresholds.
- 🔌 **Sensor Honesty Rule** — No simulated telemetry filler. If a sensor links down or falls stale for over 10 seconds, the dashboard displays it as greyed out with **NO DATA**, reflecting true hardware status.
- 🛠️ **Operator Debug Override** — An authenticated endpoint `/api/debug/inject` allows judges/operators to nudge a specific zone's live sensor readings upward to test emergency timing sequences in real hardware modes.
- ☁️ **Offline-First Two-Tier AI Narrator** — The LLM cascade is simplified into exactly two tiers: Google Gemini (Cloud Tier 1) and Local Deterministic templates (Tier 2). Groq has been stripped.
- 🧩 **Modular Frontend Architecture** — Splitting the single-page dashboard script into small, logical modules (`ws_client.js`, `map_renderer.js`, `sensor_cards.js`, `rover_panel.js`, `app.js`).

---

## What It Does

Sentinel Twin v3 follows a 5-step digital twin pipeline:

```
Detect (IoT Sensors) → Analyze (CHRONOS Engine) → Investigate (Rover Dispatch) → Verify (Vision AI) → Recommend (Dijkstra Routes)
```

1. **Detect** — Active telemetry from DHT22, MQ-2, and HC-SR04 sensors in 10 building zones.
2. **Analyze** — CHRONOS engine calculates risk (0–100) and predicts risk trends.
3. **Investigate** — Autonomous inspection rover dispatches automatically if risk score > 70.
4. **Verify** — Rover camera runs a computer vision heuristic check, outputting `CONFIRMED` or `FALSE_ALARM`.
5. **Recommend** — Dynamic Dijkstra-based evacuation pathing redirects occupants away from hazard zones, spoken out loud via text-to-speech.

---

## Quick Start

### 1. Install Dependencies

```bash
cd "Sentinel Twin"
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in credentials:
```bash
# Get a free Gemini key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_key_here

# Roboflow AI Vision (Workspace: ankit-chaudhary, Workflow: fire-smoke-and-human-detector-vfire-smoke-and-human-detector-pr48p-1-rfdetr-large-t1-logic)
ROBOFLOW_API_KEY=your_roboflow_key_here

# Configure MQTT authentication for the cybersecurity demo
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
MQTT_USER=sentinel_client
MQTT_PASS=secure_esp32_secret
```

### 3. Launching the System

Sentinel Twin v3 defaults to **Serial Hardware Mode** (`--serial`).

*   **Competition Mode** (Performs automatic diagnostic checks and runs startup validation):
    ```bash
    python run.py --sim --competition
    ```
*   **USB Serial Hardware Mode** (Default, ESP32 connected to Laptop over USB):
    ```bash
    python run.py
    ```
*   **Wireless MQTT Hardware Mode** (ESP32 on Rover connected via Raspberry Pi broker):
    ```bash
    python run.py --mqtt
    ```
*   **Simulator Mode** (Dev / Testing fallback, no hardware required):
    ```bash
    python run.py --sim
    ```

Dashboard automatically launches at **http://localhost:8000** in administrative mode (all controls unlocked).

---

## 📚 Final Competition Documentation

Please refer to the following final competition build documents:
*   **System Checklists**: [Checklists.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/Checklists.md)
*   **Demo & Presentation Guides**: [PresentationMode.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/PresentationMode.md)
*   **System Architecture Blueprint**: [Architecture.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/Architecture.md)
*   **Developer Guide**: [DeveloperDocs.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/DeveloperDocs.md)
*   **System Health Telemetry**: [HealthMonitor.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/HealthMonitor.md)
*   **Diagnostics & Failure Simulator**: [Diagnostics.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/Diagnostics.md)
*   **Performance Profile Report**: [PerformanceReport.md](file:///c:/Users/kunal/OneDrive/Desktop/Sentinel%20Twin/docs/PerformanceReport.md)

---

## Demo Script (30-Second Walkthrough for Judges)

1. Open the dashboard in **Simulator Mode** (`python run.py --sim`).
2. Click the **🔥 Simulate Lab Fire** scenario button in the left panel.
3. Observe:
   - The Chemistry Lab zone lights up **red** on the SVG digital blueprint.
   - A red **"SIMULATED DATA"** warning banner appears at the top.
   - The Rover **auto-dispatches** (cyan dot moves along Dijkstra waypoints).
   - The **AI Narrator** reports a high-probability thermal anomaly.
   - The system speaks evacuation recommendations aloud.
4. Once the rover arrives at the Chemistry Lab, it performs a simulated camera scan to output **VERDICT: CONFIRMED**.
5. Click **🔄 RESET ALL** to return the building to a nominal baseline.

---

## Project Architecture

```
sentinel-twin/
├── run.py                    ← Rebuilt entry point (Defaults to --serial)
├── config/
│   └── building.json         ← Single source of truth config (pins, zones, thresholds)
├── requirements.txt
├── .env
│
├── server/
│   ├── app.py                ← FastAPI web server with /api/debug/inject endpoint
│   ├── state.py              ← Thread-safe AppState singleton (pre-loaded with offline zones)
│   ├── data_bridge.py        ← Parses serial feeds; implements staleness checks (>10s)
│   ├── mqtt_bridge.py        ← Cybersecurity authenticated bridge with Mosquitto
│   └── scheduler.py          ← Runs CHRONOS risk checks and dispatches every 2s
│
├── engine/
│   ├── config_loader.py      ← Dynamic JSON config parser
│   ├── chronos.py            ← Rule engine scoring (excludes offline nodes from risk)
│   └── recommender.py        ← Dijkstra routing using risk weights and physical blocks
│
├── ai/
│   ├── narrator.py           ← Two-tier AI (Gemini cloud + Local fallback templates)
│   └── templates.py          ← Offline deterministic report generator
│
├── static/
│   ├── index.html            ← Auth-free commands panel
│   ├── style.css             ← Glassmorphic UI colors and SVG styles
│   ├── app.js                ← Main JS entry orchestrator
│   ├── ws_client.js          ← Websocket communication layer
│   ├── map_renderer.js       ← Digital SVG blueprint drawing
│   ├── sensor_cards.js       ← Zone sensor grid and grey "NO DATA" offline cards
│   └── rover_panel.js        ← Rover diagnostics grid and battery telemetry
```
