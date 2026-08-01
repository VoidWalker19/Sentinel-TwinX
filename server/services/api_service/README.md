# API Service

Coordinates web dashboard operations, websocket broadcasting, and REST endpoint routes.

## Endpoints
- `/ws`: Bidirectional communication.
- `/api/state`: State queries.
- `/api/export-audit`: Immutable logs.
- `/api/building-config`: Dynamic layout map.
- `/api/debug/inject`: Emergency overrides.

## Errors Handled
- Connection drops: Automatically cleans up WebSocket connection pools to prevent memory leakage.
- Direct filesystem route requests: Gracefully returns file content mappings or mounts fallbacks to prevent 404/500 loops.
