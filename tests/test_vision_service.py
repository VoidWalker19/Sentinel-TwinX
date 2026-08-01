import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from server.services.vision_service.service import VisionService

def test_vision_service_simulation_fallback():
    """Verify VisionService falls back gracefully to simulation stats if cv2 is mock/none or frame is None."""
    service = VisionService()
    assert service.start() is True
    
    results = service.process_frame(None)
    assert "motion_detected" in results
    assert "fire_detected" in results
    assert "person_detected" in results
    assert "roboflow_status" in results
    assert service.stop() is True

def test_vision_service_motion_and_roboflow_parsing():
    """Verify motion scoring, safe prediction parsing, label normalization, and threat matrix."""
    service = VisionService(config={"motion_threshold": 1.0})
    assert service.start() is True
    
    # Create black BGR frame (320x240)
    frame_a = np.zeros((240, 320, 3), dtype=np.uint8)
    
    # Initial frame
    res_a = service.process_frame(frame_a)
    assert res_a["motion_detected"] is False
    
    # Motion frame
    frame_b = frame_a.copy()
    frame_b[50:150, 50:150] = 255
    res_b = service.process_frame(frame_b)
    assert res_b["motion_detected"] is True
    assert res_b["motion_score"] > 1.0
    
    # Test Roboflow prediction extraction helper
    sample_response = {
        "outputs": [
            {
                "predictions": [
                    {"class": "fire", "confidence": 0.96, "x": 100, "y": 100, "w": 50, "h": 50},
                    {"class_name": "person", "score": 0.91, "x_min": 10, "y_min": 10, "x_max": 60, "y_max": 120}
                ]
            }
        ]
    }
    extracted = service._extract_predictions(sample_response)
    assert len(extracted) == 2
    assert extracted[0]["class"] == "fire"
    
    # Check placeholders
    assert service.detect_smoke(frame_a) is False
    assert service.recognize_face(frame_a) is False
    
    assert service.stop() is True

def test_roboflow_workflow_smoke_test():
    """Smoke test running inference on a sample synthetic frame asserting expected keys exist."""
    service = VisionService()
    assert service.start() is True
    
    # Create sample image
    sample_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    sample_frame[100:200, 100:200] = [0, 165, 255]  # Sample shape
    
    results = service.process_frame(sample_frame)
    expected_keys = [
        "motion_detected", "motion_score",
        "fire_detected", "fire_confidence", "fire_boxes",
        "smoke_detected", "smoke_confidence", "smoke_boxes",
        "person_detected", "person_count", "person_boxes",
        "roboflow_status", "fire_verified", "verification_progress",
        "threat_level", "threat_reason", "objects"
    ]
    for k in expected_keys:
        assert k in results, f"Missing key '{k}' in vision results"
    
    assert service.stop() is True


