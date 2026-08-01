from server.services.base_service import BaseService
from typing import List, Dict, Any

class HistoryService(BaseService):
    """
    History Service responsible for retrieving aggregated historical logs,
    sensor averages, battery decay trends, and alert summaries from the SQLite database.
    """
    def __init__(self, config: dict = None):
        super().__init__("HistoryService", config)

    def _on_start(self) -> bool:
        self.logger.info("HistoryService started successfully.")
        return True

    def get_sensor_statistics(self) -> List[Dict[str, Any]]:
        from server.services import registry
        db = registry.get("DatabaseService")
        if not db:
            return []
        query = """
            SELECT zone_id, 
                   ROUND(AVG(temp), 1) as avg_temp, 
                   MAX(temp) as max_temp, 
                   ROUND(AVG(humidity), 1) as avg_humidity,
                   ROUND(AVG(smoke), 1) as avg_smoke
            FROM sensorReadings
            GROUP BY zone_id
        """
        return db.execute_query(query)

    def get_alert_statistics(self) -> Dict[str, Any]:
        from server.services import registry
        db = registry.get("DatabaseService")
        if not db:
            return {"total": 0, "breakdown": {}}
        total = db.execute_query("SELECT COUNT(*) as cnt FROM alerts")
        breakdown = db.execute_query("SELECT status, COUNT(*) as cnt FROM alerts GROUP BY status")
        return {
            "total": total[0]["cnt"] if total else 0,
            "breakdown": {row["status"]: row["cnt"] for row in breakdown}
        }

    def get_battery_decay(self) -> List[Dict[str, Any]]:
        from server.services import registry
        db = registry.get("DatabaseService")
        if not db:
            return []
        query = "SELECT timestamp, percentage FROM batteryHistory ORDER BY id DESC LIMIT 50"
        return db.execute_query(query)
