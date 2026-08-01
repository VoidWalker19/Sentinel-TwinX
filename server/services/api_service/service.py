import os
import io
import time
import json
import asyncio
import logging
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel

class ConnectNetworkRequest(BaseModel):
    ssid: str
    password: str = ""

from server.services.base_service import BaseService
from server.state import app_state, TimelineEvent
from server.action_system import execute_action
from simulator.sensor_sim import sensor_simulator

class ApiService(BaseService):
    """
    API Service that hosts the FastAPI application, mounts endpoints,
    manages WebSocket client connections, and broadcasts updates.
    """
    def __init__(self, config: dict = None):
        super().__init__("ApiService", config)
        self.app = FastAPI(title="Sentinel Twin X API Server", lifespan=self.lifespan_context)
        self.active_connections: Set[WebSocket] = set()
        self._setup_routes()
        self._broadcaster_task = None

    def _setup_routes(self):
        # WebSocket Endpoint
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
            self.logger.info(f"WS client connected. Total clients: {len(self.active_connections)}")

            # Send initial state snapshot
            try:
                await websocket.send_json(app_state.get_snapshot())
            except Exception:
                self.active_connections.discard(websocket)
                return

            try:
                async for message in websocket.iter_json():
                    msg_type = message.get("type")
                    self.logger.info(f"[WS Command] {msg_type} -> {message}")
                    
                    await self._handle_ws_command(msg_type, message)
            except WebSocketDisconnect:
                self.active_connections.discard(websocket)
                self.logger.info("WS client disconnected.")
            except Exception as e:
                self.logger.error(f"WS connection error: {e}")
                self.active_connections.discard(websocket)

        # HTTP API Routes
        @self.app.get("/api/state")
        def get_api_state():
            return app_state.get_snapshot()

        @self.app.get("/api/history/sensors")
        def get_history_sensors():
            from server.services import registry
            hist = registry.get("HistoryService")
            if hist:
                return hist.get_sensor_statistics()
            return JSONResponse(status_code=500, content={"error": "History service offline"})

        @self.app.get("/api/history/alerts")
        def get_history_alerts():
            from server.services import registry
            hist = registry.get("HistoryService")
            if hist:
                return hist.get_alert_statistics()
            return JSONResponse(status_code=500, content={"error": "History service offline"})

        @self.app.get("/api/history/battery")
        def get_history_battery():
            from server.services import registry
            hist = registry.get("HistoryService")
            if hist:
                return hist.get_battery_decay()
            return JSONResponse(status_code=500, content={"error": "History service offline"})

        @self.app.post("/api/backup/create")
        def trigger_backup():
            from server.services import registry
            backup = registry.get("BackupService")
            if backup:
                path = backup.create_backup()
                if path:
                    return {"status": "success", "file": os.path.basename(path)}
                return JSONResponse(status_code=500, content={"error": "Backup creation failed"})
            return JSONResponse(status_code=500, content={"error": "Backup service offline"})

        @self.app.get("/api/export-audit")
        def export_audit():
            csv_data = app_state.export_audit_csv()
            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=sentinel_audit.csv"}
            )

        @self.app.get("/api/building-config")
        def get_building_config():
            from server.services import registry
            cfg_srv = registry.get("ConfigurationService")
            if cfg_srv:
                return cfg_srv.get_building_config()
            return JSONResponse(status_code=500, content={"error": "Config service offline"})

        # Network & Wi-Fi Management Endpoints
        @self.app.get("/api/network/status")
        def get_network_status_endpoint():
            from server.services.network_manager import get_network_status
            return get_network_status()

        @self.app.get("/api/network/scan")
        def scan_network_endpoint():
            from server.services.network_manager import scan_wifi_networks
            networks = scan_wifi_networks()
            return {"networks": networks}

        @self.app.post("/api/network/connect")
        def connect_network_endpoint(payload: ConnectNetworkRequest):
            from server.services.network_manager import connect_wifi
            res = connect_wifi(payload.ssid, payload.password)
            if res.get("status") == "error":
                return JSONResponse(status_code=400, content=res)
            return res
        
        # Analytics report endpoints
        @self.app.get("/api/reports/{report_type}")
        def get_report(report_type: str, period: str = "auto"):
            from server.services import registry
            analytics_srv = registry.get("AnalyticsService")
            if analytics_srv:
                return analytics_srv.generate_report(report_type, period)
            return JSONResponse(status_code=500, content={"error": "Analytics service offline"})

        @self.app.get("/api/reports/{report_type}/csv")
        def get_report_csv(report_type: str, period: str = "auto"):
            from server.services import registry
            analytics_srv = registry.get("AnalyticsService")
            if analytics_srv:
                report = analytics_srv.generate_report(report_type, period)
                csv_data = analytics_srv.export_csv(report)
                return StreamingResponse(io.StringIO(csv_data), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"})
            return JSONResponse(status_code=500, content={"error": "Analytics service offline"})

        @self.app.get("/api/reports/{report_type}/pdf")
        def get_report_pdf(report_type: str, period: str = "auto"):
            from server.services import registry
            analytics_srv = registry.get("AnalyticsService")
            if analytics_srv:
                report = analytics_srv.generate_report(report_type, period)
                pdf_bytes = analytics_srv.export_pdf(report)
                return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}_report.pdf"})
            return JSONResponse(status_code=500, content={"error": "Analytics service offline"})

        @self.app.get("/api/reports/graph")
        def get_report_graph(metric: str):
            from server.services import registry
            analytics_srv = registry.get("AnalyticsService")
            if analytics_srv:
                img_bytes = analytics_srv.get_graph(metric)
                return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png")
            return JSONResponse(status_code=500, content={"error": "Analytics service offline"})

        # Diagnostics endpoints
        @self.app.post("/api/diagnostics/simulation")
        async def set_simulation(mode: str, value: str):
            from server.services import registry
            diag = registry.get("DiagnosticsService")
            if diag:
                val = value
                if value.lower() == 'true':
                    val = True
                elif value.lower() == 'false':
                    val = False
                elif value.startswith("{") or value.startswith("["):
                    import json
                    try:
                        val = json.loads(value)
                    except Exception:
                        pass
                
                # Special parsing for dict values
                if mode == "sensor_failure" and isinstance(val, str):
                    if ":" in val:
                        parts = val.split(":")
                        val = {parts[0]: parts[1].lower() == 'true'}
                diag.set_simulation(mode, val)
                return {"status": "success", "mode": mode, "value": val}
            return JSONResponse(status_code=500, content={"error": "Diagnostics service offline"})

        @self.app.get("/api/diagnostics/simulation")
        def get_simulations():
            from server.services import registry
            diag = registry.get("DiagnosticsService")
            if diag:
                return diag.get_all_simulations()
            return JSONResponse(status_code=500, content={"error": "Diagnostics service offline"})

        @self.app.post("/api/diagnostics/run")
        def run_self_tests():
            from server.services import registry
            diag = registry.get("DiagnosticsService")
            if diag:
                return diag.run_self_tests()
            return JSONResponse(status_code=500, content={"error": "Diagnostics service offline"})

        # Health endpoints
        @self.app.get("/api/health")
        def get_health():
            from server.services import registry
            health_mon = registry.get("HealthMonitorService")
            if health_mon:
                return health_mon.get_status()
            return JSONResponse(status_code=500, content={"error": "Health monitor service offline"})

        @self.app.get("/api/health/history")
        def get_health_history(limit: int = 20):
            from server.services import registry
            health_mon = registry.get("HealthMonitorService")
            if health_mon:
                return health_mon.get_history(limit)
            return JSONResponse(status_code=500, content={"error": "Health monitor service offline"})

        @self.app.get("/api/video-feed")
        @self.app.get("/video_feed")
        async def get_video_feed():
            from server.services import registry
            cam_srv = registry.get("CameraService")
            vision_srv = registry.get("VisionService")
            
            async def generate_frames():
                import cv2
                import asyncio
                try:
                    while True:
                        frame = None
                        if cam_srv:
                            frame = cam_srv.get_latest_frame()
                        
                        if frame is not None:
                            frame_copy = frame.copy()
                            if vision_srv:
                                res = vision_srv.process_frame(frame_copy)
                                try:
                                    import numpy as np
                                    fh, fw = frame_copy.shape[:2]
                                    
                                    # 1. Fire Bounding Boxes (Red)
                                    fire_conf = res.get("fire_confidence", 0.0)
                                    for (bx, by, bw, bh) in res.get("fire_boxes", []):
                                        cv2.rectangle(frame_copy, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
                                        cv2.putText(frame_copy, f"FIRE {int(fire_conf * 100)}%", (bx, max(15, by - 5)), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                                    # 2. Smoke Bounding Boxes (Orange)
                                    smoke_conf = res.get("smoke_confidence", 0.0)
                                    for (sx, sy, sw, sh) in res.get("smoke_boxes", []):
                                        cv2.rectangle(frame_copy, (sx, sy), (sx + sw, sy + sh), (0, 165, 255), 2)
                                        cv2.putText(frame_copy, f"SMOKE {int(smoke_conf * 100)}%", (sx, max(15, sy - 5)), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

                                    # 3. Human / Person Bounding Boxes (Cyan/Yellow)
                                    person_conf = res.get("person_confidence", 0.0)
                                    for (px, py, pw, ph) in res.get("person_boxes", []):
                                        cv2.rectangle(frame_copy, (px, py), (px + pw, py + ph), (0, 255, 255), 2)
                                        cv2.putText(frame_copy, f"HUMAN {int(person_conf * 100)}%", (px, max(15, py - 5)), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                                    # 4. Top-Right Roboflow AI Telemetry Card Overlay
                                    roboflow_st = res.get("roboflow_status", "AI Offline")
                                    fire_verif = res.get("fire_verified", False)
                                    threat_lvl = res.get("threat_level", "NOMINAL")

                                    panel_w = 240
                                    panel_h = 110 if (res.get("fire_detected") or res.get("smoke_detected")) else 45
                                    px1, py1 = fw - panel_w - 15, 15
                                    px2, py2 = fw - 15, 15 + panel_h

                                    sub = frame_copy[py1:py2, px1:px2]
                                    if sub.shape[0] == panel_h and sub.shape[1] == panel_w:
                                        card_bg = np.zeros_like(sub) if not fire_verif else np.full_like(sub, (0, 0, 80))
                                        frame_copy[py1:py2, px1:px2] = cv2.addWeighted(sub, 0.35, card_bg, 0.65, 0)
                                        card_color = (0, 0, 255) if fire_verif else (0, 200, 100) if roboflow_st == "online" else (0, 165, 255)
                                        cv2.rectangle(frame_copy, (px1, py1), (px2, py2), card_color, 1)

                                    if fire_verif:
                                        cv2.putText(frame_copy, "ALERT: FIRE VERIFIED (2.0s)", (px1 + 10, py1 + 25), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                        cv2.putText(frame_copy, f"CONFIDENCE: {int(fire_conf * 100)}%", (px1 + 10, py1 + 48), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)
                                        cv2.putText(frame_copy, f"HUMAN DETECTED: {'YES' if res.get('person_detected') else 'NO'}", (px1 + 10, py1 + 68), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255) if res.get('person_detected') else (200, 200, 200), 1)
                                        cv2.putText(frame_copy, f"THREAT: {threat_lvl}", (px1 + 10, py1 + 88), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                                    else:
                                        ai_label = f"ROBOFLOW AI: {roboflow_st.upper()}"
                                        ai_color = (0, 230, 100) if roboflow_st == "online" else (100, 100, 100)
                                        cv2.putText(frame_copy, ai_label, (px1 + 10, py1 + 25), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, ai_color, 1)

                                    # 5. Bottom-Left Object Counters
                                    counts = []
                                    if res.get("fire_detected"):
                                        counts.append(f"FIRE: {len(res.get('fire_boxes', []))}")
                                    if res.get("smoke_detected"):
                                        counts.append(f"SMOKE: {len(res.get('smoke_boxes', []))}")
                                    if res.get("person_detected"):
                                        counts.append(f"HUMAN: {res.get('person_count', 0)}")
                                    
                                    if counts:
                                        cv2.putText(frame_copy, " | ".join(counts), (20, fh - 20),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                                except Exception:
                                    pass
                            
                            try:
                                ret, jpeg = cv2.imencode('.jpg', frame_copy, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                                if ret:
                                    jpeg_bytes = jpeg.tobytes()
                                    yield (b'--frame\r\n'
                                           b'Content-Type: image/jpeg\r\n'
                                           b'Content-Length: ' + str(len(jpeg_bytes)).encode() + b'\r\n\r\n' +
                                           jpeg_bytes + b'\r\n')
                            except Exception:
                                pass
                        await asyncio.sleep(0.04)
                except (asyncio.CancelledError, GeneratorExit, Exception):
                    pass

            return StreamingResponse(
                generate_frames(),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive"
                }
            )

        @self.app.post("/api/debug/inject")
        def inject_debug_sensor(zone: str, temp: float = None, smoke: int = None, blocked: bool = False):
            # Save overrides in state
            overrides = app_state.settings.setdefault('overrides', {})
            if temp is not None:
                overrides[zone] = 'red' if temp >= 65 else 'orange' if temp >= 50 else 'yellow'
            elif smoke is not None:
                overrides[zone] = 'red' if smoke >= 600 else 'orange' if smoke >= 400 else 'yellow'
            
            # Immediately trigger timeline alert
            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description=f"💥 Operator INJECTED sensor values to {zone.upper()}: temp={temp}, smoke={smoke}, blocked={blocked}",
                severity='critical',
                zone_id=zone
            ))
            
            # Record directly to DatabaseService if active
            from server.services import registry
            db_srv = registry.get("DatabaseService")
            if db_srv:
                db_srv.log_sensor_reading(zone, temp, smoke, 35.0, blocked)
                db_srv.log_alert(zone, 85, overrides[zone], "Debug injection alert")

            # Push immediate broadcast
            asyncio.create_task(self.broadcast_state())
            return {"status": "success", "zone": zone, "overrides": overrides}

        @self.app.post("/api/set-gemini-key")
        def set_gemini_key(key: str):
            from server.services import registry
            ai_srv = registry.get("AiService")
            if ai_srv:
                ai_srv.set_gemini_key(key)
            return {"status": "success", "message": "Gemini API key loaded successfully."}

        @self.app.get("/api/camera/stream")
        async def video_feed():
            from server.services import registry
            camera_srv = registry.get("CameraService")
            
            async def frame_generator():
                import asyncio
                try:
                    while True:
                        if camera_srv:
                            jpeg_bytes = camera_srv.get_latest_frame_jpeg()
                            if jpeg_bytes:
                                yield (b'--frame\r\n'
                                       b'Content-Type: image/jpeg\r\n'
                                       b'Content-Length: ' + str(len(jpeg_bytes)).encode() + b'\r\n\r\n' +
                                       jpeg_bytes + b'\r\n')
                        await asyncio.sleep(0.04)
                except (asyncio.CancelledError, GeneratorExit, Exception):
                    pass
                    
            return StreamingResponse(
                frame_generator(),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive"
                }
            )

        @self.app.get("/api/camera/capture")
        def capture_frame():
            from server.services import registry
            camera_srv = registry.get("CameraService")
            if camera_srv:
                jpeg_bytes = camera_srv.get_latest_frame_jpeg()
                if jpeg_bytes:
                    return StreamingResponse(io.BytesIO(jpeg_bytes), media_type="image/jpeg")
            return JSONResponse(status_code=404, content={"status": "error", "message": "Camera feed unavailable"})

        @self.app.get("/api/camera/status")
        def get_camera_status():
            """Returns camera hardware presence and stream health metadata."""
            from server.services import registry
            camera_srv = registry.get("CameraService")
            if not camera_srv:
                return JSONResponse(status_code=503, content={"status": "error", "message": "Camera service offline"})
            last_frame = camera_srv.get_latest_frame()
            frame_age_ms = None
            is_live = getattr(camera_srv, 'is_live_capture', False)
            is_simulated = getattr(camera_srv, 'is_simulated', True)
            is_streaming = last_frame is not None
            return {
                "is_live_capture": is_live,
                "is_simulated": is_simulated,
                "is_streaming": is_streaming,
                "frame_age_ms": frame_age_ms,
                "camera_index": getattr(camera_srv, 'camera_index', 0),
                "frame_rate": getattr(camera_srv, 'frame_rate', 5.0),
                "resolution": {
                    "width": getattr(camera_srv, 'width', 640),
                    "height": getattr(camera_srv, 'height', 480),
                },
                "source": "live_hardware" if is_live else "simulated_feed",
                "status": "streaming" if is_streaming else "offline",
            }

        @self.app.get("/api/mqtt/status")
        def get_mqtt_status():
            """Returns MQTT broker connection state and tracked ESP32 node statuses."""
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if not mqtt_srv:
                return JSONResponse(status_code=503, content={"status": "error", "message": "MQTT service offline"})
            is_connected = mqtt_srv.is_connected()
            node_statuses = getattr(mqtt_srv, '_node_statuses', {})
            last_heartbeat = getattr(mqtt_srv, 'get_last_heartbeat', lambda: 0.0)()
            return {
                "connected": is_connected,
                "broker_host": getattr(mqtt_srv, '_broker_host', 'unknown'),
                "broker_port": getattr(mqtt_srv, '_broker_port', 1883),
                "connected_nodes": sum(1 for v in node_statuses.values() if v.get('online', False)),
                "total_nodes": len(node_statuses),
                "last_heartbeat": last_heartbeat,
                "last_heartbeat_age_s": round(time.time() - last_heartbeat, 1) if last_heartbeat > 0 else None,
                "node_statuses": {
                    zone_id: {
                        "online": info.get('online', False),
                        "last_seen": info.get('last_seen', 0),
                        "rssi": info.get('rssi', None),
                    }
                    for zone_id, info in node_statuses.items()
                },
            }

        @self.app.post("/api/ai/query")
        def query_ai_assistant(payload: dict):
            query = payload.get("query", "")
            if not query:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Query parameter is required"})
                
            from server.services import registry
            ai_srv = registry.get("AiService")
            if ai_srv:
                response = ai_srv.generate_chat_response(query)
                return {"status": "success", "response": response}
                
            return JSONResponse(status_code=500, content={"status": "error", "message": "AI Service is currently offline"})

        @self.app.get("/api/ai/explanations")
        def get_ai_explanations():
            from server.services import registry
            ai_srv = registry.get("AiService")
            if ai_srv:
                return {"status": "success", "explanations": ai_srv.get_explanations()}
            return JSONResponse(status_code=500, content={"status": "error", "message": "AI Service offline"})

        @self.app.get("/api/ai/insights")
        def get_ai_insights():
            from server.services import registry
            ai_srv = registry.get("AiService")
            if ai_srv:
                return {"status": "success", "insights": ai_srv.get_insights()}
            return JSONResponse(status_code=500, content={"status": "error", "message": "AI Service offline"})

        @self.app.get("/api/ai/incidents")
        def get_ai_incidents():
            from server.services import registry
            ai_srv = registry.get("AiService")
            if ai_srv and hasattr(ai_srv, 'incident_engine'):
                return {"status": "success", "active_incidents": ai_srv.incident_engine.get_all_active()}
            return JSONResponse(status_code=500, content={"status": "error", "message": "AI Service offline"})

        # Mount static directory
        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static")),
        ]
        static_path = None
        for cand in candidates:
            if os.path.exists(cand):
                static_path = cand
                break

        if static_path:
            self.app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
            self.logger.info(f"Mounted static folder from {static_path}")
        else:
            self.logger.warning("Static directory not found in candidate paths!")

    @asynccontextmanager
    async def lifespan_context(self, app: FastAPI):
        # Start all other services on startup
        from server.services import registry
        from server.scheduler import Scheduler
        self.logger.info("Initializing services on Uvicorn startup lifespan...")
        
        # Start dependencies (excluding api_service to prevent recursion)
        registry.start_all()
        
        # Initialize and start data bridge based on SENTINEL_MODE
        from server.data_bridge import create_bridge
        mode = os.environ.get('SENTINEL_MODE', 'sim')
        port = os.environ.get('SENTINEL_PORT', 'COM3')
        self._bridge = create_bridge(mode, port)
        self._bridge.start()
        self.logger.info(f"Data bridge started in mode: {mode} (port={port})")

        # Initialize and start background Scheduler loop thread
        self._scheduler = Scheduler()
        self._scheduler.start()
        self.logger.info("Background Scheduler thread started.")
        
        loop = asyncio.get_running_loop()
        def thread_safe_broadcast():
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_state(), loop)
        
        ai_srv = registry.get("AiService")
        if ai_srv:
            ai_srv.websocket_broadcast_callback = thread_safe_broadcast

        # Start continuous state broadcaster
        self._broadcaster_task = asyncio.create_task(self._state_broadcaster_loop())
        
        self.logger.info("Sentinel Twin X backend pipelines booted successfully.")
        yield
        
        # Teardown services
        self.logger.info("Tearing down services on Uvicorn shutdown lifespan...")
        if self._broadcaster_task:
            self._broadcaster_task.cancel()
            
        if hasattr(self, '_bridge') and self._bridge:
            self.logger.info("Stopping Data bridge thread...")
            self._bridge.stop()
            try:
                self._bridge.join(timeout=2.0)
            except Exception:
                pass

        if hasattr(self, '_scheduler') and self._scheduler:
            self.logger.info("Stopping Scheduler thread...")
            self._scheduler.stop()
            self._scheduler.join(timeout=2.0)
        
        registry.stop_all()

    async def broadcast_state(self):
        if not self.active_connections:
            return
        snapshot = app_state.get_snapshot()
        app_state.clear_highlight()
        
        # Send json to all active clients
        for ws in list(self.active_connections):
            try:
                await ws.send_json(snapshot)
            except Exception:
                self.active_connections.discard(ws)

    async def _state_broadcaster_loop(self):
        while True:
            try:
                await self.broadcast_state()
            except Exception as e:
                self.logger.error(f"Error in broadcast loop: {e}")
            await asyncio.sleep(2.0)

    async def _handle_ws_command(self, msg_type: str, message: dict):
        if msg_type == "approve_action":
            action_id = message.get("id")
            pending = app_state.remove_pending_action(action_id)
            if pending:
                execute_action(pending.action, pending.params, source="AI (Approved)")
                app_state.add_timeline_event(TimelineEvent(
                    event_type='dispatch',
                    description=f"✅ Operator APPROVED action: {pending.action}",
                    severity='info'
                ))
            await self.broadcast_state()

        elif msg_type == "reject_action":
            action_id = message.get("id")
            pending = app_state.remove_pending_action(action_id)
            if pending:
                app_state.log_audit(pending.action, pending.params, "AI (Rejected)", pending.reason, "Rejected")
                app_state.add_timeline_event(TimelineEvent(
                    event_type='info',
                    description=f"❌ Operator REJECTED proposed action: {pending.action}",
                    severity='warning'
                ))
            await self.broadcast_state()

        elif msg_type == "set_autonomous":
            enabled = bool(message.get("enabled", False))
            app_state.set_autonomous_mode(enabled)
            app_state.add_timeline_event(TimelineEvent(
                event_type='reset',
                description=f"⚙️ Autonomous Action Execution set to {'ENABLED' if enabled else 'DISABLED'}",
                severity='warning'
            ))
            await self.broadcast_state()

        elif msg_type == "update_setting":
            key = message.get("key")
            val = message.get("value")
            app_state.update_settings(key, val)
            await self.broadcast_state()

        elif msg_type == "change_telemetry_mode":
            mode = message.get("mode")
            port = message.get("port")
            broker = message.get("broker")
            
            # Stop existing bridge if running
            if hasattr(self, '_bridge') and self._bridge:
                self.logger.info("Stopping old Data bridge thread...")
                self._bridge.stop()
                try:
                    self._bridge.join(timeout=2.0)
                except Exception:
                    pass
            
            # Update environment variables
            if mode == 'mqtt' and broker and "192.168.1.102" not in broker and "192.168.0.124" not in broker and "10.10.0.213" not in broker:
                existing_broker = os.getenv('MQTT_BROKER', '')
                if existing_broker.startswith('ws://') and not broker.startswith('ws://'):
                    broker = f"ws://{broker}"
                    if ':' in existing_broker:
                        port_suffix = existing_broker.split(':')[-1]
                        if port_suffix.isdigit() and ':' not in broker[5:]:
                            broker = f"{broker}:{port_suffix}"
                elif existing_broker.startswith('wss://') and not broker.startswith('wss://'):
                    broker = f"wss://{broker}"
                    if ':' in existing_broker:
                        port_suffix = existing_broker.split(':')[-1]
                        if port_suffix.isdigit() and ':' not in broker[6:]:
                            broker = f"{broker}:{port_suffix}"
                os.environ['MQTT_BROKER'] = broker
            if port:
                os.environ['SENTINEL_PORT'] = port
            os.environ['SENTINEL_MODE'] = mode
            
            # Create and start new bridge
            from server.data_bridge import create_bridge
            self._bridge = create_bridge(mode, port or 'COM3')
            self._bridge.start()
            self.logger.info(f"Data bridge switched dynamically to: {mode} (port={port}, broker={broker})")
            
            # Add timeline event
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description=f"🔄 Telemetry mode switched to {mode.upper()} ({port or broker or 'SIM'})",
                severity='info'
            ))
            await self.broadcast_state()

        elif msg_type == "focus_zone":
            zone = message.get("zone")
            app_state.update_layout(app_state.layout_mode, focused_zone=zone)
            await self.broadcast_state()

        elif msg_type == "set_layout":
            mode = message.get("mode")
            app_state.update_layout(mode, focused_zone=app_state.focused_zone)
            await self.broadcast_state()

        elif msg_type == "inject_scenario":
            scenario = message.get("scenario")
            sensor_simulator.inject_incident(scenario)
            if scenario == 'reset':
                if 'overrides' in app_state.settings:
                    app_state.settings['overrides'].clear()
                app_state.clear_alert()
                with app_state._lock:
                    app_state.pending_actions.clear()
            
            app_state.add_timeline_event(TimelineEvent(
                event_type='reset' if scenario == 'reset' else 'alert',
                description=f"🚨 Demo Scenario Injected: {scenario.upper()}",
                severity='info' if scenario == 'reset' else 'critical'
            ))
            await self.broadcast_state()

        elif msg_type == "manual_action":
            action = message.get("action")
            params = message.get("params", {})
            params['reason'] = params.get('reason', 'Operator manual command execution')

            # Translate high-level UI commands that map to MissionService FSM transitions
            if action in ("pause_mission", "Pause"):
                from server.services import registry
                mission_srv = registry.get("MissionService")
                if mission_srv and mission_srv.active_mission:
                    mission_srv.active_mission.status = "PAUSED"
                    mission_srv.fsm_state = "PAUSED"
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='info',
                        description="⏸️ Operator paused active mission.",
                        severity='info',
                    ))
                await self.broadcast_state()
                return

            if action in ("resume_mission", "Resume", "Autonomous Patrol"):
                from server.services import registry
                mission_srv = registry.get("MissionService")
                if mission_srv and mission_srv.active_mission and mission_srv.active_mission.status == "PAUSED":
                    mission_srv.active_mission.status = "ACTIVE"
                    mission_srv.fsm_state = "ACTIVE"
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='info',
                        description="▶️ Operator resumed active mission.",
                        severity='info',
                    ))
                await self.broadcast_state()
                return

            if action in ("abort_mission", "Stop"):
                from server.services import registry
                mission_srv = registry.get("MissionService")
                if mission_srv and mission_srv.active_mission:
                    mission_srv.active_mission.status = "ABORTED"
                    mission_srv.fsm_state = "IDLE"
                    mission_srv.active_mission = None
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='info',
                        description="⏹️ Operator aborted active mission.",
                        severity='warning',
                    ))
                await self.broadcast_state()
                return

            # All other actions route through the standard allowlist executor
            execute_action(action, params, source="Manual")
            await self.broadcast_state()

        elif msg_type in ("publish_mqtt", "rover_mission_command"):
            topic = message.get("topic", "sentinel/commands/rover")
            payload = message.get("payload")
            if isinstance(payload, dict):
                cmd = payload.get("command", "")
                payload_str = json.dumps(payload)
            else:
                cmd = str(message.get("command", ""))
                payload_str = json.dumps({"command": cmd})

            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                mqtt_srv.publish(topic, payload_str)
            else:
                self.logger.warning(f"MQTT service not active/connected. Payload prepared for topic '{topic}': {payload_str}")

            # Update backend rover status for Mission Control tracking
            if cmd == "start":
                app_state.rover.status = "patrolling"
            elif cmd == "pause":
                app_state.rover.status = "paused"
            elif cmd == "stop":
                app_state.rover.status = "idle"
            elif cmd == "emergency":
                app_state.rover.status = "emergency"

            app_state.add_timeline_event(TimelineEvent(
                event_type='dispatch' if cmd in ('start', 'emergency') else 'info',
                description=f"📡 MQTT Published [{topic}]: {payload_str}",
                severity='critical' if cmd == 'emergency' else 'info'
            ))
            await self.broadcast_state()


    def _on_start(self) -> bool:
        # FastAPI starts automatically via Uvicorn lifecycle, so we return True
        return True

    def _on_stop(self) -> bool:
        return True
