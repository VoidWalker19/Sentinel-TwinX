import time
import json
import logging
from typing import Dict, Any, Callable, Optional
from server.services.base_service import BaseService
from server.state import app_state, ZoneReading, TimelineEvent
from engine.config_loader import ZONE_CONFIG

class MqttService(BaseService):
    """
    Service responsible for connecting to the Mosquitto MQTT broker,
    subscribing to telemetry channels, and dispatching command requests.
    """
    def __init__(self, config: dict = None):
        super().__init__("MqttService", config)
        self.broker_host = self.config.get("broker_host", "sentinelpi.local")
        self.broker_port = self.config.get("broker_port", 9001)
        self.username = self.config.get("username", "")
        self.password = self.config.get("password", "")
        self.client_id = self.config.get("client_id", f"sentinel-twin-server-{int(time.time())}")

        self._client = None
        self._connected = False
        self._on_message_callback: Optional[Callable[[str, dict], None]] = None
        self._on_status_callback: Optional[Callable[[str, dict], None]] = None
        self._node_statuses: Dict[str, dict] = {}

    def set_callbacks(self, on_message: Callable[[str, dict], None], on_status: Callable[[str, dict], None]):
        self._on_message_callback = on_message
        self._on_status_callback = on_status

    def _on_start(self) -> bool:
        try:
            import paho.mqtt.client as paho_mqtt
        except ImportError:
            self.logger.error("paho-mqtt not installed! Run: pip install paho-mqtt>=2.0.0")
            return False

        # Load dynamic configurations from registry configuration service if available
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        if cfg_srv:
            self.broker_host = cfg_srv.get_env_var("MQTT_BROKER", self.broker_host)
            self.broker_port = int(cfg_srv.get_env_var("MQTT_PORT", str(self.broker_port)))
            self.username = cfg_srv.get_env_var("MQTT_USER", self.username)
            self.password = cfg_srv.get_env_var("MQTT_PASS", self.password)

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

        try:
            self._client = paho_mqtt.Client(
                callback_api_version=paho_mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
                clean_session=True,
                transport=transport,
            )
        except (AttributeError, TypeError):
            self._client = paho_mqtt.Client(
                client_id=self.client_id,
                clean_session=True,
                transport=transport,
            )

        if self.username:
            self._client.username_pw_set(self.username, self.password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Set Last Will
        lwt_topic = "sentinel/server/status"
        self._client.will_set(lwt_topic, json.dumps({"online": False}), qos=1, retain=True)

        self.logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
        try:
            self._client.connect_async(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
            return True
        except Exception as e:
            self.logger.error(f"Failed to start async MQTT connection: {e}")
            return False

    def _on_stop(self) -> bool:
        if self._client:
            self.logger.info("Stopping MQTT client loop...")
            self._client.publish("sentinel/server/status", json.dumps({"online": False}), qos=1, retain=True)
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
        return True

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        status_code = getattr(rc, "value", rc)
        if status_code == 0:
            self._connected = True
            self.logger.info("MQTT connected successfully to broker.")
            self._client.publish("sentinel/server/status", json.dumps({"online": True}), qos=1, retain=True)
            
            # Subscribe to all structured topics
            topics = [
                ("sentinel/sensors/#", 1),
                ("sentinel/sensors", 1),
                ("sentinel/status/#", 1),
                ("sentinel/status", 1),
                ("sentinel/ack/#", 1),
                ("sentinel/diagnostics/#", 1),
                ("sentinel/battery/#", 1),
                ("sentinel/camera/events", 1),
                ("sentinel/alerts/#", 1),
                ("sentinel/missions/#", 1),
                ("sentinel/navigation/#", 1)
            ]
            self._client.subscribe(topics)
            self.logger.info("Subscribed to structured sentinel/# topics.")
        else:
            self._connected = False
            self.logger.error(f"MQTT connection refused with reason code: {rc}")

    def _on_disconnect(self, client, userdata, disconnect_flags, rc, properties=None):
        self._connected = False
        self.logger.warning(f"MQTT client disconnected: {rc}")

    def _on_message(self, client, userdata, message):
        if not self.is_connected():
            return
        payload = message.payload.decode('utf-8', errors='ignore')
        topic = message.topic
        
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self.logger.warning(f"MQTT message payload not JSON: {payload} on topic {topic}")
            return

        # Trigger user-defined legacy callbacks
        if topic.startswith("sentinel/sensors"):
            parts = topic.split("/")
            zone_id = parts[-1] if len(parts) > 2 else "chem_lab"
            if self._on_message_callback:
                try:
                    self._on_message_callback(zone_id, data)
                except Exception as e:
                    self.logger.error(f"Error executing on_message callback for zone {zone_id}: {e}")
        elif topic.startswith("sentinel/status"):
            parts = topic.split("/")
            zone_id = parts[-1] if len(parts) > 2 else "chem_lab"
            if self._on_status_callback:
                try:
                    self._on_status_callback(zone_id, data)
                except Exception as e:
                    self.logger.error(f"Error executing on_status callback for zone {zone_id}: {e}")

        # Core state updates (automatic state ingestion)
        try:
            self._process_structured_message(topic, data)
        except Exception as e:
            self.logger.error(f"Error in automatic state ingestion for {topic}: {e}")

    def _process_structured_message(self, topic: str, data: dict):
        parts = topic.split('/')
        if len(parts) < 2:
            return

        prefix = parts[1]
        zone_id = parts[2] if len(parts) > 2 else 'chem_lab'

        if prefix == 'sensors':
            payload_zone = str(data.get('zone', zone_id)).lower().replace(' ', '_')
            
            if payload_zone == 'rover' or zone_id == 'rover':
                self._update_rover_sensors(data)
                return

            if payload_zone == 'classroom_a':
                if 'classroom_a' not in ZONE_CONFIG:
                    ZONE_CONFIG['classroom_a'] = {
                        'name': 'Classroom A',
                        'floor': 2,
                        'high_risk_baseline': False
                    }

            if payload_zone in ZONE_CONFIG:
                zone_id = payload_zone
            elif zone_id not in ZONE_CONFIG:
                for known_id in ZONE_CONFIG:
                    if (zone_id and known_id.startswith(zone_id[:4])) or \
                       (zone_id and zone_id.startswith(known_id[:4])):
                        zone_id = known_id
                        break
                else:
                    return

            temp_val = data.get('temp')
            hum_val = data.get('hum', data.get('humidity'))
            smoke_val = data.get('smoke', data.get('mq2'))
            mq7_val = data.get('mq7')
            mq135_val = data.get('mq135')
            blocked_val = data.get('blocked', data.get('obstacle', False))

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
            app_state.update_zone(reading)
            if reading.online:
                self._node_statuses[zone_id] = {
                    'online': True,
                    'ip': 'unknown',
                    'rssi': 0,
                    'uptime': 0,
                    'fw_ver': '2.0.0',
                    'health': 'OK',
                    'last_seen': time.time(),
                }

        elif prefix == 'status':
            if zone_id == 'server':
                if 'server' not in ZONE_CONFIG:
                    ZONE_CONFIG['server'] = {
                        'name': 'Server Room',
                        'floor': 1,
                        'high_risk_baseline': True
                    }

            online = bool(data.get('online', False))
            fw_ver = data.get('fw_ver', '2.0.0')
            health = data.get('health', 'OK')
            ip = data.get('ip', 'unknown')
            rssi = int(data.get('rssi', 0))
            uptime = int(data.get('uptime', 0))

            status_entry = {
                'online': online,
                'ip': ip,
                'rssi': rssi,
                'uptime': uptime,
                'fw_ver': fw_ver,
                'health': health,
                'last_seen': time.time(),
            }
            
            zone_name = ZONE_CONFIG.get(zone_id, {}).get('name', zone_id)
            prev_online = self._node_statuses.get(zone_id, {}).get('online', False)
            self._node_statuses[zone_id] = status_entry

            if online != prev_online:
                if online:
                    self.logger.info(f"ESP32 Node {zone_name} online (IP: {ip}, RSSI: {rssi})")
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='info',
                        description=f"📡 ESP32 node online: {zone_name} (v{fw_ver}, health: {health})",
                        severity='info',
                        zone_id=zone_id,
                    ))
                else:
                    self.logger.warning(f"ESP32 Node {zone_name} went offline")
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='alert',
                        description=f"🔴 ESP32 node OFFLINE: {zone_name}",
                        severity='warning',
                        zone_id=zone_id,
                    ))

        elif prefix == 'ack':
            cmd = data.get('cmd', '')
            status = data.get('status', 'ACK')
            msg = data.get('msg', '')
            
            self.logger.info(f"Command ack from {zone_id}: {cmd} -> {status} ({msg})")
            
            if status == 'ACK':
                app_state.add_timeline_event(TimelineEvent(
                    event_type='info',
                    description=f"✅ ESP32 [{zone_id.upper()}] ACK: {cmd} - {msg}",
                    severity='info',
                    zone_id=zone_id,
                ))
            else:
                app_state.add_timeline_event(TimelineEvent(
                    event_type='alert',
                    description=f"❌ ESP32 [{zone_id.upper()}] ERROR: {cmd} - {msg}",
                    severity='warning',
                    zone_id=zone_id,
                ))

        elif prefix == 'battery':
            pct = int(data.get('battery_pct', 100))
            voltage = float(data.get('battery_v', 0.0))

            # Update rover battery level if this is from the rover node
            if zone_id == 'rover':
                with app_state._lock:
                    app_state.rover.battery_pct = float(pct)

            if pct < 20:
                app_state.add_timeline_event(TimelineEvent(
                    event_type='alert',
                    description=f"🔋 Low battery warning on [{zone_id.upper()}]: {pct}% ({voltage:.2f}V)",
                    severity='warning',
                    zone_id=zone_id,
                ))

        elif prefix == 'diagnostics':
            loop_hz = int(data.get('loop_hz', 0))
            free_heap = int(data.get('free_heap', 0))
            self.logger.debug(f"Diagnostics from {zone_id}: loop_hz={loop_hz}, free_heap={free_heap}")

        elif prefix == 'alerts':
            # External alert published by ESP32 or Raspberry Pi sub-system
            # Expected: {"zone": "chem_lab", "type": "fire", "severity": "critical", "msg": "...", "value": 128}
            alert_type = data.get('type', 'unknown')
            severity = data.get('severity', 'warning')
            msg = data.get('msg', data.get('message', f'Alert from {zone_id}'))
            value = data.get('value', '')
            value_str = f" (value: {value})" if value else ''
            severity_mapped = 'critical' if severity in ('critical', 'high') else 'warning' if severity == 'warning' else 'info'

            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description=f"⚠️ [{zone_id.upper()}] {alert_type.upper()}: {msg}{value_str}",
                severity=severity_mapped,
                zone_id=zone_id,
            ))
            self.logger.warning(f"External alert from ESP32 [{zone_id}]: type={alert_type}, severity={severity}, msg={msg}")

        elif prefix == 'missions':
            # Mission status broadcast from Raspberry Pi or central mission hub
            # Expected: {"mission_id": "abc123", "status": "ACTIVE", "zone": "chem_lab", "progress": 45}
            mission_id = data.get('mission_id', zone_id)
            status = data.get('status', '')
            mission_zone = data.get('zone', zone_id)
            progress = int(data.get('progress', 0))
            self.logger.info(f"Mission MQTT update: id={mission_id}, status={status}, zone={mission_zone}, progress={progress}%")

            from server.services import registry
            mission_srv = registry.get("MissionService")
            if mission_srv and hasattr(mission_srv, 'active_mission') and mission_srv.active_mission:
                active = mission_srv.active_mission
                # Only update if IDs match to prevent stale overrides
                if active.mission_id == mission_id or status in ('DONE', 'ABORTED'):
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='info',
                        description=f"📋 Mission [{mission_id}] status update: {status} ({progress}% complete)",
                        severity='info',
                        zone_id=mission_zone,
                    ))

        elif prefix == 'navigation':
            # Rover path/position updates from on-board navigation system
            # Expected: {"x": 385.0, "y": 225.0, "zone": "corridor", "heading": 90, "speed": 45}
            x = float(data.get('x', 0.0))
            y = float(data.get('y', 0.0))
            current_zone = data.get('zone', '')
            heading = float(data.get('heading', 0.0))
            speed = float(data.get('speed', 0.0))

            with app_state._lock:
                if x > 0 or y > 0:
                    app_state.rover.position = (x, y)
                if current_zone:
                    app_state.rover.current_zone = current_zone
                app_state.rover.speed = speed

            self.logger.debug(f"Navigation update: pos=({x:.1f},{y:.1f}), zone={current_zone}, heading={heading:.1f}°, speed={speed:.1f}cm/s")

    def _update_rover_sensors(self, data: dict):
        try:
            temp_val = data.get('temp')
            hum_val = data.get('hum', data.get('humidity'))
            smoke_val = data.get('smoke', data.get('mq2'))
            blocked_val = data.get('blocked', data.get('obstacle'))
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

            self.logger.info(f"Rover sensors updated via MQTT: {rover_sensors}")
        except Exception as e:
            self.logger.error(f"Error parsing rover sensors in MqttService: {e}")

    def publish_command(self, zone_id: str, cmd_type: str, params: dict = None) -> bool:
        """Publishes command packages to the rover."""
        if not self.is_connected() or not self._client:
            self.logger.warning(f"Cannot publish command {cmd_type} to zone {zone_id}: MQTT client disconnected.")
            return False

        topic = f"sentinel/commands/{zone_id}"
        payload_data = {"type": cmd_type}
        if params:
            payload_data.update(params)
        
        payload = json.dumps(payload_data)
        res = self._client.publish(topic, payload, qos=1)
        # In paho v2, res has rc parameter. Evaluate to 0 on success.
        status_code = getattr(res, "rc", res)
        if status_code == 0:
            self.logger.info(f"Published command '{cmd_type}' to topic {topic}")
            return True
        else:
            self.logger.error(f"Failed to publish command {cmd_type} to {topic} (rc={status_code})")
            return False

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        """Publishes a raw payload string to any MQTT topic."""
        if not self.is_connected() or not self._client:
            self.logger.warning(f"Cannot publish to {topic}: MQTT client disconnected.")
            return False

        res = self._client.publish(topic, payload, qos=qos, retain=retain)
        status_code = getattr(res, "rc", res)
        if status_code == 0:
            self.logger.info(f"Published payload to topic '{topic}': {payload}")
            return True
        else:
            self.logger.error(f"Failed to publish to '{topic}' (rc={status_code})")
            return False

    def is_connected(self) -> bool:
        """Returns True if MQTT broker connection is active and not suppressed by diagnostics."""
        from server.services import registry
        diag = registry.get("DiagnosticsService")
        if diag:
            if diag.get_simulation("wifi_loss") or diag.get_simulation("mqtt_loss"):
                return False
        return self._connected

    def get_node_statuses(self) -> dict:
        """Returns a copy of the tracked ESP32 node status map."""
        return dict(self._node_statuses)

    def get_last_heartbeat(self) -> float:
        """Returns the most recent last_seen timestamp across all known nodes. 0 if never connected."""
        if not self._node_statuses:
            return 0.0
        return max((v.get('last_seen', 0.0) for v in self._node_statuses.values()), default=0.0)
