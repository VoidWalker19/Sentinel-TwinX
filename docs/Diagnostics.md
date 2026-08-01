# Sentinel Twin X — Diagnostics & Failure Simulation Service

The `DiagnosticsService` supports self-tests and failure simulations to guarantee hardware, communication, and software resilience.

## Core Features

1. **Self-Tests**: Query status of database operations, path planners, camera frame acquisitions, WiFi latency, and MQTT broker connectivity.
2. **Failure Simulations**:
   - **Wi-Fi Loss**: Drop Convex cloud synchronization and MQTT traffic.
   - **MQTT Loss**: Simulate broker disconnection or broker crash.
   - **Sensor Failure**: Inject stuck values, physical out-of-range bounds, or missing updates.
   - **Camera Failure**: Mock webcam connection drops.
   - **Low Battery**: Simulate battery depletion below 15% to test emergency home-dock routing.
   - **Navigation Blockage**: Inject obstacles on critical paths to verify rerouting.

## Endpoints

*   `POST /api/diagnostics/simulation?mode={mode}&value={value}`
    Enables/disables a simulation mode.
    *   **Parameters**:
        - `mode`: `"wifi_loss"`, `"mqtt_loss"`, `"camera_failure"`, `"low_battery"`, `"navigation_blockage"`, `"sensor_failure"`
        - `value`: `"true"`, `"false"`, or a JSON dict (e.g. `lobby:true` for sensor failure)
*   `GET /api/diagnostics/simulation`
    Returns a dictionary of all active simulation override states.
*   `POST /api/diagnostics/run`
    Triggers all self-tests synchronously and returns a component health report.
