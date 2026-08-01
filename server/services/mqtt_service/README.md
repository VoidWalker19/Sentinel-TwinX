# MQTT Service

Manages connection to the Mosquitto MQTT broker, subscribes to telemetry channels, and dispatches command requests to rover nodes.

## Configuration
- `broker_host`: Address of broker (default: `"192.168.1.100"`).
- `broker_port`: Port of broker (default: `1883`).
- `username`: Auth username.
- `password`: Auth password.
- `client_id`: MQTT client identity string.

## Callbacks Registered
- `on_message(zone_id, telemetry_dict)`: Fired on incoming zone sensor telemetry.
- `on_status(zone_id, status_dict)`: Fired on status heartbeats (online/offline/heap).

## Errors Handled
- Connection dropouts / refuse: Auto reconnection handler provided by paho-mqtt client with non-blocking exponential backoffs.
- Invalid JSON payloads: Decaptured gracefully and logged as warnings rather than crashing message handler thread.
