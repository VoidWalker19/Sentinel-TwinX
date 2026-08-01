# Sentinel Twin X — Performance Profile & Optimization Report

Generated: 2026-07-18 22:15:52

## 1. System Resource Usage Profile
- **Average CPU Load**: 25.05% (Peak: 28.5%)
- **Average Memory Footprint**: 90.86 MB (Peak: 90.86 MB)
- **Disk IO Profile**: Normal / Nominal

## 2. Microbenchmarks
### Database Operations
- **Total Test Writes**: 50
- **Execution Time**: 0.0665 seconds
- **Database Write Throughput**: 752.14 writes/sec

### Path Planning & Dijkstra Routing
- **Total Test Lookups**: 100
- **Execution Time**: 0.0006 seconds
- **Routing Engine Speed**: 173677.18 paths/sec

## 3. Network & Connection Optimization
- **Offline Cache**: Implemented in `ConvexService` (stores pending sync messages in queue, retries with exponential backoff on reconnection).
- **MQTT Broker Efficiency**: Topic-based routing reduces wildcard matches, minimizing message overhead on low-bandwidth networks.
- **Payload Compression**: JSON telemetry messages are flat and compact, averaging under 150 bytes per payload.

## 4. Power & Raspberry Pi CPU Optimizations
- **Thread Yielding**: Background loops (camera capture, health checks, risk evaluations, and diagnostics tracker) utilize `time.sleep()` blocks to prevent 100% CPU thread-locking.
- **Idle Polling Rate**: Polling rate is dynamically tuned via `sensor_poll_rate` setting (default 2.0s), saving CPU cycles when system is quiet.
- **Hardware Fallbacks**: CPU-intensive computer vision and AI models fall back to lightweight rule-based local engines when network limits are encountered.
