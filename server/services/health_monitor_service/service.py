import threading
import time
import logging
from typing import List, Dict

import psutil

from server.services.base_service import BaseService

class HealthMonitorService(BaseService):
    """Collects system health metrics (CPU, memory, disk, battery) in the background.
    Stores the latest reading and a short history. In production this will publish
    to MQTT and sync with Convex.
    """
    def __init__(self, config: dict = None):
        super().__init__("HealthMonitorService", config)
        self._interval = self.config.get("interval_seconds", 10)
        self._history: List[Dict] = []
        self._latest: Dict = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.logger = logging.getLogger(self.name)

    def _collect_metrics(self) -> Dict:
        import os
        try:
            disk_percent = psutil.disk_usage(os.path.abspath(os.sep)).percent
        except Exception:
            try:
                disk_percent = psutil.disk_usage('.').percent
            except Exception:
                disk_percent = 0.0

        metrics = {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": disk_percent,
        }
        if hasattr(psutil, "sensors_battery"):
            batt = psutil.sensors_battery()
            if batt:
                metrics.update({
                    "battery_percent": batt.percent,
                    "battery_plugged": batt.power_plugged,
                })
        return metrics

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            metric = self._collect_metrics()
            with self._lock:
                self._latest = metric
                self._history.append(metric)
                if len(self._history) > 100:
                    self._history.pop(0)
            time.sleep(self._interval)

    def _on_start(self) -> bool:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("Health monitor started (interval=%s sec)", self._interval)
        return True

    def _on_stop(self) -> bool:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("Health monitor stopped")
        return True

    def get_status(self) -> Dict:
        with self._lock:
            return self._latest.copy()

    def get_history(self, limit: int = 20) -> List[Dict]:
        with self._lock:
            return self._history[-limit:].copy()
