import pytest
import sqlite3
import time
import os
from server.services.database_service.service import DatabaseService

def test_database_retention_pruning():
    """Verify that records older than max_age_days are successfully deleted from SQLite."""
    # Initialize DatabaseService with a temporary test DB
    test_db = "data/test_pruning.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    db = DatabaseService({"db_path": test_db})
    assert db.start() is True
    
    # Insert a mix of old and new data into sensorReadings
    now = time.time()
    old_timestamp = now - (10 * 24 * 3600) # 10 days ago
    new_timestamp = now - (2 * 24 * 3600)  # 2 days ago
    
    db.execute_write(
        "INSERT INTO sensorReadings (timestamp, zone_id, temp, smoke, humidity, blocked) VALUES (?, ?, ?, ?, ?, ?)",
        (old_timestamp, "classroom_a", 22.0, 50, 50.0, 0)
    )
    db.execute_write(
        "INSERT INTO sensorReadings (timestamp, zone_id, temp, smoke, humidity, blocked) VALUES (?, ?, ?, ?, ?, ?)",
        (new_timestamp, "classroom_a", 24.0, 45, 52.0, 0)
    )
    
    # 1. Prune with 5-day policy (should delete the 10-day old row, keep the 2-day old one)
    deleted = db.prune_old_data(max_age_days=5)
    assert deleted == 1
    
    # Verify rows remaining
    rows = db.execute_query("SELECT * FROM sensorReadings")
    assert len(rows) == 1
    assert rows[0]["temp"] == 24.0
    
    assert db.stop() is True
    if os.path.exists(test_db):
        os.remove(test_db)
