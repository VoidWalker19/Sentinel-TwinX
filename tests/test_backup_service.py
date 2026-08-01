import pytest
import os
import glob
import time
import zipfile
from server.services.database_service.service import DatabaseService
from server.services.backup_service.service import BackupService
from server.services import registry

def test_backup_service_creation_and_rotation():
    """Verify BackupService creates ZIP archive and limits the total backup count to 5."""
    test_db = "data/test_backup_src.db"
    backup_dir = "data/test_backups_dest"
    
    # Cleanup pre-existing files
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
        if os.path.exists(backup_dir):
            import shutil
            shutil.rmtree(backup_dir)
    except Exception:
        pass
        
    db = DatabaseService({"db_path": test_db})
    assert db.start() is True
    registry.register(db)
    
    # Write some data
    db.log_alert("classroom_a", 90, "red", "Heat spike")
    
    backup = BackupService({"backup_dir": backup_dir, "max_backups": 5})
    assert backup.start() is True
    registry.register(backup)
    
    # 1. Test backup creation
    zip_path = backup.create_backup()
    assert zip_path is not None
    assert os.path.exists(zip_path)
    assert zipfile.is_zipfile(zip_path)
    
    # Verify contents of zip contains the database
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        namelist = zipf.namelist()
        assert os.path.basename(test_db) in namelist
        
    # 2. Test rotation limit policy by triggering 6 backups
    for _ in range(6):
        backup.create_backup()
        time.sleep(1.0) # separate file timestamps
        
    # Assert total files count matches max_backups limit (5)
    files = glob.glob(os.path.join(backup_dir, "sentinel_backup_*.zip"))
    assert len(files) == 5
    
    assert backup.stop() is True
    assert db.stop() is True
    
    # Clean up test directories
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
        if os.path.exists(backup_dir):
            import shutil
            shutil.rmtree(backup_dir)
    except Exception:
        pass
