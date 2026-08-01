import os
import json
import threading
import datetime
import logging
from pathlib import Path
from typing import Dict, Any


from server.services.base_service import BaseService
from server.state import app_state

class AnalyticsService(BaseService):
    """Analytics Engine service.

    Generates periodic reports, exports CSV/PDF, creates graphs, and syncs
    with Convex. Reports are generated on demand via the API or automatically
    via a scheduler defined in ``config/analytics_config.json``.
    """

    def __init__(self, config: dict = None):
        super().__init__("AnalyticsService", config)
        self._config_path = self._find_config_path()
        self._schedule = []  # loaded config entries
        self._stop_event = threading.Event()
        self._thread = None
        self.logger = logging.getLogger(f"Service.{self.name}")

    def _find_config_path(self) -> str:
        current = Path(__file__).resolve()
        for parent in current.parents:
            candidate = parent / 'config' / 'analytics_config.json'
            if candidate.exists():
                return str(candidate)
        return str(current.parents[3] / 'config' / 'analytics_config.json')


    # ---------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------
    def _on_start(self) -> bool:
        self._load_config()
        self._thread = threading.Thread(target=self._scheduler_loop, name="AnalyticsScheduler", daemon=True)
        self._thread.start()
        self.logger.info("AnalyticsService scheduler started.")
        return True

    def _on_stop(self) -> bool:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self.logger.info("AnalyticsService stopped.")
        return True

    # ---------------------------------------------------------------------
    # Configuration handling
    # ---------------------------------------------------------------------
    def _load_config(self):
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._schedule = json.load(f)
            self.logger.info(f"Analytics config loaded: {self._schedule}")
        except Exception as e:
            self.logger.warning(f"Failed to load analytics config ({self._config_path}): {e}")
            self._schedule = []

    # ---------------------------------------------------------------------
    # Scheduler loop – very lightweight demo implementation
    # ---------------------------------------------------------------------
    def _scheduler_loop(self):
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            for entry in self._schedule:
                report_type = entry.get("report_type")
                # For demo purposes we trigger every minute regardless of cron expression.
                # Production code should parse the cron expression.
                try:
                    self._generate_and_sync(report_type)
                except Exception as e:
                    self.logger.error(f"Error generating {report_type} report: {e}")
            # Sleep 60 seconds – adjust as needed.
            self._stop_event.wait(60)

    # ---------------------------------------------------------------------
    # Public API used by HTTP routes and other services
    # ---------------------------------------------------------------------
    def generate_report(self, report_type: str, period: str = "auto") -> Dict[str, Any]:
        """Collect data and build a report dictionary.

        The implementation currently returns placeholder metrics; real logic
        should query ``DatabaseService`` and the in‑memory ``app_state``.
        """
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        # Placeholder – in a real system we would aggregate sensor, mission,
        # alert and battery data here.
        metrics = {
            "temperature_avg": 22.5,
            "humidity_avg": 45.0,
            "gas_ppm_avg": 350,
            "battery_level": getattr(app_state, "rover_state", {}).get("battery_pct", None),
        }
        return {
            "type": report_type,
            "period": period,
            "generated_at": generated_at,
            "metrics": metrics,
        }

    def export_csv(self, report_data: Dict[str, Any]) -> str:
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        # Header
        writer.writerow(["type", "period", "generated_at"])
        writer.writerow([report_data.get("type"), report_data.get("period"), report_data.get("generated_at")])
        # Metrics – flatten simple key/value pairs
        writer.writerow([])
        writer.writerow(["metric", "value"])
        for k, v in report_data.get("metrics", {}).items():
            writer.writerow([k, v])
        return output.getvalue()

    def export_pdf(self, report_data: Dict[str, Any]) -> bytes:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            import io
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            y = 750
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, f"Analytics Report – {report_data.get('type').title()}")
            y -= 30
            c.setFont("Helvetica", 12)
            c.drawString(50, y, f"Period: {report_data.get('period')}")
            y -= 20
            c.drawString(50, y, f"Generated at: {report_data.get('generated_at')}")
            y -= 40
            for metric, value in report_data.get("metrics", {}).items():
                c.drawString(60, y, f"{metric}: {value}")
                y -= 15
            c.showPage()
            c.save()
            return buffer.getvalue()
        except Exception as e:
            self.logger.warning(f"PDF generation failed: {e}")
            return b""

    def get_graph(self, metric: str) -> bytes:
        """Return a PNG image for the requested metric.

        Uses ``matplotlib`` to produce a simple line plot. In production this
        would visualize historical data from the database.
        """
        try:
            import matplotlib.pyplot as plt
            import io
            # Dummy data – replace with real historical series.
            xs = list(range(1, 13))
            ys = [i * 5 + (hash(metric) % 10) for i in xs]
            plt.figure(figsize=(5, 3))
            plt.plot(xs, ys, marker="o")
            plt.title(f"{metric.title()} Trend")
            plt.xlabel("Time")
            plt.ylabel(metric.title())
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format="png")
            plt.close()
            return buf.getvalue()
        except Exception as e:
            self.logger.warning(f"Graph generation failed for {metric}: {e}")
            return b""

    def _generate_and_sync(self, report_type: str):
        """Internal helper – generate a report and push it to Convex.

        The ``ConvexService`` API is assumed to expose a ``sync_analytics_report``
        method; if it does not exist the call is safely ignored.
        """
        report = self.generate_report(report_type)
        # Sync with Convex if available.
        from server.services import registry
        convex_srv = registry.get("ConvexService")
        if convex_srv and hasattr(convex_srv, "sync_analytics_report"):
            try:
                convex_srv.sync_analytics_report(report_type, json.dumps(report))
            except Exception as exc:
                self.logger.warning(f"Convex sync failed: {exc}")
        # Optionally broadcast via WebSocket – omitted for brevity.
        return report
