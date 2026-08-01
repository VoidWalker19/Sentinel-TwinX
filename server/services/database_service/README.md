# Database Service

Manages dynamic schema layout and persistence of incident history to a local SQLite database file using Write-Ahead Logging (WAL) mode.

## Configuration
- `db_path`: Location of database file (default: `"data/sentinel.db"`).

## Schema Tables
- `sensorReadings`: Environmental metrics history.
- `alerts`: Historical alarms log.
- `missions`: Rover patrol logs.
- `roverStatus`: Coordination track.
- `batteryHistory`: Power telemetry.
- `cameraEvents`: Motion and vision logs.
- `reports`: Saved AI analysis summaries.
- `settings`: Persisted custom limits.

## Errors Handled
- Database busy / locked conditions: Mitigated by activating WAL mode, check_same_thread=False, and transactional operations.
- Write IO failures: Caught and logged defensively without raising stack traces.
