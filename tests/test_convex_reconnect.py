import pytest
import time
from unittest.mock import patch, MagicMock
import requests
from server.services.convex_service.service import ConvexService

@patch("server.services.convex_service.service.requests.post")
def test_convex_sync_reconnect_retry(mock_post):
    """Verify that ConvexService caches sync items and retries on failure, resetting on success."""
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    
    # Track request results sequentially (throw RequestException first, then return 200 OK)
    mock_post.side_effect = [requests.RequestException("Offline"), mock_ok]

    with patch.dict("os.environ", {"CONVEX_URL": "https://mock-convex-cloud.convex.cloud"}):
        service = ConvexService()
        assert service.start() is True
        
        # Enqueue item
        service.sync_battery_history(3.8, 75.0)
        
        # Allow worker thread to attempt first post (should fail, enters backoff retry loop)
        time.sleep(0.3)
        assert service.is_connected() is False
        
        # Allow worker thread to run retry post (wait 1.5s since backoff is 1.0s)
        time.sleep(1.5)
        assert service.is_connected() is True
        
        assert service.stop() is True
        assert mock_post.call_count == 2
