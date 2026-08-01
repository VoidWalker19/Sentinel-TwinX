import os
import time
import zipfile
import glob
from typing import Optional
from server.services.base_service import BaseService

class BackupService(BaseService):
    """
    Backup Service responsible for creating compressed SQLite database snapshots
    and enforcing rotation policies to keep only the 5 most recent backup files.
    """
    def __init__(self, config: dict = None):
        super().__init__("BackupService", config)
        self.backup_dir = self.config.get("backup_dir", "data/backups")
        self.max_backups = self.config.get("max_backups", 5)

    def _on_start(self) -> bool:
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        self.logger.info(f"BackupService started. Directory: {self.backup_dir}")
        return True

    def create_backup(self) -> Optional[str]:
        from server.services import registry
        db = registry.get("DatabaseService")
        if not db or not db.db_path:
            self.logger.warning("DatabaseService not available; skipping backup.")
            return None
        
        db_file = db.db_path
        if not os.path.exists(db_file):
            self.logger.warning(f"Database file not found at {db_file}")
            return None

        # Build backup zip path
        timestr = time.strftime("%Y%m%d_%H%M%S")
        backup_zip = os.path.join(self.backup_dir, f"sentinel_backup_{timestr}.zip")
        
        try:
            with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(db_file, os.path.basename(db_file))
            self.logger.info(f"Database backup created successfully: {backup_zip}")
            
            # Enforce local backup rotation policy
            self._rotate_backups()
            return backup_zip
        except Exception as e:
            self.logger.error(f"Failed to create database backup: {e}")
            return None

    def _rotate_backups(self):
        """Removes older backups to keep count under max_backups."""
        pattern = os.path.join(self.backup_dir, "sentinel_backup_*.zip")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime)
        
        if len(backups) > self.max_backups:
            to_remove = backups[:-self.max_backups]
            for file in to_remove:
                try:
                    os.remove(file)
                    self.logger.info(f"Pruned old backup file: {file}")
                except Exception as e:
                    self.logger.error(f"Failed to remove backup {file}: {e}")
