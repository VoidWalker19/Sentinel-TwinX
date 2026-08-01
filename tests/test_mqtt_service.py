import json
import time
import pytest
from unittest.mock import MagicMock, patch

from server.services.mqtt_service.service import MqttService
from server.state import app_state, ZoneReading
from engine.config_loader import ZONE_CONFIG

def test_mqtt_service_config_loading():
    """Verify MqttService dynamically resolves credentials from ConfigurationService on start."""
    mock_config_service = MagicMock()
    mock_config_service.get_env_var.side_effect = lambda key, default=None: {
        "MQTT_BROKER": "10.0.0.10",
        "MQTT_PORT": "1883",
        "MQTT_USER": "test_user",
        "MQTT_PASS": "test_pass"
    }.get(key, default)

    # Mock registry lookups
    with patch("server.services.registry.get", return_value=mock_config_service):
        with patch("paho.mqtt.client.Client") as mock_paho_client:
            service = MqttService()
            # Mock client interactions
            service._on_start()
            
            # Assert loaded settings
            assert service.broker_host == "10.0.0.10"
            assert service.broker_port == 1883
            assert service.username == "test_user"
            assert service.password == "test_pass"

def test_mqtt_service_structured_sensor_stream():
    """Verify that structured sensor telemetry is parsed and updates app_state.zones."""
    service = MqttService()
    
    # 1. Zone Reading Ingestion
    telemetry_payload = {
        "zone": "classroom_a",
        "temp": 22.3,
        "smoke": 45,
        "hum": 40.5,
        "blocked": False,
        "uptime": 500,
        "rssi": -60
    }
    
    service._process_structured_message("sentinel/sensors/classroom_a", telemetry_payload)
    
    zone_reading = app_state.zones["classroom_a"]
    assert zone_reading.temp == 22.3
    assert zone_reading.smoke == 45
    assert zone_reading.humidity == 40.5
    assert zone_reading.blocked is False
    assert zone_reading.online is True

    # 2. Rover Sensors Ingestion
    rover_payload = {
        "zone": "rover",
        "temp": 24.0,
        "hum": 50.0,
        "smoke": 10,
        "blocked": True,
        "mq7": 20,
        "mq135": 85,
        "uptime": 1200,
        "rssi": -70
    }
    
    service._process_structured_message("sentinel/sensors/rover", rover_payload)
    
    rover_sensors = app_state.rover.sensors
    assert rover_sensors["temp"] == 24.0
    assert rover_sensors["humidity"] == 50.0
    assert rover_sensors["blocked"] is True
    assert rover_sensors["mq7"] == 20
    assert rover_sensors["mq135"] == 85
    assert rover_sensors["source"] == "mqtt"

def test_mqtt_service_status_and_ack_routing():
    """Verify that node status and command acknowledgments generate timeline events."""
    service = MqttService()
    
    # Clear timeline
    app_state.timeline = []
    
    # 1. Online Heartbeat Event
    status_payload = {
        "zone": "server",
        "online": True,
        "ip": "192.168.1.99",
        "rssi": -40,
        "uptime": 2000,
        "free_heap": 180000,
        "fw_ver": "2.0.0",
        "health": "OK"
    }
    
    service._process_structured_message("sentinel/status/server", status_payload)
    
    # Check timeline for online connection log
    assert len(app_state.timeline) > 0
    online_event = app_state.timeline[0]
    assert "online: Server Room" in online_event.description
    assert online_event.zone_id == "server"
    
    # 2. Command Acknowledgment Ingestion
    ack_payload = {
        "cmd": "buzzer_on",
        "status": "ACK",
        "msg": "Buzzer activated successfully"
    }
    
    service._process_structured_message("sentinel/ack/server", ack_payload)
    
    ack_event = app_state.timeline[0]
    assert "ACK: buzzer_on" in ack_event.description
    assert "Buzzer activated" in ack_event.description
    assert ack_event.zone_id == "server"


def test_mqtt_service_rover_commands():
    """Verify publishing rover commands to topic sentinel/commands/rover with exact JSON payloads."""
    service = MqttService()
    service._connected = True
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.rc = 0
    mock_client.publish.return_value = mock_res
    service._client = mock_client

    commands = ["start", "pause", "stop", "emergency"]
    for cmd in commands:
        payload = json.dumps({"command": cmd})
        res = service.publish("sentinel/commands/rover", payload)
        assert res is True
        mock_client.publish.assert_called_with("sentinel/commands/rover", payload, qos=1, retain=False)

