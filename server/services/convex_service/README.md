# Convex Service

Coordinates synchronization of local telemetry events to the Convex Cloud database.

## Configuration
- `CONVEX_URL`: Exposes HTTP endpoints of the Convex deployment (loads from `.env`).

## Features
- Background thread queue: all HTTP mutation posts are executed asynchronously in a daemon worker thread to prevent lagging scheduling loops.
- Graceful network failover: catches request timeouts and connection drops safely.
