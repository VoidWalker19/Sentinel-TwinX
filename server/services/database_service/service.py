import os
import sqlite3
import json
import time
from typing import List, Dict, Any, Optional
from server.services.base_service import BaseService

class DatabaseService(BaseService):
    """
    Service responsible for local SQLite storage and queries.
    Configures SQLite in Write-Ahead Logging (WAL) mode for concurrency safety.
    """
    def __init__(self, config: dict = None):
        super().__init__("DatabaseService", config)
        self.db_path = self.config.get("db_path", "data/sentinel.db")
        self._conn = None

    def _on_start(self) -> bool:
        try:
            # Ensure data directory exists
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            self.logger.info(f"Connecting to SQLite database at {self.db_path}...")
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            
            # Enable WAL mode and foreign keys
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            self.logger.info("SQLite journal mode set to WAL.")

            self._create_tables(cursor)
            self._conn.commit()
            
            # Run automatic data retention policy on startup (e.g. prune records older than 7 days)
            self.prune_old_data(7)
            
            return True
        except Exception as e:
            self.logger.exception(f"Failed to initialize SQLite database: {e}")
            return False

    def _on_stop(self) -> bool:
        if self._conn:
            self._conn.close()
            self.logger.info("SQLite connection closed.")
        return True

    def _create_tables(self, cursor: sqlite3.Cursor):
        # 1. sensorReadings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensorReadings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                zone_id TEXT NOT NULL,
                temp REAL,
                smoke INTEGER,
                humidity REAL,
                blocked INTEGER
            );
        """)

        # 2. alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                zone_id TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                description TEXT
            );
        """)

        # 3. missions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                mission_id TEXT NOT NULL,
                state TEXT NOT NULL,
                target_zone TEXT NOT NULL,
                priority INTEGER NOT NULL
            );
        """)

        # 4. roverStatus
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roverStatus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                status TEXT NOT NULL,
                battery INTEGER NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                wifi_rssi INTEGER NOT NULL,
                uptime INTEGER NOT NULL
            );
        """)

        # 5. batteryHistory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batteryHistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                voltage REAL NOT NULL,
                percentage INTEGER NOT NULL
            );
        """)

        # 6. cameraEvents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cameraEvents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_path TEXT
            );
        """)

        # 7. reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                summary TEXT NOT NULL,
                analysis TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence TEXT NOT NULL,
                recommendations_json TEXT NOT NULL
            );
        """)

        # 8. settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL
            );
        """)

        # 9. analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                meta_json TEXT
            );
        """)

    # --- Write Helpers ---
    def execute_write(self, query: str, params: tuple = ()) -> bool:
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            self._conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"SQL write error: {e} | Query: {query}")
            return False

    def log_sensor_reading(self, zone_id: str, temp: Optional[float], smoke: Optional[int], humidity: Optional[float], blocked: bool):
        self.execute_write(
            "INSERT INTO sensorReadings (timestamp, zone_id, temp, smoke, humidity, blocked) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), zone_id, temp, smoke, humidity, 1 if blocked else 0)
        )

    def log_alert(self, zone_id: str, risk_score: int, status: str, description: str):
        self.execute_write(
            "INSERT INTO alerts (timestamp, zone_id, risk_score, status, description) VALUES (?, ?, ?, ?, ?)",
            (time.time(), zone_id, risk_score, status, description)
        )

    def log_mission(self, mission_id: str, state: str, target_zone: str, priority: int):
        self.execute_write(
            "INSERT INTO missions (timestamp, mission_id, state, target_zone, priority) VALUES (?, ?, ?, ?, ?)",
            (time.time(), mission_id, state, target_zone, priority)
        )

    def log_rover_status(self, status: str, battery: int, x: float, y: float, wifi_rssi: int, uptime: int):
        self.execute_write(
            "INSERT INTO roverStatus (timestamp, status, battery, x, y, wifi_rssi, uptime) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), status, battery, x, y, wifi_rssi, uptime)
        )

    def log_battery(self, voltage: float, percentage: int):
        self.execute_write(
            "INSERT INTO batteryHistory (timestamp, voltage, percentage) VALUES (?, ?, ?)",
            (time.time(), voltage, percentage)
        )

    def log_camera_event(self, event_type: str, confidence: float, image_path: str):
        self.execute_write(
            "INSERT INTO cameraEvents (timestamp, event_type, confidence, image_path) VALUES (?, ?, ?, ?)",
            (time.time(), event_type, confidence, image_path)
        )

    def log_report(self, summary: str, analysis: str, severity: str, confidence: str, recommendations: list):
        self.execute_write(
            "INSERT INTO reports (timestamp, summary, analysis, severity, confidence, recommendations_json) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), summary, analysis, severity, confidence, json.dumps(recommendations))
        )

    def set_setting(self, key: str, value: Any):
        self.execute_write(
            "INSERT OR REPLACE INTO settings (timestamp, key, value) VALUES (?, ?, ?)",
            (time.time(), key, str(value))
        )

    def log_analytics_metric(self, event_type: str, metric_value: float, meta_json: str = None):
        self.execute_write(
            "INSERT INTO analytics (timestamp, event_type, metric_value, meta_json) VALUES (?, ?, ?, ?)",
            (time.time(), event_type, metric_value, meta_json)
        )

    def prune_old_data(self, max_age_days: int = 7) -> int:
        """Prunes telemetry records older than max_age_days to maintain database size. Returns count of deleted rows."""
        if not self._conn:
            return 0
        cutoff = time.time() - (max_age_days * 24 * 3600)
        total_deleted = 0
        try:
            cursor = self._conn.cursor()
            tables = ["sensorReadings", "alerts", "roverStatus", "batteryHistory", "cameraEvents", "analytics"]
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))
                total_deleted += cursor.rowcount
            self._conn.commit()
            self.logger.info(f"Database pruning completed. Removed {total_deleted} records older than {max_age_days} days.")
            return total_deleted
        except Exception as e:
            self.logger.error(f"Failed to prune old data: {e}")
            return 0

    # --- Read Helpers ---
    def execute_query(self, query: str, params: tuple = ()) -> List[dict]:
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"SQL query error: {e} | Query: {query}")
            return []

    def get_latest_sensor_readings(self, limit: int = 100) -> List[dict]:
        return self.execute_query("SELECT * FROM sensorReadings ORDER BY id DESC LIMIT ?", (limit,))

    def get_latest_alerts(self, limit: int = 20) -> List[dict]:
        return self.execute_query("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))

    def get_settings(self) -> Dict[str, str]:
        rows = self.execute_query("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}
