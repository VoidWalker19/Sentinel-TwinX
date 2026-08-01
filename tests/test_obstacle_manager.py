import pytest
from server.services.obstacle_manager.service import ObstacleManagerService

def test_obstacle_manager_thresholds():
    """Verify ObstacleManagerService correctly maps echo measurements to blocked flags."""
    manager = ObstacleManagerService()
    manager.obstacle_threshold_cm = 30.0
    
    # 1. Nominal distance: no obstacle
    manager.process_ultrasonic_reading("classroom_a", 150.0)
    assert manager.is_blocked("classroom_a") is False
    
    # 2. Distance less than threshold: obstacle detected
    manager.process_ultrasonic_reading("classroom_a", 15.0)
    assert manager.is_blocked("classroom_a") is True
    
    # 3. Clearing obstacle
    manager.process_ultrasonic_reading("classroom_a", 45.0)
    assert manager.is_blocked("classroom_a") is False
