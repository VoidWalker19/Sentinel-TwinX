# Sentinel Twin X — Operational Checklists

This document outlines the startup and shutdown procedures to ensure reliability during competitive events and live hardware deployments.

## Startup Checklist (Automatic & Manual)

To start the system with full component validation, execute the competition launcher:

```bash
python run.py --sim --competition
```

The competition script automatically executes the following checks:

| Step | Component | Verification Criteria | Action if Fails |
| :--- | :--- | :--- | :--- |
| **1** | **Sensors** | SensorService and HealthService are registered. | Verify `server/services/__init__.py` has registered both services. |
| **2** | **Battery** | Rover battery telemetry reads > 0%. | Check ESP32 telemetry battery payload or mock battery state. |
| **3** | **WiFi** | Link connection test passes. | Verify wireless network adapter is active and connected. |
| **4** | **MQTT** | Connection established with Mosquitto broker. | Ensure broker is running (`START_MQTT.bat` or `sudo systemctl start mosquitto`). Check credentials in `.env`. |
| **5** | **Camera** | OpenCV frame buffer returns valid data. | Ensure USB webcam is plugged in and recognized as webcam index `0`. |
| **6** | **Dashboard** | Web server binds to port 8000 successfully. | Close any other processes running on port 8000 (e.g., duplicate uvicorn runners). |
| **7** | **Navigation** | Dijkstra routing successfully resolves path. | Verify graph configuration in `config/building.json` is not corrupted. |
| **8** | **Mission Manager** | Preemption queue is initialized. | Verify MissionService is registered in registry. |
| **9** | **AI** | Cloud Gemini API or Local Rule Engine ready. | Check `GEMINI_API_KEY` in `.env`. If absent, system automatically boots Local Rule Engine. |

Once all checks pass, the console prints `SYSTEM READY` and launches the Uvicorn FastAPI dashboard on `http://localhost:8000`.

---

## Shutdown Checklist

To perform a clean shutdown, follow these steps:

1. **Stop FastAPI / Uvicorn Server**:
   - Focus the running terminal and press `Ctrl+C`.
   - The launcher will catch `KeyboardInterrupt` and trigger `registry.stop_all()`.
2. **Verify Daemon Thread Exit**:
   - Wait for the log print `Shutdown logging service handlers`.
   - All background threads (Camera acquisition, Health monitoring, MQTT subscriber loops) will terminate cleanly.
3. **Stop MQTT Broker (If running locally)**:
   - Close the Mosquitto broker terminal window.
4. **Inspect Database Integrity**:
   - Ensure `data/sentinel.db` database file is closed cleanly (WAL file prunes back into database file).
