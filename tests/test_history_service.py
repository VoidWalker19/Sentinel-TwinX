import pytest
import os
import time
from server.services.database_service.service import DatabaseService
from server.services.history_service.service import HistoryService
from server.services import registry

def test_history_service_aggregations():
    """Verify aggregated metrics fetched by HistoryService match SQLite inserts."""
    test_db = "data/test_history.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    db = DatabaseService({"db_path": test_db})
    assert db.start() is True
    registry.register(db)
    
    # Insert test sensor readings
    db.execute_write(
        "INSERT INTO sensorReadings (timestamp, zone_id, temp, smoke, humidity, blocked) VALUES (?, ?, ?, ?, ?, ?)",
        (time.time(), "classroom_a", 20.0, 50, 40.0, 0)
    )
    db.execute_write(
        "INSERT INTO sensorReadings (timestamp, zone_id, temp, smoke, humidity, blocked) VALUES (?, ?, ?, ?, ?, ?)",
        (time.time(), "classroom_a", 30.0, 60, 60.0, 0)
    )
    
    # Insert alerts
    db.log_alert("classroom_a", 85, "red", "Fire threat")
    db.log_alert("classroom_a", 40, "yellow", "Elevated heat")
    
    # Insert battery history
    db.log_battery(3.9, 78)
    db.log_battery(3.8, 72)
    
    # Start HistoryService
    hist = HistoryService()
    assert hist.start() is True
    
    # 1. Test sensor stats averages (average of 20 and 30 is 25.0)
    stats = hist.get_sensor_statistics()
    assert len(stats) == 1
    assert stats[0]["zone_id"] == "classroom_a"
    assert stats[0]["avg_temp"] == 25.0
    assert stats[0]["max_temp"] == 30.0
    assert stats[0]["avg_humidity"] == 50.0
    
    # 2. Test alert stats count
    alert_stats = hist.get_alert_statistics()
    assert alert_stats["total"] == 2
    assert alert_stats["breakdown"]["red"] == 1
    assert alert_stats["breakdown"]["yellow"] == 1
    
    # 3. Test battery decay list
    decay = hist.get_battery_decay()
    assert len(decay) == 2
    assert decay[0]["percentage"] == 72
    
    assert hist.stop() is True
    assert db.stop() is True
    if os.path.exists(test_db):
        os.remove(test_db)
