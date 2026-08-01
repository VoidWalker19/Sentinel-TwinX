# Sentinel Twin X — SQLite Database Documentation

This document describes the local storage backend architecture, tables, and data retention policies for Sentinel Twin X v2.

## Local Storage Node (Raspberry Pi)

The primary data persistence layer resides locally on the Raspberry Pi using a SQLite database located at `data/sentinel.db`. It is configured in **Write-Ahead Logging (WAL)** mode for concurrency safety and thread isolation.

## SQLite Schema Details

The database is structured into 9 tables containing indexes on query fields:

### 1. `sensorReadings`
Logs DHT22 temperature and humidity values, MQ-2 smoke levels, and hallway blocked statuses.
- **Index:** `by_zone`, `by_timestamp`

### 2. `alerts`
Stores safety events, risk scores, status levels, and text descriptions.
- **Index:** `by_zone`, `by_timestamp`

### 3. `missions`
Tracks mission IDs, types, priorities, FSM states, and target waypoints.
- **Index:** `by_mission_id`, `by_status`

### 4. `roverStatus`
Contains battery percentages, coordinates, Wifi RSSI telemetry, and uptime.
- **Index:** `by_timestamp`

### 5. `batteryHistory`
Logs battery voltage and decay curves.
- **Index:** `by_timestamp`

### 6. `cameraEvents`
Logs OpenCV computer vision detection types, confidence metrics, and JPG snapshot paths.
- **Index:** `by_timestamp`

### 7. `reports`
Caches Gemini AI safety intelligence analysis, severity verdicts, and recommendation arrays.
- **Index:** `by_timestamp`

### 8. `settings`
Key-value configuration maps for system parameters.
- **Index:** `by_key`

### 9. `analytics` (New)
Captures custom performance telemetry and system metric trends.
- **Index:** `by_event_type`, `by_timestamp`

---

## Automatic Data Retention Policy

To prevent the local SQLite file from consuming excessive disk space on the Raspberry Pi, `DatabaseService` runs a data retention policy on startup:
*   Prunes all data entries older than **7 days** (configurable via the building config).
*   Applies pruning across all major log tables: `sensorReadings`, `alerts`, `roverStatus`, `batteryHistory`, `cameraEvents`, and `analytics`.
