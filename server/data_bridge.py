"""
server/data_bridge.py — Data Bridge (Serial ↔ Simulator → State)

This module connects the sensor data source to the shared state.
It runs in a background thread and updates `app_state.zones` every 2 seconds.

Two modes:
1. SimBridge — reads from the software simulator (no hardware needed)
2. SerialBridge — reads JSON lines from an ESP32 over USB/UART serial

Both produce identical ZoneReading objects so the rest of the system
doesn't care which mode is active.
"""

import json
import time
import threading
import logging
from typing import Optional
from server.state import app_state, ZoneReading, TimelineEvent
from simulator.sensor_sim import sensor_simulator
from engine.chronos import ZONE_CONFIG


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Base bridge
# ─────────────────────────────────────────────────────────────────────────────

class DataBridge(threading.Thread):
    """
    Abstract background thread that feeds sensor data into app_state.
    Subclasses override _fetch_readings() with the actual data source.
    """

    TICK_INTERVAL = 2.0   # Seconds between sensor reads

    def __init__(self, name: str = 'DataBridge'):
        super().__init__(name=name, daemon=True)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info(f"[{self.name}] Starting data bridge loop")
        while not self._stop_event.is_set():
            try:
                readings = self._fetch_readings() or {}
                if isinstance(self, SimBridge):
                    for zone_id, sim_reading in readings.items():
                        app_state.update_zone(sim_reading)
                else:
                    for zone_id, reading in readings.items():
                        if reading is not None:
                            app_state.update_zone(reading)
            except Exception as e:
                logger.error(f"[{self.name}] Error fetching readings: {e}")

            poll_rate = app_state.settings.get('sensor_poll_rate', 2.0)
            time.sleep(poll_rate)

    def _fetch_readings(self) -> Optional[dict]:
        """Override in subclass. Return dict of zone_id → ZoneReading."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# SimBridge — uses the software simulator
# ─────────────────────────────────────────────────────────────────────────────

class SimBridge(DataBridge):
    """
    Reads from the sensor simulator.
    No hardware required — perfect for demos and development.
    """

    def __init__(self):
        super().__init__(name='SimBridge')

    def _fetch_readings(self) -> dict:
        return sensor_simulator.get_all_readings()


# ─────────────────────────────────────────────────────────────────────────────
# SerialBridge — reads JSON from ESP32 over USB
# ─────────────────────────────────────────────────────────────────────────────

class SerialBridge(DataBridge):
    """
    Reads sensor JSON from an ESP32 connected over USB serial.

    Expected JSON format (one line per reading):
        {"zone":"chem_lab","temp":28.5,"smoke":48,"hum":54.2,"blocked":false}

    If a zone is missing from the serial stream, we fill in from the
    simulator so the map always shows all 10 zones.
    """

    def __init__(self, port: str = 'COM3', baud: int = 115200):
        super().__init__(name='SerialBridge')
        self.port = port
        self.baud = baud
        self._serial = None
        self._buffer = {}    # Accumulate readings per tick

    def _connect(self):
        """Try to open the serial port. Logs but doesn't crash on failure."""
        try:
            import serial
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            logger.info(f"[SerialBridge] Connected to {self.port} @ {self.baud} baud")
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description=f"ESP32 connected on {self.port}",
                severity='info',
            ))
        except Exception as e:
            logger.warning(f"[SerialBridge] Cannot open {self.port}: {e}")
            self._serial = None

    def _parse_line(self, line: str) -> Optional[ZoneReading]:
        """
        Parse one JSON line from the ESP32.

        Expected keys: zone, temp, smoke, hum, blocked
        Returns None on any parse error (never crashes).
        """
        try:
            line = line.strip()
            if not line or not line.startswith('{'):
                return None

            data = json.loads(line)

            zone_id = str(data.get('zone', '')).lower().replace(' ', '_')
            if zone_id not in ZONE_CONFIG:
                # Try partial match (ESP32 might send "laboratory" for "chem_lab")
                for known_id in ZONE_CONFIG:
                    if known_id.startswith(zone_id[:4]) or zone_id.startswith(known_id[:4]):
                        zone_id = known_id
                        break
                else:
                    return None

            return ZoneReading(
                zone_id=zone_id,
                name=ZONE_CONFIG[zone_id]['name'],
                temp=float(data.get('temp', 25.0)),
                smoke=int(data.get('smoke', 20)),
                humidity=float(data.get('hum', 60.0)),
                blocked=bool(data.get('blocked', False)),
                timestamp=time.time(),
            )
        except Exception as e:
            logger.debug(f"[SerialBridge] Bad line: {line!r} → {e}")
            return None

    def _fetch_readings(self) -> dict:
        """
        Read all available lines from serial.
        """
        # Try to connect if not connected
        if self._serial is None:
            self._connect()

        received: dict = {}

        if self._serial and self._serial.is_open:
            try:
                # Drain all waiting lines in this tick window
                while self._serial.in_waiting:
                    raw = self._serial.readline().decode('utf-8', errors='ignore')
                    reading = self._parse_line(raw)
                    if reading:
                        received[reading.zone_id] = reading
            except Exception as e:
                logger.warning(f"[SerialBridge] Read error: {e}")
                self._serial = None   # Will reconnect next tick

        return received


# ─────────────────────────────────────────────────────────────────────────────
# Factory function
# ─────────────────────────────────────────────────────────────────────────────

def create_bridge(mode: str, port: str = 'COM3'):
    """
    Create the appropriate data bridge based on the mode string.

    Args:
        mode: 'sim', 'serial', or 'mqtt'
        port: Serial port name (only used in serial mode)

    Returns:
        A bridge instance (not yet started). Call .start() to begin.
    """
    if mode == 'mqtt':
        from server.mqtt_bridge import MqttBridge
        import os
        broker_host = os.getenv('MQTT_BROKER', 'sentinelpi.local')
        broker_port = int(os.getenv('MQTT_PORT', '1883'))
        mqtt_user = os.getenv('MQTT_USER', '')
        mqtt_pass = os.getenv('MQTT_PASS', '')
        logger.info(f"Using MqttBridge → broker at {broker_host}:{broker_port}")
        bridge = MqttBridge(
            broker_host=broker_host,
            broker_port=broker_port,
            username=mqtt_user,
            password=mqtt_pass,
        )
        app_state.port = f"{broker_host}:{broker_port}"
    elif mode == 'serial':
        logger.info(f"Using SerialBridge on port {port}")
        bridge = SerialBridge(port=port)
        app_state.port = port
    else:
        logger.info("Using SimBridge (software simulator)")
        bridge = SimBridge()
        app_state.port = 'SIMULATED'

    app_state.mode = mode
    return bridge
