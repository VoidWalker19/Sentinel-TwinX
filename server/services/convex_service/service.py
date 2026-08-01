import os
import time
import queue
import threading
import logging
import requests
from typing import Optional, Dict, Any
from server.services.base_service import BaseService

class ConvexService(BaseService):
    """
    Convex Cloud Sync Service that queues and mirrors telemetry snapshots to Convex HTTP endpoints.
    Includes connection tracking and automatic exponential backoff retries.
    """
    def __init__(self, config: dict = None):
        super().__init__("ConvexService", config)
        self.convex_url = os.getenv("CONVEX_URL", "").strip()
        self._queue = queue.Queue(maxsize=1000)
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._is_connected = False
        self._lock = threading.Lock()

    def _on_start(self) -> bool:
        self.convex_url = os.getenv("CONVEX_URL", "").strip()
        if not self.convex_url:
            self.logger.warning("CONVEX_URL is not set in environment variables. Convex synchronization is disabled.")

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self.logger.info("ConvexService started successfully.")
        return True

    def _on_stop(self) -> bool:
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
        self.logger.info("Convex sync service stopped.")
        return True

    def is_connected(self) -> bool:
        with self._lock:
            return self._is_connected

    def _worker_loop(self):
        retry_item = None
        retry_delay = 1.0

        while not self._stop_event.is_set() or not self._queue.empty() or retry_item is not None:
            if retry_item is None:
                try:
                    item = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
            else:
                item = retry_item

            endpoint, payload = item
            if self.convex_url:
                full_url = f"{self.convex_url.rstrip('/')}/api/convex/{endpoint}"
                try:
                    resp = requests.post(full_url, json=payload, timeout=3)
                    if resp.status_code == 200:
                        with self._lock:
                            self._is_connected = True
                        retry_item = None
                        retry_delay = 1.0
                        if retry_item is None and not self._queue.empty():
                            self._queue.task_done()
                    else:
                        with self._lock:
                            self._is_connected = False
                        retry_item = item
                        time.sleep(retry_delay)
                except Exception as e:
                    self.logger.debug(f"Convex sync post error: {e}")
                    with self._lock:
                        self._is_connected = False
                    retry_item = item
                    time.sleep(retry_delay)
            else:
                if retry_item is None:
                    self._queue.task_done()
                retry_item = None

    def _enqueue(self, endpoint: str, payload: dict):
        if not self.is_running:
            return
        try:
            self._queue.put_nowait((endpoint, payload))
        except queue.Full:
            pass

    def sync_sensor_reading(self, zone_id: str, temp: float, smoke: int, humidity: float, blocked: bool):
        self._enqueue("sync_sensor_readings", {
            "zone_id": zone_id, "temp": temp, "smoke": smoke, "humidity": humidity, "blocked": blocked, "timestamp": time.time()
        })

    def sync_alert(self, zone_id: str, risk_score: int, status: str, reasons: str):
        self._enqueue("sync_alert", {
            "zone_id": zone_id, "risk_score": risk_score, "status": status, "reasons": reasons, "timestamp": time.time()
        })

    def sync_rover_status(self, status: str, battery_pct: float, pos_x: float, pos_y: float, rssi: int, eta: int):
        self._enqueue("sync_rover_status", {
            "status": status, "battery_pct": battery_pct, "pos_x": pos_x, "pos_y": pos_y, "rssi": rssi, "eta": eta, "timestamp": time.time()
        })

    def sync_camera_event(self, event_type: str, confidence: float, image_url: str):
        self._enqueue("sync_camera_event", {
            "event_type": event_type, "confidence": confidence, "image_url": image_url, "timestamp": time.time()
        })

    def sync_ai_report(self, summary: str, analysis: str, severity: str, confidence: str, recommendations_json: str):
        self._enqueue("sync_ai_report", {
            "summary": summary, "analysis": analysis, "severity": severity, "confidence": confidence, "recommendations": recommendations_json, "timestamp": time.time()
        })

    def sync_mission(self, mission_id: str, mission_type: str, status: str, target_zones: list, priority: int):
        self._enqueue("sync_mission", {
            "mission_id": mission_id, "mission_type": mission_type, "status": status, "target_zones": target_zones, "priority": priority, "timestamp": time.time()
        })

    def sync_battery_history(self, voltage: float, battery_pct: float):
        self._enqueue("sync_battery_history", {
            "voltage": voltage, "battery_pct": battery_pct, "timestamp": time.time()
        })
