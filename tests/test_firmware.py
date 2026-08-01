import json
import time
import pytest
from unittest.mock import MagicMock

from server.state import app_state, ZoneReading
from server.mqtt_bridge import MqttBridge
from engine.chronos import ZONE_CONFIG

def test_telemetry_payload_compatibility():
    """Verify that the FastAPI AppState accepts telemetry formatted exactly like our new ESP32 firmware."""
    bridge = MqttBridge()

    # 1. Telemetry Payload from a Room (e.g. Chem Lab)
    chem_lab_payload = json.dumps({
        "zone": "chem_lab",
        "temp": 24.5,
        "smoke": 120,
        "hum": 55.4,
        "blocked": False,
        "uptime": 3600,
        "rssi": -65,
        "mq7": 85,
        "mq135": 140,
        "battery_v": 7.45,
        "battery_pct": 82,
        "loop_hz": 15000
    })

    # Simulate receiving sensor message on MQTT topic
    bridge._handle_sensor_message("sentinel/sensors/chem_lab", chem_lab_payload)

    # Assert the zone state was updated correctly
    zone_reading = app_state.zones["chem_lab"]
    assert zone_reading.temp == 24.5
    assert zone_reading.smoke == 120
    assert zone_reading.humidity == 55.4
    assert zone_reading.blocked is False
    assert zone_reading.online is True

    # 2. Telemetry Payload from the Rover Node
    rover_payload = json.dumps({
        "zone": "rover",
        "temp": 28.1,
        "smoke": 40,
        "hum": 42.0,
        "blocked": True,
        "uptime": 7200,
        "rssi": -72,
        "mq7": 12,
        "mq135": 95,
        "battery_v": 11.2,
        "battery_pct": 74,
        "loop_hz": 14200
    })

    bridge._handle_sensor_message("sentinel/sensors/rover", rover_payload)

    # Assert rover sensor state was updated correctly
    rover_sensors = app_state.rover.sensors
    assert rover_sensors["temp"] == 28.1
    assert rover_sensors["humidity"] == 42.0
    assert rover_sensors["smoke"] == 40
    assert rover_sensors["blocked"] is True
    assert rover_sensors["mq7"] == 12
    assert rover_sensors["mq135"] == 95
    assert rover_sensors["uptime"] == 7200
    assert rover_sensors["rssi"] == -72
    assert rover_sensors["source"] == "mqtt"

def test_heartbeat_payload_compatibility():
    """Verify that status and heartbeat payloads are processed correctly by MqttBridge."""
    bridge = MqttBridge()

    # Status heartbeat payload with new diagnostic metrics (fw_ver, health)
    heartbeat_payload = json.dumps({
        "zone": "chem_lab",
        "online": True,
        "ip": "192.168.1.55",
        "rssi": -55,
        "uptime": 12000,
        "free_heap": 210000,
        "buzzer": False,
        "battery_v": 7.82,
        "battery_pct": 90,
        "loop_hz": 14900,
        "wifi_cycles": 1,
        "mqtt_cycles": 2,
        "fw_ver": "2.0.0",
        "health": "OK"
    })

    bridge._handle_status_message("sentinel/status/chem_lab", heartbeat_payload)

    # Assert status history is updated in bridge state
    status_entry = bridge._esp32_status["chem_lab"]
    assert status_entry["online"] is True
    assert status_entry["ip"] == "192.168.1.55"
    assert status_entry["rssi"] == -55
    assert status_entry["uptime"] == 12000

def test_custom_json_value_extractor():
    """
    Verify that our custom C++ style substring-based JSON value extractor logic
    runs correctly for all command schemas. We mock it in Python to validate parser logic correctness.
    """
    def extract_json_value_py(json_str, key):
        search_key = f'"{key}"'
        key_idx = json_str.find(search_key)
        if key_idx == -1:
            return ""
        
        colon_idx = json_str.find(':', key_idx + len(search_key))
        if colon_idx == -1:
            return ""
        
        val_start = colon_idx + 1
        while val_start < len(json_str) and json_str[val_start] in (' ', '\t', '\r', '\n'):
            val_start += 1
            
        if val_start >= len(json_str):
            return ""
            
        if json_str[val_start] == '"':
            val_end = json_str.find('"', val_start + 1)
            if val_end == -1:
                return ""
            return json_str[val_start + 1:val_end]
        else:
            val_end = val_start
            while val_end < len(json_str) and json_str[val_end] not in (',', '}', ']', ' ', '\r', '\n'):
                val_end += 1
            return json_str[val_start:val_end]

    # Test cases representing various formats sent by the server or user CLI
    payload1 = '{"cmd": "buzzer_on"}'
    payload2 = '{"cmd":"set_config", "key":"motor_speed", "value":"200"}'
    payload3 = '{\n  "type": "rover_dispatched",\n  "zone": "chem_lab"\n}'

    assert extract_json_value_py(payload1, "cmd") == "buzzer_on"
    assert extract_json_value_py(payload2, "cmd") == "set_config"
    assert extract_json_value_py(payload2, "key") == "motor_speed"
    assert extract_json_value_py(payload2, "value") == "200"
    assert extract_json_value_py(payload3, "type") == "rover_dispatched"
    assert extract_json_value_py(payload3, "zone") == "chem_lab"
    assert extract_json_value_py(payload1, "non_existent") == ""
