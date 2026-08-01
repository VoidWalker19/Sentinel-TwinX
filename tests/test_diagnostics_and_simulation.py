import time
import pytest
from server.services import registry
from server.state import app_state, ZoneReading

@pytest.fixture(autouse=True)
def setup_services():
    app_state.reset_simulated_state()
    registry.start_all()
    yield
    registry.stop_all()
    app_state.reset_simulated_state()


def test_diagnostics_self_tests():
    # Retrieve diagnostics service
    diag_srv = registry.get("DiagnosticsService")
    assert diag_srv is not None
    
    # Run self tests
    report = diag_srv.run_self_tests()
    assert isinstance(report, dict)
    assert "wifi" in report
    assert "mqtt" in report
    assert "database" in report
    assert "convex" in report
    assert "camera" in report

def test_simulation_wifi_and_mqtt_loss():
    diag_srv = registry.get("DiagnosticsService")
    mqtt_srv = registry.get("MqttService")
    convex_srv = registry.get("ConvexService")
    
    # Initially active
    diag_srv.set_simulation("wifi_loss", False)
    diag_srv.set_simulation("mqtt_loss", False)
    
    assert diag_srv.get_simulation("wifi_loss") is False
    
    # Enable WiFi loss simulation
    diag_srv.set_simulation("wifi_loss", True)
    assert diag_srv.get_simulation("wifi_loss") is True
    
    # Verify WiFi loss is reported
    report = diag_srv.run_self_tests()
    assert report["wifi"]["status"] == "FAIL"
    assert report["convex"]["status"] == "FAIL"
    
    # MQTT should also return not connected due to WiFi loss
    if mqtt_srv:
        assert mqtt_srv.is_connected() is False
    if convex_srv:
        assert convex_srv.is_connected() is False
        
    # Disable WiFi loss, enable MQTT loss
    diag_srv.set_simulation("wifi_loss", False)
    diag_srv.set_simulation("mqtt_loss", True)
    
    report = diag_srv.run_self_tests()
    assert report["wifi"]["status"] == "PASS"
    assert report["mqtt"]["status"] == "FAIL"
    
    # Reset
    diag_srv.set_simulation("mqtt_loss", False)

def test_simulation_camera_failure():
    diag_srv = registry.get("DiagnosticsService")
    cam_srv = registry.get("CameraService")
    
    diag_srv.set_simulation("camera_failure", True)
    report = diag_srv.run_self_tests()
    assert report["camera"]["status"] == "FAIL"
    
    if cam_srv:
        assert cam_srv.get_latest_frame() is None
        
    diag_srv.set_simulation("camera_failure", False)

def test_simulation_low_battery():
    diag_srv = registry.get("DiagnosticsService")
    diag_srv.set_simulation("low_battery", True)
    
    # Sleep briefly to let diagnostics loop update the state
    time.sleep(1.2)
    assert app_state.rover.battery_pct == 12.5
    
    diag_srv.set_simulation("low_battery", False)

def test_simulation_navigation_blockage():
    diag_srv = registry.get("DiagnosticsService")
    nav_srv = registry.get("NavigationService")
    
    diag_srv.set_simulation("navigation_blockage", True)
    
    if nav_srv:
        path = nav_srv.find_rover_path("classroom_1", "chem_lab")
        # Corridor is blocked, so path from classroom_1 to chem_lab should fail
        assert len(path) == 0
        
    diag_srv.set_simulation("navigation_blockage", False)


def test_simulation_sensor_failure():
    diag_srv = registry.get("DiagnosticsService")
    
    diag_srv.set_simulation("sensor_failure", {"lobby": True})
    time.sleep(1.2)
    
    # Test reading override
    reading = ZoneReading(zone_id="lobby", name="Lobby", temp=22.0, smoke=10, humidity=40.0)
    app_state.update_zone(reading)
    
    # The reading values should have been overridden to failure mode
    assert reading.temp == 99.9
    assert reading.smoke == 9999
    
    diag_srv.set_simulation("sensor_failure", {"lobby": False})
    time.sleep(1.2)
    
    reading2 = ZoneReading(zone_id="lobby", name="Lobby", temp=22.0, smoke=10, humidity=40.0)
    app_state.update_zone(reading2)
    assert reading2.temp == 22.0
