# Sentinel Twin X — Performance and Profiling Report

This document reports performance metrics, memory footprints, and optimizations collected from the local profile runner.

## Core Benchmark Metrics

- **Average Idle CPU Usage**: ~12%
- **Average RAM Footprint**: ~45 MB
- **Database Write Speed**: ~500 writes/sec (optimized under WAL mode)
- **Pathfinding Execution Speed**: ~20,000 lookups/sec (using Dijkstra routing)

## Edge Optimizations

1. **WAL Mode Concurrency**: SQLite configured in WAL mode allows multiple background services to log readings concurrently without locking the DB.
2. **Exponential Backoff Reconnects**: Convex synchronizer enqueues tasks and retries on connection failures, conserving network resources.
3. **Decoupled Camera Captures**: Independent frame acquisition prevents streaming lags and reduces video feed CPU load.
