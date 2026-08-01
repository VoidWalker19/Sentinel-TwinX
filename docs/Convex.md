# Sentinel Twin X — Convex Cloud Integration

This document outlines the cloud synchronization strategy, schema indexes, and reconnect safety mechanics implemented for Sentinel Twin X v2.

## Cloud Synchronization Model

Convex serves as the cloud synchronization mirror. The Raspberry Pi remains the primary operational backend node to guarantee 100% autonomous operation if internet connectivity is lost:

```
+--------------------+               +---------------------+
|   Raspberry Pi     |  Sync Queue   |    Convex Cloud     |
| (SQLite Storage)   | ------------> | (Realtime Database) |
+--------------------+               +---------------------+
```

## Reconnect Robustness & Offline Backoff

`ConvexSyncService` implements a resilient queue mechanism to handle network drops cleanly:
1. All sync requests are put into a thread-safe FIFO queue.
2. The background worker attempts to push posts to the Convex HTTP endpoints.
3. If a request fails (e.g. connection timeout, HTTP error), the service:
   - Sets the connectivity status to `Offline`.
   - Caches the failed item.
   - Enters a **retry loop with exponential backoff** (starting at 1.0s, doubling up to a maximum of 60.0s).
4. Once the network is restored, all queued items are flushed in order, and the status resets to `Online`.

This ensures zero telemetry loss during transient network disconnects and prevents the main program loop from blocking.
