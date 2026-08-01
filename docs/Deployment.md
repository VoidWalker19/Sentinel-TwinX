# Sentinel Twin X — Deployment & Operations Guide

This guide covers deployment procedures, environment configurations, backups, and operational guidelines.

## Environment Variables

Create a local `.env` file in the project root:

```ini
# MQTT Broker Config
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883

# Convex Cloud DB
CONVEX_URL=https://your-project.convex.cloud

# AI Copilot API
GEMINI_API_KEY=AIzaSy...
```

## Backup & Recovery Management

`BackupService` handles database integrity snapshots:
*   **Location:** Snapshots are compressed into ZIP archives in `data/backups/`.
*   **Retention:** Keeps only the **5 most recent** backup archives, automatically rotating out older snapshots.
*   **Manual Trigger:** Can be requested via endpoint:
    `POST http://localhost:8000/api/backup/create`

## Health Monitoring & Diagnostics

Sentinel Twin X runs a continuous health monitoring agent and failure test runner:
*   **System Health:** Accessible at `GET http://localhost:8000/api/health` and `GET http://localhost:8000/api/health/history`.
*   **Diagnostics Self-Test:** Triggered using `POST http://localhost:8000/api/diagnostics/run`.
*   **Failure Simulation Control:** Enabled/disabled via `POST http://localhost:8000/api/diagnostics/simulation`.

## Deployment Steps (Raspberry Pi 3)

1. Clone the repository to the primary node.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up the Mosquitto MQTT broker:
   ```bash
   sudo apt-get install mosquitto mosquitto-clients
   ```
4. Configure Mosquitto to listen on all interfaces.
5. Launch the application:
   ```bash
   python run.py --sim
   ```
