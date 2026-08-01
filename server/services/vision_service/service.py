import time
import logging
import json
import base64
import threading
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional, List
from server.services.base_service import BaseService

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

ROBOFLOW_WORKFLOW_URL = "https://serverless.roboflow.com/ankit-chaudhary/workflows/fire-smoke-and-human-detector-vfire-smoke-and-human-detector-pr48p-1-rfdetr-large-t1-logic"
ROBOFLOW_WORKFLOW_ALT_URL = "https://serverless.roboflow.com/infer/workflows/ankit-chaudhary/fire-smoke-and-human-detector-vfire-smoke-and-human-detector-pr48p-1-rfdetr-large-t1-logic"

class VisionService(BaseService):
    """
    Roboflow AI Vision Service for Sentinel Twin.
    Performs real-time object detection (Fire, Smoke, Human) via Roboflow Serverless Workflow proxy.
    Includes 2-second continuous fire verification, Human Awareness Threat Matrix,
    background 1-2 FPS rate-limiting, and MQTT state synchronization.
    """
    def __init__(self, config: dict = None):
        super().__init__("VisionService", config)
        self.motion_threshold = self.config.get("motion_threshold", 1.5)
        self.alert_hold_duration = self.config.get("alert_hold_duration", 4.0)

        # Roboflow settings & state
        self.roboflow_url = ROBOFLOW_WORKFLOW_URL
        self.roboflow_api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
        self.inference_interval = 0.5  # ~2 FPS max for Roboflow API calls to maintain stream smoothness
        
        self._prev_gray = None
        self._last_inference_time = 0.0
        self._inference_in_progress = False
        self._lock = threading.Lock()

        # Cached Roboflow inference output
        self._cached_results = {
            "fire_detected": False,
            "fire_confidence": 0.0,
            "fire_boxes": [],
            "smoke_detected": False,
            "smoke_confidence": 0.0,
            "smoke_boxes": [],
            "person_detected": False,
            "person_count": 0,
            "person_confidence": 0.0,
            "person_boxes": [],
            "roboflow_status": "online" if self.roboflow_api_key else "AI Offline",
            "threat_level": "NOMINAL",
            "threat_reason": "Monitoring parameters nominal.",
            "objects": []
        }

        # Verification state (2.0 seconds continuous Fire detection required)
        self._fire_start_time: Optional[float] = None
        self._fire_verified: bool = False
        self._last_fire_time: float = 0.0
        self._last_published_state: Dict[str, Any] = {}

    def _on_start(self) -> bool:
        self.roboflow_api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
        status_str = "Loaded API key" if self.roboflow_api_key else "No API key found (AI Offline)"
        self.logger.info(f"Roboflow AI Vision Service initialized with workflow: {self.roboflow_url}. {status_str}")
        return True

    def process_frame(self, frame) -> Dict[str, Any]:
        """Processes BGR video frame, computes fast motion score, and updates cached Roboflow AI detections."""
        results = {
            "motion_detected": False,
            "motion_score": 0.0,
            "fire_detected": False,
            "fire_ratio": 0.0,
            "fire_confidence": 0.0,
            "fire_boxes": [],
            "smoke_detected": False,
            "smoke_confidence": 0.0,
            "smoke_boxes": [],
            "person_detected": False,
            "person_count": 0,
            "person_boxes": [],
            "face_recognized": False,
            "roboflow_status": "AI Offline",
            "fire_verified": False,
            "verification_progress": 0.0,
            "threat_level": "NOMINAL",
            "threat_reason": "Monitoring parameters nominal.",
            "objects": []
        }

        if frame is None or cv2 is None or np is None:
            return self._simulate_vision()

        try:
            # 1. Fast Motion Analysis (< 1ms)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

            if self._prev_gray is not None:
                frame_diff = cv2.absdiff(self._prev_gray, gray_blurred)
                _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
                motion_pixels = cv2.countNonZero(thresh)
                total_pixels = thresh.size
                motion_ratio = (motion_pixels / total_pixels) * 100
                results["motion_score"] = round(motion_ratio, 2)
                results["motion_detected"] = motion_ratio >= self.motion_threshold

            self._prev_gray = gray_blurred

            # 2. Trigger Async Roboflow Inference if interval elapsed (1-2 FPS rate-limiting)
            now = time.time()
            if (now - self._last_inference_time >= self.inference_interval) and not self._inference_in_progress:
                self._last_inference_time = now
                frame_copy = frame.copy()
                thread = threading.Thread(target=self._run_roboflow_inference, args=(frame_copy,), daemon=True)
                thread.start()

            # 3. Read cached Roboflow results
            with self._lock:
                cached = dict(self._cached_results)

            # Update results with cached Roboflow output
            results.update({
                "fire_detected": cached.get("fire_detected", False),
                "fire_confidence": cached.get("fire_confidence", 0.0),
                "fire_boxes": cached.get("fire_boxes", []),
                "smoke_detected": cached.get("smoke_detected", False),
                "smoke_confidence": cached.get("smoke_confidence", 0.0),
                "smoke_boxes": cached.get("smoke_boxes", []),
                "person_detected": cached.get("person_detected", False),
                "person_count": cached.get("person_count", 0),
                "person_boxes": cached.get("person_boxes", []),
                "roboflow_status": cached.get("roboflow_status", "AI Offline"),
                "threat_level": cached.get("threat_level", "NOMINAL"),
                "threat_reason": cached.get("threat_reason", ""),
                "objects": cached.get("objects", [])
            })

            # 4. Continuous 2.0-Second Fire Verification Logic
            raw_fire = results["fire_detected"]
            if raw_fire:
                if self._fire_start_time is None:
                    self._fire_start_time = now
                elapsed = now - self._fire_start_time
                results["verification_progress"] = min(1.0, round(elapsed / 2.0, 2))
                
                if elapsed >= 2.0:
                    self._fire_verified = True
                    results["fire_verified"] = True
                    self._handle_verified_fire(results)
                else:
                    results["fire_verified"] = False
            else:
                self._fire_start_time = None
                self._fire_verified = False
                results["fire_verified"] = False
                results["verification_progress"] = 0.0

            # Sync MQTT state if changed
            self._sync_mqtt_state(results)

        except Exception as e:
            self.logger.error(f"Error in VisionService process_frame: {e}")

        return results

    def _run_roboflow_inference(self, frame_bgr):
        """Runs Roboflow Serverless Workflow inference via HTTP POST proxy with retries and backoff."""
        self._inference_in_progress = True
        try:
            api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
            if not api_key:
                with self._lock:
                    self._cached_results["roboflow_status"] = "AI Offline"
                return

            # Encode BGR frame to JPEG base64 string
            ret, buffer = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                return

            b64_image = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "api_key": api_key,
                "inputs": {
                    "image": {
                        "type": "base64",
                        "value": b64_image
                    }
                }
            }
            body_bytes = json.dumps(payload).encode('utf-8')

            # Attempt endpoint call with up to 2 retries
            urls_to_try = [self.roboflow_url, ROBOFLOW_WORKFLOW_ALT_URL]
            response_data = None
            latency = 0.0

            for target_url in urls_to_try:
                for attempt in range(2):
                    try:
                        req = urllib.request.Request(
                            target_url,
                            data=body_bytes,
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        start_t = time.time()
                        with urllib.request.urlopen(req, timeout=4.0) as resp:
                            resp_bytes = resp.read()
                            response_data = json.loads(resp_bytes.decode('utf-8'))
                            latency = round((time.time() - start_t) * 1000, 1)
                        if response_data:
                            break
                    except urllib.error.HTTPError as he:
                        if he.code == 404 and target_url == self.roboflow_url:
                            break  # Try alternative URL format
                        time.sleep(0.2 * (attempt + 1))
                    except Exception as ex:
                        time.sleep(0.2 * (attempt + 1))
                if response_data:
                    break

            if not response_data:
                with self._lock:
                    self._cached_results["roboflow_status"] = "AI Offline"
                return

            # Extract prediction array safely from nested Roboflow structures
            raw_predictions = self._extract_predictions(response_data)


            # Normalize predictions (Fire, Smoke, Human ONLY)
            fire_boxes = []
            fire_confs = []
            smoke_boxes = []
            smoke_confs = []
            person_boxes = []
            person_confs = []
            normalized_objects = []

            h_img, w_img = frame_bgr.shape[:2]

            for p in raw_predictions:
                if not isinstance(p, dict):
                    continue

                raw_class = str(p.get("class", p.get("class_name", p.get("label", "")))).lower().strip()
                conf = float(p.get("confidence", p.get("score", p.get("conf", 0.90))))

                # Calculate bounding box coordinates [x, y, w, h]
                x_center = p.get("x", p.get("x_center", 0))
                y_center = p.get("y", p.get("y_center", 0))
                bw = p.get("width", p.get("w", 0))
                bh = p.get("height", p.get("h", 0))

                if "x_min" in p and "y_min" in p:
                    bx = int(p["x_min"])
                    by = int(p["y_min"])
                    bw = int(p.get("x_max", bx + bw) - bx)
                    bh = int(p.get("y_max", by + bh) - by)
                else:
                    bx = int(max(0, x_center - (bw / 2.0)))
                    by = int(max(0, y_center - (bh / 2.0)))
                    bw = int(min(w_img - bx, bw))
                    bh = int(min(h_img - by, bh))

                box_tuple = (bx, by, bw, bh)

                if any(k in raw_class for k in ["fire", "flame", "blaze"]):
                    fire_boxes.append(box_tuple)
                    fire_confs.append(conf)
                    normalized_objects.append({"class": "Fire", "confidence": conf, "box": box_tuple})
                elif any(k in raw_class for k in ["smoke", "haze", "fume"]):
                    smoke_boxes.append(box_tuple)
                    smoke_confs.append(conf)
                    normalized_objects.append({"class": "Smoke", "confidence": conf, "box": box_tuple})
                elif any(k in raw_class for k in ["human", "person", "man", "woman", "people"]):
                    person_boxes.append(box_tuple)
                    person_confs.append(conf)
                    normalized_objects.append({"class": "Human", "confidence": conf, "box": box_tuple})

            fire_det = len(fire_boxes) > 0
            smoke_det = len(smoke_boxes) > 0
            person_det = len(person_boxes) > 0

            # Human Awareness Threat Classification Matrix
            if fire_det and person_det:
                threat_lvl = "CRITICAL"
                threat_reason = "Human detected near active fire. Immediate evacuation recommended."
            elif fire_det:
                threat_lvl = "HIGH"
                threat_reason = "Active fire candidate detected. Verification sequence active."
            elif smoke_det:
                threat_lvl = "MEDIUM"
                threat_reason = "Smoke accumulation detected. Monitoring zone air quality."
            elif person_det:
                threat_lvl = "Monitoring"
                threat_reason = "Human present in monitored zone. Parameters nominal."
            else:
                threat_lvl = "NOMINAL"
                threat_reason = "Zone clear. All vision metrics nominal."

            with self._lock:
                self._cached_results = {
                    "fire_detected": fire_det,
                    "fire_confidence": max(fire_confs) if fire_confs else 0.0,
                    "fire_boxes": fire_boxes,
                    "smoke_detected": smoke_det,
                    "smoke_confidence": max(smoke_confs) if smoke_confs else 0.0,
                    "smoke_boxes": smoke_boxes,
                    "person_detected": person_det,
                    "person_count": len(person_boxes),
                    "person_confidence": max(person_confs) if person_confs else 0.0,
                    "person_boxes": person_boxes,
                    "roboflow_status": "online",
                    "latency_ms": latency,
                    "threat_level": threat_lvl,
                    "threat_reason": threat_reason,
                    "objects": normalized_objects
                }

        except urllib.error.URLError as ue:
            self.logger.warning(f"Roboflow API connection error: {ue}")
            with self._lock:
                self._cached_results["roboflow_status"] = "AI Offline"
        except Exception as e:
            self.logger.error(f"Error calling Roboflow Workflow: {e}")
            with self._lock:
                self._cached_results["roboflow_status"] = "AI Offline"
        finally:
            self._inference_in_progress = False

    def _extract_predictions(self, data) -> List[dict]:
        """Safely extracts prediction items from arbitrary Roboflow JSON response structures."""
        if not data:
            return []
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict) and any(k in data[0] for k in ('class', 'class_name', 'label')):
                return data
            for item in data:
                res = self._extract_predictions(item)
                if res:
                    return res
        elif isinstance(data, dict):
            if "predictions" in data:
                res = self._extract_predictions(data["predictions"])
                if res:
                    return res
            if "outputs" in data:
                res = self._extract_predictions(data["outputs"])
                if res:
                    return res
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    res = self._extract_predictions(v)
                    if res:
                        return res
        return []

    def _handle_verified_fire(self, results: dict):
        """Triggers Critical Alert, Timeline Event, Mission Dispatch, and Explainable AI Report upon 2.0s verification."""
        try:
            from server.state import app_state, VerificationResult, TimelineEvent, AIReport, MissionItem
            current_zone = getattr(app_state.rover, 'current_zone', 'chem_lab') or 'chem_lab'

            # 1. Update verification result in state
            app_state.verification = VerificationResult(
                zone_id=current_zone,
                verdict="CONFIRMED",
                confidence=round(results.get("fire_confidence", 0.95) * 100, 1),
                method="Roboflow AI Vision",
                timestamp=time.time()
            )

            app_state.set_alert_active(True)
            app_state.update_layout('crisis')

            # 2. Add Timeline Event
            if (time.time() - self._last_fire_time) >= 15.0:
                self._last_fire_time = time.time()
                app_state.add_timeline_event(TimelineEvent(
                    event_type='alert',
                    description=f"🔥 Roboflow AI: VERIFIED FIRE DETECTED (2.0s continuous check, Conf: {int(results.get('fire_confidence', 0.95)*100)}%)!",
                    severity='critical',
                    zone_id=current_zone
                ))

            # 3. Auto-dispatch Emergency Mission
            if app_state.rover and (not app_state.rover.current_mission or app_state.rover.current_mission.status == "COMPLETED"):
                app_state.rover.current_mission = MissionItem(
                    id=f"mission_{int(time.time())}",
                    name="Emergency Fire Inspection & Containment",
                    type="EMERGENCY",
                    target_zone=current_zone,
                    status="IN_PROGRESS",
                    priority="CRITICAL",
                    progress=25
                )

            # 4. Generate Explainable AI Analysis Report
            fire_conf = int(results.get("fire_confidence", 0.95) * 100)
            human_det = results.get("person_detected", False)
            smoke_det = results.get("smoke_detected", False)

            threat_lvl = results.get("threat_level", "CRITICAL")
            threat_reason = results.get("threat_reason", "Fire continuously detected for 2 seconds. Hazardous situation active.")

            report = AIReport(
                summary=f"Roboflow AI Threat Level: {threat_lvl}",
                analysis=f"Incoming Feed -> Roboflow Workflow -> Fire Conf: {fire_conf}%, Smoke: {smoke_det}, Human: {human_det}. Reason: {threat_reason}",
                severity=threat_lvl,
                confidence=f"{fire_conf}%",
                recommendations=[
                    "Immediate evacuation of hazardous area",
                    "Deploy Emergency Rover Inspection & Suppression Mission"
                ],
                timestamp=time.time()
            )
            app_state.update_ai_report(report)

        except Exception as e:
            self.logger.error(f"Error handling verified fire: {e}")

    def _sync_mqtt_state(self, results: dict):
        """Publishes verified telemetry to MQTT broker whenever vision state changes."""
        try:
            curr_state = {
                "fire": results.get("fire_verified", False),
                "smoke": results.get("smoke_detected", False),
                "human": results.get("person_detected", False),
                "fire_count": len(results.get("fire_boxes", [])),
                "smoke_count": len(results.get("smoke_boxes", [])),
                "human_count": results.get("person_count", 0),
                "roboflow_status": results.get("roboflow_status", "AI Offline")
            }

            if curr_state != self._last_published_state:
                self._last_published_state = curr_state
                from server.services import registry
                mqtt_srv = registry.get("MqttService")
                if mqtt_srv and getattr(mqtt_srv, 'is_connected', lambda: False)():
                    payload = {
                        "fire": curr_state["fire"],
                        "smoke": curr_state["smoke"],
                        "human": curr_state["human"],
                        "fire_count": curr_state["fire_count"],
                        "smoke_count": curr_state["smoke_count"],
                        "human_count": curr_state["human_count"],
                        "confidence": round(max(results.get("fire_confidence", 0), results.get("person_confidence", 0), results.get("smoke_confidence", 0)) * 100, 1),
                        "verification_time": 2.0 if curr_state["fire"] else 0.0,
                        "status": "verified" if curr_state["fire"] else "monitoring",
                        "camera": "online",
                        "source": "roboflow",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
                    }
                    mqtt_srv.publish("sentinel/vision/detections", payload)
        except Exception as e:
            self.logger.warning(f"MQTT publish failed: {e}")

    # Architectural placeholders preserved
    def detect_smoke(self, frame) -> bool:
        with self._lock:
            return self._cached_results.get("smoke_detected", False)

    def recognize_face(self, frame) -> bool:
        return False

    def detect_objects(self, frame) -> list:
        with self._lock:
            return self._cached_results.get("objects", [])

    def _simulate_vision(self) -> Dict[str, Any]:
        """Provides dynamic simulation stats if hardware camera features are disabled."""
        import random
        return {
            "motion_detected": random.random() < 0.05,
            "motion_score": round(random.uniform(0.1, 0.8), 2),
            "fire_detected": False,
            "fire_confidence": 0.0,
            "fire_boxes": [],
            "smoke_detected": False,
            "smoke_confidence": 0.0,
            "smoke_boxes": [],
            "person_detected": False,
            "person_count": 0,
            "person_boxes": [],
            "roboflow_status": "online" if self.roboflow_api_key else "AI Offline",
            "fire_verified": False,
            "verification_progress": 0.0,
            "threat_level": "NOMINAL",
            "threat_reason": "Simulated nominal operations.",
            "objects": []
        }

