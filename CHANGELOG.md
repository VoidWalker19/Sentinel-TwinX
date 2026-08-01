# Changelog — Sentinel Twin X (v2 Upgrade)

All modifications, architectural enhancements, and software upgrades completed during Phase 2 are documented below. Every change preserves backwards-compatibility with the existing physical hardware (Raspberry Pi 3, ESP32, motor controllers, and sensor pins).

---

## [Phase 8] — Competition Build & Diagnostics
### Added
- **Competition Launcher Mode**: Added `--competition` flag to `run.py` to perform automatic startup checks and verification.
- **Diagnostics Service (`DiagnosticsService`)**: Automated component self-test runner and simulation overrides (WiFi loss, MQTT loss, sensor failures, low battery, path blockages).
- **Health Monitoring (`HealthMonitorService`)**: Real-time edge resource monitor tracking CPU, Memory, Disk, and Battery percentages.
- **Pytest Verification**: Added unit/integration test suite `tests/test_diagnostics_and_simulation.py` (all passing).
- **Comprehensive Documentation**:
  - `docs/Checklists.md` (Startup/Shutdown checklists)
  - `docs/PresentationMode.md` (Judging demo scripts & settings)
  - `docs/DeveloperDocs.md` (Architecture, custom service creation)
  - `docs/HealthMonitor.md`, `docs/Diagnostics.md`, `docs/PerformanceReport.md`
  - `reports/performance_report.md`, `reports/optimization_report.md` (Generated from local benchmarks)

---

## [Phase 5] — Professional Lovable-grade Web Dashboard
### Added
- **Dynamic Digital Twin Map Rendering**: Fully rewritten `map_renderer.js` to draw Rooms, Waypoints, Connections, and Overlays on the fly using `/api/building-config` with zero coordinate hardcoding.
- **Dynamic Trend Graphs Grid**: Plotted CSS/SVG temperature, humidity, gas/smoke, and battery decay charts inside the Analytics page.
- **Nesting Tag Fix**: Resolved unclosed div issues in pages 6 through 9 inside `index.html` that caused vertical layout collapsing.
- **Out-of-the-Box Lovable Styling**: Appended custom SVG glowing hover filters, risk score alert pulses, and chart layouts in `style.css`.
- **`avg_smoke` Metric**: Upgraded local SQLite aggregated statistics in `HistoryService` and verified via pytest.
- **`Dashboard.md`**: Created new documentation.

---

## [Phase 4] — Convex Realtime Backend Architecture
### Added
- **`HistoryService`**: Provides aggregated SQLite metrics endpoints `/api/history/sensors`, `/api/history/alerts`, and `/api/history/battery`.
- **`BackupService`**: Schedules automated database ZIP snapshots to `data/backups/` and enforces a local rotation policy keeping only the 5 most recent files.
- **`ConvexSyncService`**: Features a resilient synchronization queue with exponential backoff retries and offline caching to survive network disconnects.
- **`analytics` Table**: Created in both Convex schema and local SQLite.
- **Automated Data Retention Policy**: Prunes SQLite telemetry older than 7 days on startup to maintain database performance and storage safety.
- **Unit Tests**: Added test suites `test_database_pruning.py`, `test_convex_reconnect.py`, `test_history_service.py`, and `test_backup_service.py`.

### Modified
- **`schema.ts`**: Configured indexes on primary keys, timestamps, and zone properties for performance optimization.
- **`ApiService`**: Registered history endpoints and triggered backups dynamically via REST routes.
- **`DatabaseService`**: Integrated the analytics table, metrics write APIs, and the automatic pruning policy.

### Why Changes Were Made
- To enable multi-user dashboard real-time data sync.
- To prevent database inflation on SD cards.
- To allow remote statistics audits.
- To protect the system against local filesystem loss.

---

## [Phase 3] — Navigation & Mission Manager Upgrades
### Added
- **`PathPlannerService`**: Decoupled Dijkstra pathfinding service with multi-floor edge weight penalty calculation.
- **`ObstacleManagerService`**: Monitors HC-SR04 ultrasonic sensor inputs and manages zone/path blocking states.
- **Obstacle Recovery Loop**: Implemented a 3-tick (6-second) waiting recovery logic inside `RoverSimulator` travel tick; falls back to autonomous backtracking recall to home base if persistent.
- **State Transition Logging**: Hooked the Mission Manager FSM to output state transitions (`IDLE`, `PATROL`, `INSPECTION`, `EMERGENCY`, `RETURN_HOME`) to terminal logs, SQLite operations databases, and dashboard timeline events.
- **Unit Tests**: Created `tests/test_path_planner.py`, `tests/test_obstacle_manager.py`, and `tests/test_obstacle_recovery.py` to assert routing, distance/ETA calculations, and obstacle recovery.

### Modified
- **`NavigationService`**: Delegated shortest path queries, distances, and ETAs to `PathPlannerService`, keeping the core interpolation logic.
- **`MissionService`**: Integrated FSM tracking FSM transitions dynamically.
- **`RoverSimulator`**: Decoupled from hardcoded rooms/corridors, resolving the base station configuration dynamically from the config service.
- **`building.json`**: Added `navigation_config` block defining `base_zone`, speeds, and obstacle thresholds.

### Why Changes Were Made
- To complete the modular separation of duties between routing, obstacle sensing, travel execution, and mission state coordination.
- To allow dynamic waypoint edits and future multi-floor scalability without code modification.
- To implement robust fail-safes for physical rovers navigating dynamic office environments.

---

## [Phase 2F, 2G, 2J] — Camera, CV Auditing & Live Dashboard
### Added
- **POST `/api/ai/query` Endpoint:** Exposes natural language copilot chat queries routing to the unified `AiService`.
- **Unit Tests:** Created `tests/test_camera_service.py` and `tests/test_vision_service.py` to assert simulated frames, JPEG image stream headers, motion detection differences, and HSV color fire segment ratios.
- **Background CV Audits:** Embedded `VisionService` and `CameraService` background processing loops inside the main Scheduler tick.

### Modified
- **Streaming endpoints:** Replaced simulated setTimeout queries in `static/app.js` with live POST requests. Exposes raw and overlayed camera streams.
- **Failsafe Camera Startup:** Modified `CameraService` startup checks to fall back to simulated feed generation if a physical USB camera fails initial frame grabs, avoiding uvicorn thread hangs on headless rigs.

### Why Changes Were Made
- To allow the system to continuously audit safety hazards (smoke, flame, intruders) in the background without needing an active operator viewing the video stream.
- To bridge the front-end chat copilot to the backend AI model for telemetry-aware situation assessments.

### Hardware/Software Compatibility
- Frame downscaling is implemented for OpenCV HOG processing to minimize CPU overhead on the Raspberry Pi 3.
- Stream routes utilize standard HTTP MJPEG streams, supported by all major browsers.

---

## [Phase 2I] — Convex Realtime Cloud Integration
### Added
- **Convex HTTP Routes:** Added POST endpoints `/sync_ai_report`, `/sync_mission`, and `/sync_battery_history` in `convex/http.ts`.
- **Sync methods:** Extended `ConvexService` to upload reports, battery voltage history, and active missions.
- **Unit Tests:** Created `tests/test_convex_service.py` validating async request queues for all 7 Convex tables.

### Why Changes Were Made
- To support cloud mirroring and real-time dashboard state subscriptions for multiple remote clients.

### Hardware/Software Compatibility
- Sync queries operate on a non-blocking queue background thread. If the network link drops or latency rises, the local scheduler loop continues running at its 2Hz target without any hardware command lag.

---

## [Phase 2D & 2E] — Decoupled Mission & Navigation Managers
### Added
- **Standalone `MissionService` & `NavigationService`:** Decoupled high-level mission planning (Dijkstra egress routes, waypoint selection) from direct motor actuators.
- **Preemption Queue:** Added priorities to missions (IDLE, PATROL, INSPECTION, EMERGENCY, RETURN_HOME). Higher priority tasks instantly preempt routine patrols.

### Why Changes Were Made
- Separated high-level decision-making (on Raspberry Pi) from hardware movement control (on ESP32) for improved reliability and code separation.

---

## [Phase 2A & 2B] — ESP32 Firmware & MQTT Broker Integration
### Modified
- **Non-blocking Loop:** Upgraded ESP32 Arduino sketches to avoid `delay()` in sensor/motor reading loops.
- **MQTT Reconnections:** Added robust client broker connection retry logic and status heartbeat reporting.

### Why Changes Were Made
- Improves responsiveness to control commands, prevents watchdog triggers, and maintains continuous telemetry streams under erratic WiFi signals.
