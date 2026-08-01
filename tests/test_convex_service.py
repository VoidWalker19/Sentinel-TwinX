import pytest
from unittest.mock import patch, MagicMock
from server.services.convex_service.service import ConvexService
import time

@patch("server.services.convex_service.service.requests")
def test_convex_service_sync_flows(mock_requests):
    """Verify ConvexService puts items into queue and sends request.post correctly."""
    # Mock successful HTTP 200 responses
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.post.return_value = mock_response

    # Initialize with mock url
    with patch.dict("os.environ", {"CONVEX_URL": "https://mock-convex-cloud.convex.cloud"}):
        service = ConvexService()
        assert service.start() is True
        
        # Sync sensor readings
        service.sync_sensor_reading("classroom_a", 24.5, 120, 45.0, False)
        # Sync alerts
        service.sync_alert("classroom_a", 15, "green", "Clear")
        # Sync rover status
        service.sync_rover_status("patrolling", 85, 1.2, 3.4, -65, 1200)
        # Sync camera event
        service.sync_camera_event("motion", 0.98, "/images/cam1.jpg")
        # Sync AI reports
        service.sync_ai_report("Summary", "Analysis", "LOW", "95%", "[]")
        # Sync missions
        service.sync_mission("m1", "inspection", "active", ["classroom_a"], 2)
        # Sync battery
        service.sync_battery_history(3.9, 78.0)
        
        # Allow background queue worker time to process items
        time.sleep(0.3)
        
        assert service.stop() is True
        
        # Verify requests.post was called for each synced collection
        assert mock_requests.post.call_count >= 7
        
        # Verify URL matching
        endpoints = [call[0][0] for call in mock_requests.post.call_args_list]
        assert any("sync_sensor_readings" in ep for ep in endpoints)
        assert any("sync_alert" in ep for ep in endpoints)
        assert any("sync_rover_status" in ep for ep in endpoints)
        assert any("sync_camera_event" in ep for ep in endpoints)
        assert any("sync_ai_report" in ep for ep in endpoints)
        assert any("sync_mission" in ep for ep in endpoints)
        assert any("sync_battery_history" in ep for ep in endpoints)
