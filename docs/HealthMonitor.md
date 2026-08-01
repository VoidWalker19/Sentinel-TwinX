# Sentinel Twin X — Health Monitor Service Documentation

The `HealthMonitorService` runs as a background service on the primary node. It tracks edge system resources and publishes diagnostic metrics to support continuous operations.

## Architecture

```
+------------------------+
|  HealthMonitorService  |
+-----------+------------+
            |
            | (Reads metrics)
            v
   +--------+---------+
   |  psutil / OS API |
   +------------------+
```

## Tracked Metrics

1. **CPU Usage**: Average load percentage across all CPU cores.
2. **Memory Footprint**: System virtual memory usage percentage and RSS footprint in MB.
3. **Disk Space**: Utilization percentage of the primary root partition.
4. **Battery Status**: Rover battery percentages (when mock/hardware reports it).

## Endpoints

*   `GET /api/health`
    Returns a JSON object representing the latest system resource usage metrics.
    *   **Response format**:
        ```json
        {
          "timestamp": 1784393157.0,
          "cpu_percent": 12.4,
          "memory_percent": 45.2,
          "disk_percent": 30.5
        }
        ```
*   `GET /api/health/history?limit=20`
    Returns a list of the last `limit` metrics entries to support plotting historical resource trends.
