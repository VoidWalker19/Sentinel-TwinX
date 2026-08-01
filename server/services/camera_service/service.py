import time
import threading
import logging
import sys
from typing import Optional, Tuple
from server.services.base_service import BaseService

try:
    import cv2
except ImportError:
    cv2 = None

class CameraService(BaseService):
    """
    Service responsible for reading video frames from USB Webcams.
    Runs a background frame acquisition thread to prevent blocking.
    """
    def __init__(self, config: dict = None):
        super().__init__("CameraService", config)
        self.camera_index = self.config.get("camera_index", 0)
        self.frame_rate = self.config.get("frame_rate", 25.0) # FPS (Real-time live rate)
        self.width = self.config.get("width", 640)
        self.height = self.config.get("height", 480)
        self.is_simulated = "--sim" in sys.argv or self.config.get("simulated", False)

        self._cap = None
        self._latest_frame = None
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.is_live_capture = False
        self._fallback_frame_count = 0
        self._last_frame_grab_time = 0.0
        self._consecutive_failures = 0


    def _on_start(self) -> bool:
        import os
        camera_source = os.getenv("ESP32_CAM_URL", "").strip()

        if not camera_source:
            import socket
            from urllib.parse import urlparse
            for test_url in ["http://sentinelpi.local:5000/video_feed", "http://127.0.0.1:5000/video_feed"]:
                try:
                    parsed = urlparse(test_url)
                    with socket.create_connection((parsed.hostname, 5000), timeout=0.8):
                        camera_source = test_url
                        self.logger.info(f"Auto-detected Pi camera stream server on Port 5000 ({test_url})")
                        break
                except Exception:
                    pass

        if self.is_simulated or cv2 is None:
            self.logger.info("CameraService running in simulated mode (--sim active or OpenCV missing).")
            self._start_simulated_feed()
            return True

        if camera_source:
            import socket
            from urllib.parse import urlparse
            self.logger.info(f"Attempting to open ESP32-CAM stream at {camera_source}...")
            
            try:
                parsed = urlparse(camera_source)
                host = parsed.hostname
                port = parsed.port or (80 if parsed.scheme == 'http' else 443)
                if host:
                    self.logger.info(f"Pre-checking TCP connection to camera host {host}:{port}...")
                    with socket.create_connection((host, port), timeout=2.0):
                        self.logger.info("Camera host is reachable. Opening stream...")
                    
                    self._cap = cv2.VideoCapture(camera_source)
                    if self._cap.isOpened():
                        self.is_live_capture = True
                        self.logger.info(f"Connected to ESP32-CAM stream successfully.")
                    else:
                        self.logger.warning(f"Failed to connect to ESP32-CAM stream. Falling back to simulated feed.")
                        self._cap = None
                else:
                    self._cap = None
            except Exception as e:
                self.logger.warning(f"Camera host is unreachable or connection check failed ({e}). Falling back to simulated feed.")
                self._cap = None
        else:
            self.logger.info(f"Attempting to open USB Webcam (index {self.camera_index})...")
            try:
                self._cap = cv2.VideoCapture(self.camera_index)
                if self._cap and self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.is_live_capture = True
                    self.logger.info(f"Connected to local USB Webcam (index {self.camera_index}) at {self.width}x{self.height}.")
                else:
                    self.logger.warning(f"USB Webcam at index {self.camera_index} is unavailable.")
                    self._cap = None
            except Exception as e:
                self.logger.warning(f"USB Webcam initialization error: {e}")
                self._cap = None

        if not self.is_live_capture:
            self.logger.info("No live webcam or network stream available. Falling back to simulated feed.")
            self._start_simulated_feed()
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def _on_stop(self) -> bool:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()
            self._cap = None
        self.logger.info("Camera service stopped.")
        return True

    def _capture_loop(self):
        import os
        camera_source = os.getenv("ESP32_CAM_URL", "").strip()
        while not self._stop_event.is_set():
            cap = self._cap
            if cap:
                try:
                    ret, frame = cap.read()
                except Exception:
                    ret, frame = False, None
                if ret and frame is not None:
                    with self._lock:
                        self._latest_frame = frame
                        self._last_frame_grab_time = time.time()
                        self._consecutive_failures = 0
                    time.sleep(1.0 / self.frame_rate)
                else:
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= 3:
                        with self._lock:
                            self._latest_frame = None
                        self.logger.warning("Live camera stream stalled (>3 failed reads). Re-opening video capture...")
                        if self._cap:
                            self._cap.release()
                        time.sleep(0.5)
                        target = camera_source if camera_source else self.camera_index
                        self._cap = cv2.VideoCapture(target)
                    else:
                        time.sleep(0.05)
            else:
                time.sleep(0.05)

    def _start_simulated_feed(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._simulated_capture_loop, daemon=True)
        self._thread.start()

    def _simulated_capture_loop(self):
        # Generates a premium night-vision BGR camera feed with grid overlays and rover state telemetry
        import numpy as np
        from server.state import app_state
        interval = 1.0 / self.frame_rate
        frame_count = 0
        
        while not self._stop_event.is_set():
            start_time = time.time()
            frame_count += 1
            
            # Base dark green night-vision matrix
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            frame[:, :] = (12, 28, 12)  # Very dark green
            
            cv2_temp = cv2 if cv2 else None
            
            if cv2_temp:
                # 1. Draw grid overlay
                grid_spacing = 60
                for x in range(0, self.width, grid_spacing):
                    cv2_temp.line(frame, (x, 0), (x, self.height), (20, 60, 20), 1)
                for y in range(0, self.height, grid_spacing):
                    cv2_temp.line(frame, (0, y), (self.width, y), (20, 60, 20), 1)
                
                # 2. Add rolling scan line
                scan_y = int((frame_count * 8) % self.height)
                cv2_temp.line(frame, (0, scan_y), (self.width, scan_y), (40, 140, 40), 2)
                
                # 3. Add random camera noise/static (subtle)
                noise = np.random.normal(0, 4, (self.height, self.width, 3)).astype(np.int16)
                frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                # 4. Draw HUD reticles/corners
                pad = 40
                length = 20
                color_hud = (0, 230, 190)  # Neon Teal/Green
                # Top Left
                cv2_temp.line(frame, (pad, pad), (pad + length, pad), color_hud, 1)
                cv2_temp.line(frame, (pad, pad), (pad, pad + length), color_hud, 1)
                # Top Right
                cv2_temp.line(frame, (self.width - pad, pad), (self.width - pad - length, pad), color_hud, 1)
                cv2_temp.line(frame, (self.width - pad, pad), (self.width - pad, pad + length), color_hud, 1)
                # Bottom Left
                cv2_temp.line(frame, (pad, self.height - pad), (pad + length, self.height - pad), color_hud, 1)
                cv2_temp.line(frame, (pad, self.height - pad), (pad, self.height - pad - length), color_hud, 1)
                # Bottom Right
                cv2_temp.line(frame, (self.width - pad, self.height - pad), (self.width - pad - length, self.height - pad), color_hud, 1)
                cv2_temp.line(frame, (self.width - pad, self.height - pad), (self.width - pad, self.height - pad - length), color_hud, 1)
                
                # Center crosshair
                cx, cy = self.width // 2, self.height // 2
                cv2_temp.drawMarker(frame, (cx, cy), color_hud, cv2_temp.MARKER_CROSS, 20, 1)
                cv2_temp.circle(frame, (cx, cy), 8, color_hud, 1)
                
                # 5. Fetch and Overlay Rover Telemetry dynamically
                rover_state = getattr(app_state, 'rover', None)
                r_status = "STANDBY"
                r_zone = "BASE"
                r_batt = 100.0
                
                if rover_state:
                    r_status = (getattr(rover_state, 'status', 'standby') or 'standby').upper()
                    r_zone = (getattr(rover_state, 'current_zone', 'base') or 'base').upper()
                    r_batt = float(getattr(rover_state, 'battery_pct', 100.0) or 100.0)
                
                # Font configurations
                font = cv2_temp.FONT_HERSHEY_SIMPLEX
                scale_title = 0.5
                scale_data = 0.4
                thickness = 1
                
                # Top Left HUD Text
                cv2_temp.putText(frame, "◆ SENTINEL COMMAND LAYER V2", (pad + 10, pad + 25), font, scale_title, color_hud, thickness)
                cv2_temp.putText(frame, "POV FEED: ROVER_CAM_01", (pad + 10, pad + 45), font, scale_data, (139, 92, 246), thickness)
                
                # Top Right HUD Text
                ts = time.strftime("%Y-%m-%d %H:%M:%S UTC")
                cv2_temp.putText(frame, f"TIME: {ts}", (self.width - pad - 240, pad + 25), font, scale_data, color_hud, thickness)
                cv2_temp.putText(frame, f"FPS: {self.frame_rate:.1f} (LIVE SIM)", (self.width - pad - 240, pad + 45), font, scale_data, color_hud, thickness)
                
                # Bottom Left HUD Text (Status / Location)
                cv2_temp.putText(frame, f"SYS STATUS: {r_status}", (pad + 10, self.height - pad - 35), font, scale_data, color_hud, thickness)
                cv2_temp.putText(frame, f"CURR ZONE: {r_zone}", (pad + 10, self.height - pad - 15), font, scale_data, color_hud, thickness)
                
                # Bottom Right HUD Text (Battery / Signal)
                batt_color = (0, 230, 190) if r_batt > 30 else (50, 150, 255) if r_batt > 15 else (60, 60, 240)
                cv2_temp.putText(frame, f"BATTERY  : {r_batt:.1f}%", (self.width - pad - 180, self.height - pad - 35), font, scale_data, batt_color, thickness)
                cv2_temp.putText(frame, "LINK QUAL: 98% (UART)", (self.width - pad - 180, self.height - pad - 15), font, scale_data, color_hud, thickness)
                
                # 6. Thermal Signature Alert Indicator
                risk_scores = getattr(app_state, 'risk_scores', {})
                risk_obj = risk_scores.get(rover_state.current_zone) if (rover_state and hasattr(rover_state, 'current_zone') and isinstance(risk_scores, dict)) else None
                risk_score = risk_obj.score if (risk_obj and hasattr(risk_obj, 'score')) else 0
                if risk_score >= 70 and (frame_count // 5) % 2 == 0:
                    cv2_temp.rectangle(frame, (pad - 10, pad - 10), (self.width - pad + 10, self.height - pad + 10), (60, 60, 240), 2)
                    cv2_temp.putText(frame, "🚨 WARNING: HIGH THERMAL INTRUSION DETECTED", (cx - 190, cy - 50), font, 0.5, (60, 60, 240), 2)

            with self._lock:
                self._latest_frame = frame
                self._last_frame_grab_time = time.time()
            
            elapsed = time.time() - start_time
            sleep_time = max(0.0, interval - elapsed)
            time.sleep(sleep_time)

    def _generate_fallback_frame(self):
        """Generate a dynamic 30 FPS BGR frame with animated HUD overlay when live stream stalls."""
        if cv2 is not None:
            import numpy as np
            self._fallback_frame_count += 1
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            frame[:, :] = (15, 25, 15)
            
            # Grid overlay
            for x in range(0, self.width, 60):
                cv2.line(frame, (x, 0), (x, self.height), (20, 50, 20), 1)
            for y in range(0, self.height, 60):
                cv2.line(frame, (0, y), (self.width, y), (20, 50, 20), 1)

            # Animated rolling scanline
            scan_y = int((self._fallback_frame_count * 6) % self.height)
            cv2.line(frame, (0, scan_y), (self.width, scan_y), (0, 200, 150), 2)

            font = cv2.FONT_HERSHEY_SIMPLEX
            ts = time.strftime("%Y-%m-%d %H:%M:%S UTC")
            color_hud = (0, 230, 190)
            
            cv2.putText(frame, "◆ SENTINEL CAMERA FEED · STANDBY HUD", (30, 40), font, 0.5, color_hud, 1)
            cv2.putText(frame, f"TIME: {ts}", (30, 70), font, 0.4, (200, 200, 200), 1)
            cv2.putText(frame, "STATUS: SEARCHING / STANDBY FEED (LIVE)", (30, 120), font, 0.4, (0, 200, 255), 1)
            
            # Animated pulsing crosshair
            cx, cy = self.width // 2, self.height // 2
            cv2.circle(frame, (cx, cy), 15 + (self._fallback_frame_count % 10), color_hud, 1)
            cv2.drawMarker(frame, (cx, cy), color_hud, cv2.MARKER_CROSS, 30, 1)
            return frame
        return None

    def get_latest_frame(self):
        from server.services import registry
        diag = registry.get("DiagnosticsService")
        if diag and diag.get_simulation("camera_failure"):
            return None

        
        now = time.time()
        with self._lock:
            # If live frame exists and is less than 1 second old, return live frame
            if self._latest_frame is not None and (now - self._last_frame_grab_time < 1.0):
                return self._latest_frame
        
        # Stream stalled or camera offline: return dynamic animated standby HUD frame
        return self._generate_fallback_frame()

    def get_latest_frame_jpeg(self) -> Optional[bytes]:
        """Encodes frame to JPEG for streaming endpoints."""
        frame = self.get_latest_frame()
        if frame is None or cv2 is None:
            return None
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes() if ret else None
