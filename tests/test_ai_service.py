import time
import pytest
from unittest.mock import MagicMock, patch

from server.services.ai_service.service import AiService
from server.state import app_state, AIReport, ZoneReading, RoverState
from engine.config_loader import ZONE_CONFIG

def test_ai_service_lifecycle_and_config():
    """Verify AiService initializes correctly and retrieves dynamic configs."""
    mock_config_service = MagicMock()
    mock_config_service.get_env_var.side_effect = lambda key, default=None: {
        "GEMINI_API_KEY": "test-gemini-key-123"
    }.get(key, default)

    with patch("server.services.registry.get", return_value=mock_config_service):
        service = AiService()
        assert service._on_start() is True
        assert service._gemini_key == "test-gemini-key-123"
        assert service._on_stop() is True

def test_ai_service_local_fallback_rules():
    """Verify local deterministic rule fallback agent proposals."""
    service = AiService()
    service.start()
    
    # Setup safe snapshot
    safe_snapshot = {
        "overall_risk": 0,
        "system_status": "green",
        "zones": {
            "classroom_1": ZoneReading(zone_id="classroom_1", name="Classroom 1", temp=22.0, smoke=15, humidity=40.0, online=True).to_dict()
        },
        "risk_scores": {
            "classroom_1": {"score": 10, "status": "green", "reasons": []}
        },

        "rover": RoverState(status="idle", current_zone="corridor").to_dict(),
        "layout_mode": "standard",
        "alert_active": False
    }

    hazards = service.hazard_engine.analyze_snapshot(safe_snapshot)
    explanations = service.decision_engine.evaluate_actions(safe_snapshot, hazards)
    assert len(explanations) == 0  # No anomalies, no actions proposed

    # Setup high risk anomaly snapshot (trigger alarm & crisis view & dispatch rover)
    danger_snapshot = {
        "overall_risk": 85,
        "system_status": "red",
        "zones": {
            "classroom_1": ZoneReading(zone_id="classroom_1", name="Classroom 1", temp=55.0, smoke=350, humidity=20.0, online=True).to_dict()
        },
        "risk_scores": {
            "classroom_1": {"score": 85, "status": "red", "reasons": ["High Smoke Detected"]}
        },
        "rover": RoverState(status="idle", current_zone="corridor").to_dict(),
        "layout_mode": "standard",
        "alert_active": False
    }

    danger_hazards = service.hazard_engine.analyze_snapshot(danger_snapshot)
    danger_explanations = service.decision_engine.evaluate_actions(danger_snapshot, danger_hazards)
    actions = [de.action_name for de in danger_explanations]
    assert "set_alarm" in actions
    assert "dispatch_rover" in actions
    assert "set_layout" in actions
    service.stop()

def test_ai_service_rover_recall():
    """Verify local fallback recall proposals when rover finishes scanning."""
    service = AiService()
    service.start()

    recall_snapshot = {
        "overall_risk": 0,
        "system_status": "green",
        "zones": {
            "classroom_1": ZoneReading(zone_id="classroom_1", name="Classroom 1", temp=22.0, smoke=15, humidity=45.0, online=True).to_dict()
        },
        "risk_scores": {
            "classroom_1": {"score": 10, "status": "green", "reasons": []}
        },
        "rover": RoverState(status="done", current_zone="classroom_1").to_dict(),
        "layout_mode": "standard",
        "alert_active": False
    }

    hazards = service.hazard_engine.analyze_snapshot(recall_snapshot)
    explanations = service.decision_engine.evaluate_actions(recall_snapshot, hazards)
    actions = [de.action_name for de in explanations]
    assert "recall_rover" in actions
    service.stop()

def test_ai_service_chat_queries():
    """Verify generate_chat_response uses Gemini key or defaults correctly to fallback templates."""
    service = AiService()
    
    # 1. Verify local fallback matches query patterns
    # Query about specific room (e.g. classroom)
    resp_room = service.generate_chat_response("What is the status of Classroom 1?")
    assert "Classroom 1" in resp_room
    assert "temp" in resp_room
    
    # Query about rover
    resp_rover = service.generate_chat_response("Where is the rover right now?")
    assert "Rover status" in resp_rover
    
    # Query about general exit routes
    resp_exit = service.generate_chat_response("Show exit paths")
    assert "Egress routing" in resp_exit

def test_ai_api_endpoints():
    """Verify chat queries route successfully to ApiService and returns JSON response."""
    from server.services.api_service.service import ApiService
    from fastapi.testclient import TestClient
    from server.services import registry
    
    mock_ai = AiService()
    mock_ai.set_gemini_key("")
    mock_ai.start()
    
    with patch.object(registry, 'get', side_effect=lambda name: mock_ai if name == "AiService" else None):
        api = ApiService()
        client = TestClient(api.app)
        
        response = client.post("/api/ai/query", json={"query": "Is Classroom 1 safe?"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Classroom 1" in data["response"]
        
        # Test bad query payload
        bad_response = client.post("/api/ai/query", json={})
        assert bad_response.status_code == 400
        
    mock_ai.stop()

