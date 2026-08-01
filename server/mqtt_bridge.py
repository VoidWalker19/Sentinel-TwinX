"""
server/mqtt_bridge.py — MQTT Data Bridge (ESP32 → Broker → Sentinel Twin)

This module connects to a Mosquitto MQTT broker (running on the Raspberry Pi)
and subscribes to sensor telemetry published by the ESP32. Incoming JSON
messages are parsed into ZoneReading objects and fed into app_state, exactly
like the SimBridge and SerialBridge do.

MQTT Topics:
    Subscribe:  sentinel/sensors/#     — wildcard, picks up all zones
    Subscribe:  sentinel/status/#      — ESP32 online/offline (LWT)
    Publish:    sentinel/commands/<zone> — send commands to ESP32 (buzzer, etc.)

The bridge fills in any missing zones from the simulator, so the dashboard
always shows all 10 zones even if only one ESP32 is deployed.

Thread safety: paho-mqtt runs its own network thread. All writes to
app_state go through the existing thread-safe update_zone() method.
"""

import json
import time
import threading
import logging
import os
from typing import Dict, Optional

from server.state import app_state, ZoneReading, TimelineEvent
from simulator.sensor_sim import sensor_simulator
from engine.chronos import ZONE_CONFIG

logger = logging.getLogger(__name__)


class MqttBridge:
    """
    MQTT-based data bridge that subscribes to ESP32 sensor telemetry
    via a Mosquitto broker and feeds readings into the Sentinel Twin pipeline.

    Unlike SimBridge/SerialBridge (which extend DataBridge/Thread), this
    class uses paho-mqtt's own network thread via loop_start(). It doesn't
    need to poll — messages arrive via callbacks.
    """

    FILL_INTERVAL = 2.0  # Seconds between filling missing zones from simulator

    def __init__(self, broker_host: str = 'sentinelpi.local',
                 broker_port: int = 9001,
                 username: str = '',
                 password: str = ''):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password

        # Track the latest reading per zone from MQTT
        self._lock = threading.Lock()
        self._mqtt_readings: Dict[str, ZoneReading] = {}
        self._esp32_status: Dict[str, dict] = {}  # zone → status info
        self._obstacle_start_times: Dict[str, float] = {}  # zone → obstacle start timestamp
        self._connected = False
        self._client = None

        # Background thread to fill missing zones
        self._stop_event = threading.Event()
        self._fill_thread = None

    def start(self):
        """Connect to the MQTT broker and start listening."""
        try:
            import paho.mqtt.client as paho_mqtt
        except ImportError:
            logger.error(
                "[MqttBridge] paho-mqtt not installed! "
                "Run: pip install paho-mqtt>=2.0.0"
            )
            logger.warning("[MqttBridge] Falling back to simulator mode")
            self._start_fill_thread()
            return

        # Parse transport and check for ws/wss or port 9001
        broker = self.broker_host
        transport = 'tcp'
        if broker.startswith('ws://'):
            transport = 'websockets'
            broker = broker[5:]
            self.broker_port = 9001
        elif broker.startswith('wss://'):
            transport = 'websockets'
            broker = broker[6:]
            self.broker_port = 9001
            
        if ':' in broker:
            parts = broker.split(':')
            broker = parts[0]
            try:
                self.broker_port = int(parts[1])
            except ValueError:
                pass
                
        if self.broker_port == 9001:
            transport = 'websockets'
            
        self.broker_host = broker

        # Create MQTT client
        # paho-mqtt v2 uses CallbackAPIVersion
        try:
            self._client = paho_mqtt.Client(
                callback_api_version=paho_mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"sentinel-twin-server-{int(time.time())}",
                clean_session=True,
                transport=transport,
            )
        except (AttributeError, TypeError):
            # Fallback for paho-mqtt v1
            self._client = paho_mqtt.Client(
                client_id=f"sentinel-twin-server-{int(time.time())}",
                clean_session=True,
                transport=transport,
            )

        # Set credentials if provided
        if self.username:
            self._client.username_pw_set(self.username, self.password)

        # Set Last Will (so other subscribers know if the server goes down)
        self._client.will_set(
            "sentinel/server/status",
            payload='{"server":"offline"}',
            qos=1,
            retain=True
        )

        # Wire callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Connect (non-blocking)
        try:
            self._client.connect_async(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()  # Starts paho's network thread
            logger.info(
                f"[MqttBridge] Connecting to MQTT broker at "
                f"{self.broker_host}:{self.broker_port}..."
            )
        except Exception as e:
            logger.error(f"[MqttBridge] Failed to connect: {e}")
            logger.warning("[MqttBridge] Will keep retrying via paho reconnect...")

        # Log to timeline
        app_state.add_timeline_event(TimelineEvent(
            event_type='info',
            description=f"📡 MQTT Bridge connecting to {self.broker_host}:{self.broker_port}",
            severity='info',
        ))

        # Start background fill thread
        self._start_fill_thread()

    def stop(self):
        """Disconnect from the broker and stop background threads."""
        self._stop_event.set()

        if self._client:
            # Publish server offline status
            try:
                self._client.publish(
                    "sentinel/server/status",
                    '{"server":"offline"}',
                    qos=1,
                    retain=True
                )
            except Exception:
                pass

            self._client.loop_stop()
            self._client.disconnect()
            logger.info("[MqttBridge] Disconnected from MQTT broker")

        if self._fill_thread:
            self._fill_thread.join(timeout=2.0)

    def join(self, timeout=None):
        """Wait for the fill thread to finish (for compatibility with DataBridge API)."""
        if self._fill_thread:
            self._fill_thread.join(timeout=timeout)

    def publish_command(self, zone_id: str, command: dict):
        """
        Publish a command to an ESP32 node via MQTT.

        Args:
            zone_id: Target zone (e.g., 'chem_lab')
            command: Dict with command data, e.g. {"cmd": "buzzer_on"}
        """
        if not self._client or not self._connected:
            logger.warning("[MqttBridge] Cannot publish — not connected to broker")
            return False

        topic = f"sentinel/commands/{zone_id}"
        payload = json.dumps(command)

        try:
            result = self._client.publish(topic, payload, qos=1)
            if result.rc == 0:
                logger.info(f"[MqttBridge] Published command to {topic}: {payload}")
                return True
            else:
                logger.warning(f"[MqttBridge] Publish failed (rc={result.rc})")
                return False
        except Exception as e:
            logger.error(f"[MqttBridge] Publish error: {e}")
            return False

    # ── MQTT Callbacks ────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc, *args):
        """Called when the broker accepts our connection."""
        if isinstance(rc, int):
            reason_code = rc
        else:
            # paho v2 passes a ReasonCode object
            reason_code = rc.value if hasattr(rc, 'value') else int(rc)

        if reason_code == 0:
            self._connected = True
            logger.info("[MqttBridge] ✓ Connected to MQTT broker")

            # Subscribe to sensor telemetry from all zones
            client.subscribe("sentinel/sensors/#", qos=1)
            client.subscribe("sentinel/sensors", qos=1)
            # Subscribe to ESP32 status (online/offline via LWT)
            client.subscribe("sentinel/status/#", qos=1)
            client.subscribe("sentinel/status", qos=1)

            logger.info("[MqttBridge] Subscribed to sentinel/sensors/#, sentinel/sensors, sentinel/status/#, and sentinel/status")

            # Publish server online status
            client.publish(
                "sentinel/server/status",
                '{"server":"online"}',
                qos=1,
                retain=True
            )

            # Log to timeline
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description=f"📡 MQTT broker connected — receiving live ESP32 data",
                severity='info',
            ))
        else:
            self._connected = False
            logger.error(f"[MqttBridge] Connection refused (rc={reason_code})")
            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description=f"⚠️ MQTT broker connection refused (code {reason_code})",
                severity='warning',
            ))

    def _on_disconnect(self, client, userdata, *args):
        """Called when we lose connection to the broker."""
        self._connected = False
        logger.warning("[MqttBridge] Disconnected from MQTT broker — will auto-reconnect")
        app_state.add_timeline_event(TimelineEvent(
            event_type='alert',
            description="⚠️ MQTT broker connection lost — reconnecting...",
            severity='warning',
        ))

    def _on_message(self, client, userdata, msg):
        """Called for every incoming MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8', errors='ignore')

            # Route based on topic prefix
            if topic.startswith("sentinel/sensors"):
                self._handle_sensor_message(topic, payload)
            elif topic.startswith("sentinel/status"):
                self._handle_status_message(topic, payload)
            else:
                logger.debug(f"[MqttBridge] Ignoring unknown topic: {topic}")

        except Exception as e:
            logger.error(f"[MqttBridge] Error processing message: {e}")

    # ── Message Handlers ──────────────────────────────────────────────────

    def _handle_sensor_message(self, topic: str, payload: str):
        """
        Parse a sensor telemetry message from an ESP32.

        Expected topic: sentinel/sensors/<zone_id>
        Expected JSON:  {"zone":"chem_lab","temp":28.5,"smoke":48,"hum":54.2,"blocked":false}
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.debug(f"[MqttBridge] Bad JSON on {topic}: {payload!r}")
            return

        # Extract zone ID from topic or payload
        parts = topic.split('/')
        zone_id = parts[-1] if len(parts) > 2 else 'chem_lab'
        payload_zone = str(data.get('zone', '')).lower().replace(' ', '_')

        # Check if this is the rover
        if payload_zone == 'rover' or zone_id == 'rover':
            self._handle_rover_sensor_message(data)
            return

        # Prefer payload zone, fall back to topic zone
        if payload_zone and payload_zone in ZONE_CONFIG:
            zone_id = payload_zone
        elif zone_id not in ZONE_CONFIG or not zone_id or zone_id == 'sensors':
            # Try partial match (ESP32 might send a slightly different name)
            matched = False
            for known_id in ZONE_CONFIG:
                if (zone_id and known_id.startswith(zone_id[:4])) or \
                   (zone_id and zone_id.startswith(known_id[:4])):
                    zone_id = known_id
                    matched = True
                    break
            if not matched:
                if not payload_zone:
                    zone_id = 'chem_lab'
                else:
                    logger.debug(f"[MqttBridge] Unknown zone '{zone_id}' — ignoring")
                    return

        # Parse sensor values (handle null/offline values for failed/broken sensors)
        temp_val = data.get('temp')
        hum_val = data.get('hum', data.get('humidity'))
        smoke_val = data.get('smoke', data.get('mq2'))
        mq7_val = data.get('mq7')
        mq135_val = data.get('mq135')
        blocked_val = data.get('blocked', False)

        temp = float(temp_val) if temp_val is not None else None
        humidity = float(hum_val) if hum_val is not None else None
        smoke = int(smoke_val) if smoke_val is not None else None
        mq7 = int(mq7_val) if mq7_val is not None else None
        mq135 = int(mq135_val) if mq135_val is not None else None
        blocked = bool(blocked_val)

        reading = ZoneReading(
            zone_id=zone_id,
            name=ZONE_CONFIG[zone_id]['name'],
            temp=round(temp, 1) if temp is not None else None,
            smoke=max(0, smoke) if smoke is not None else None,
            humidity=round(max(0, min(100, humidity)), 1) if humidity is not None else None,
            mq7=mq7,
            mq135=mq135,
            blocked=blocked,
            timestamp=time.time(),
            online=(temp is not None and smoke is not None)
        )

        # Store and immediately push to app_state
        with self._lock:
            self._mqtt_readings[zone_id] = reading

        app_state.update_zone(reading)

        now = time.time()
        if blocked:
            if zone_id not in self._obstacle_start_times:
                self._obstacle_start_times[zone_id] = now
            
            obstacle_duration = now - self._obstacle_start_times[zone_id]
            # Trigger crisis layout & camera pop-up ONLY after 10.0 seconds of continuous obstruction
            if obstacle_duration >= 10.0:
                app_state.set_alert_active(True)
                app_state.update_layout('crisis', focused_zone=zone_id)
        else:
            self._obstacle_start_times.pop(zone_id, None)

        if (smoke is not None and smoke > 80) or (temp is not None and temp > 45):
            app_state.set_alert_active(True)
            app_state.update_layout('crisis', focused_zone=zone_id)

    def _handle_status_message(self, topic: str, payload: str):
        """
        Handle ESP32 online/offline status messages (including LWT).

        Expected topic: sentinel/status/<zone_id>
        Expected JSON:  {"zone":"chem_lab","online":true,"ip":"192.168.1.50","rssi":-45}
                    or  {"zone":"chem_lab","online":false}  (LWT — ESP32 died)
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return

        parts = topic.split('/')
        zone_id = data.get('zone', parts[-1] if len(parts) > 2 else 'chem_lab')
        if not zone_id or zone_id == 'status':
            zone_id = 'chem_lab'
        online = data.get('online', False)

        with self._lock:
            self._esp32_status[zone_id] = {
                'online': online,
                'ip': data.get('ip', ''),
                'rssi': data.get('rssi', 0),
                'uptime': data.get('uptime', 0),
                'last_seen': time.time(),
            }

        zone_name = ZONE_CONFIG.get(zone_id, {}).get('name', zone_id)

        if online:
            ip = data.get('ip', 'unknown')
            rssi = data.get('rssi', '?')
            logger.info(f"[MqttBridge] ESP32 ONLINE: {zone_name} (IP: {ip}, RSSI: {rssi})")
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description=f"📡 ESP32 node online: {zone_name} (IP: {ip})",
                severity='info',
                zone_id=zone_id,
            ))
        else:
            logger.warning(f"[MqttBridge] ESP32 OFFLINE: {zone_name} (LWT received)")
            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description=f"🔴 ESP32 node OFFLINE: {zone_name} — sensor data will use simulator fallback",
                severity='warning',
                zone_id=zone_id,
            ))

    # ── Background Fill Thread ────────────────────────────────────────────

    def _start_fill_thread(self):
        """Start a background thread that fills missing zones from the simulator."""
        self._fill_thread = threading.Thread(
            target=self._fill_loop,
            name='MqttBridge-Fill',
            daemon=True,
        )
        self._fill_thread.start()

    def _fill_loop(self):
        """
        Periodically check for stale MQTT readings and mark them offline (Honesty Rule).
        """
        logger.info("[MqttBridge] Staleness and health check thread started.")

        while not self._stop_event.is_set():
            try:
                now = time.time()
                stale_cutoff = now - 10.0
                with self._lock:
                    # Check 10s continuous obstacle threshold in background thread
                    for zone_id, start_time in list(self._obstacle_start_times.items()):
                        if now - start_time >= 10.0:
                            app_state.set_alert_active(True)
                            app_state.update_layout('crisis', focused_zone=zone_id)

                with app_state._lock:
                    for zone_id, reading in list(app_state.zones.items()):
                        # Only mark offline if it's currently online and has stale data
                        if reading.online and reading.timestamp > 0 and (reading.timestamp < stale_cutoff):
                            reading.online = False
                            reading.temp = None
                            reading.smoke = None
                            reading.humidity = None
                            logger.warning(f"[MqttBridge] Zone {zone_id} sensor STALE/DISCONNECTED. Marking offline.")
                            app_state.add_timeline_event(TimelineEvent(
                                event_type='alert',
                                description=f"🔌 Zone {reading.name} sensor link offline (no data >10s)",
                                severity='warning',
                                zone_id=zone_id
                            ))
            except Exception as e:
                logger.error(f"[MqttBridge] Staleness check thread error: {e}")

            self._stop_event.wait(self.FILL_INTERVAL)

    # ── Status Properties ─────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """Is the MQTT broker connection active?"""
        return self._connected

    def get_esp32_status(self) -> dict:
        """Get the online/offline status of all ESP32 nodes."""
        with self._lock:
            return dict(self._esp32_status)

    def get_mqtt_zone_count(self) -> int:
        """How many zones are currently receiving live MQTT data?"""
        with self._lock:
            stale_cutoff = time.time() - 10.0
            return sum(
                1 for r in self._mqtt_readings.values()
                if r.timestamp >= stale_cutoff
            )

    def _handle_rover_sensor_message(self, data: dict):
        """Parse sensor telemetry from the rover and update app_state.rover."""
        try:
            temp_val = data.get('temp')
            hum_val = data.get('hum', data.get('humidity'))
            smoke_val = data.get('smoke')
            blocked_val = data.get('blocked')
            mq7_val = data.get('mq7')
            mq135_val = data.get('mq135')
            uptime_val = data.get('uptime')
            rssi_val = data.get('rssi')

            rover_sensors = {
                'temp': float(temp_val) if temp_val is not None else None,
                'humidity': float(hum_val) if hum_val is not None else None,
                'smoke': int(smoke_val) if smoke_val is not None else None,
                'blocked': bool(blocked_val) if blocked_val is not None else None,
                'mq7': int(mq7_val) if mq7_val is not None else None,
                'mq135': int(mq135_val) if mq135_val is not None else None,
                'uptime': int(uptime_val) if uptime_val is not None else None,
                'rssi': int(rssi_val) if rssi_val is not None else None,
                'source': 'mqtt',
                'last_seen': time.time()
            }

            with app_state._lock:
                app_state.rover.sensors = rover_sensors

            logger.info(f"[MqttBridge] Rover sensors updated: {rover_sensors}")

        except Exception as e:
            logger.error(f"[MqttBridge] Error parsing rover sensors: {e}")
