# Sentinel Twin X — Developer Documentation

This developer guide is intended for engineers modifying, maintaining, or expanding the Sentinel Twin X platform.

---

## 1. Project Directory Structure

```
├── config/                      # JSON configuration files (building layouts, thresholds)
├── data/                        # Local SQLite databases and automated backups
├── docs/                        # Markdown guides, checklists, and blueprints
├── firmware/                    # ESP32 Arduino/C++ source code
├── reports/                     # Generated performance profiles and optimization audits
├── rover/                       # Rover simulator loops
├── server/                      # Core FastAPI backend web server
│   ├── services/                # Registry-managed modular OOP service modules
│   │   ├── ai_service/          # Gemini API wrapper and RuleEngine fallback
│   │   ├── alert_service/       # CHRONOS risk index engine
│   │   ├── analytics_service/   # Reporting and export engine
│   │   ├── camera_service/      # Camera frame buffer acquisition
│   │   ├── diagnostics_service/ # Self-test runners and simulator overrides
│   │   ├── health_monitor_service/# OS resource monitoring
│   │   └── ...                  # Other core modules
│   └── state.py                 # Thread-safe global AppState singleton
├── static/                      # Frontend HTML, CSS, and JS files
├── tests/                       # Pytest unit and integration test suite
├── requirements.txt             # Python project dependencies
└── run.py                       # CLI application launcher
```

---

## 2. Adding a New Service

To add a new modular service to the backend:

1. Inherit from `BaseService` defined in `server/services/base_service.py`.
2. Implement the standard lifecycle methods:
   - `_on_start(self) -> bool`
   - `_on_stop(self) -> bool`
3. Register the service in the Service Registry inside `server/services/__init__.py`:
   ```python
   from server.services.my_service.service import MyService
   registry.register(MyService())
   ```
4. Define its startup order in the `order` list to handle topological dependencies.

---

## 3. Modifying state telemetry

All shared variables belong in the thread-safe `AppState` singleton inside `server/state.py`.
Always modify variables using the `self._lock` mutex context to guarantee concurrency safety for background telemetry threads:

```python
with self._lock:
    self.rover.position = new_coordinates
```
