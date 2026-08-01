import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from server.services.camera_service.service import CameraService
from server.services.api_service.service import ApiService

@patch("server.services.camera_service.service.cv2")
def test_camera_service_simulated_feed(mock_cv2):
    """Verify CameraService generates valid mock frames in simulated fallback mode."""
    # Force VideoCapture to fail opening so it falls back to simulated feed
    mock_cv2.VideoCapture.return_value.isOpened.return_value = False
    mock_cv2.imencode.return_value = (True, MagicMock(tobytes=lambda: b'\xff\xd8mockjpeg'))
    
    service = CameraService(config={"frame_rate": 10.0, "width": 320, "height": 240})
    assert service.start() is True
    
    # Robustly wait for first frame (avoiding race conditions)
    frame = None
    for _ in range(30):
        frame = service.get_latest_frame()
        if frame is not None:
            break
        time.sleep(0.1)
    
    assert frame is not None
    assert frame.shape == (240, 320, 3)
    
    jpeg_bytes = service.get_latest_frame_jpeg()
    assert jpeg_bytes is not None
    assert jpeg_bytes.startswith(b'\xff\xd8')
    
    assert service.stop() is True

@patch("server.services.camera_service.service.cv2")
def test_camera_api_endpoints(mock_cv2):
    """Verify camera streaming and capture routes are exposed on ApiService."""
    mock_cv2.VideoCapture.return_value.isOpened.return_value = False
    mock_cv2.imencode.return_value = (True, MagicMock(tobytes=lambda: b'\xff\xd8mockjpeg'))
    
    mock_camera = CameraService(config={"width": 320, "height": 240})
    mock_camera.start()
    
    # Robustly wait for first frame
    for _ in range(30):
        if mock_camera.get_latest_frame() is not None:
            break
        time.sleep(0.1)
    
    from server.services import registry
    with patch.object(registry, 'get', side_effect=lambda name: mock_camera if name == "CameraService" else None):
        api = ApiService()
        client = TestClient(api.app)
        
        # 1. Capture endpoint
        response = client.get("/api/camera/capture")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert len(response.content) > 0
        
    mock_camera.stop()
