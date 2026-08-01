import time
import heapq
import logging
from typing import Dict, List, Optional, Tuple, Any
from server.services.base_service import BaseService
from server.state import ZoneReading, RiskResult

# --- Threshold Constants and Smoother imported from unified engine/chronos.py ---
from engine.chronos import EMAScoreSmoother


class AlertService(BaseService):
    """
    Alert Service running the CHRONOS scoring engine, EMA smoothing filters,
    and Dijkstra egress route recommender.
    """
    def __init__(self, config: dict = None):
        super().__init__("AlertService", config)
        self._smoother = EMAScoreSmoother(alpha=0.35)
        self._zone_graph = {}
        self._exit_zones = set()
        self._zone_config = {}

    def _on_start(self) -> bool:
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        if cfg_srv:
            zones_raw = cfg_srv.get_zones()
            zone_graph = {zid: z.get("adjacencies", []) for zid, z in zones_raw.items()}
            exit_zones = {zid for zid, z in zones_raw.items() if z.get("is_exit", False)}
            zone_config = {
                zid: {
                    'name': z.get('name', zid),
                    'floor': z.get('floor', 1),
                    'high_risk_baseline': z.get('high_risk_baseline', False)
                }
                for zid, z in zones_raw.items()
            }
            self.configure_building_topology(zone_graph, exit_zones, zone_config)
        self.logger.info("Alert service initialized.")
        return True

    def configure_building_topology(self, zone_graph: dict, exit_zones: set, zone_config: dict):
        self._zone_graph = zone_graph
        self._exit_zones = exit_zones
        self._zone_config = zone_config

    def compute_chronos_risk(self, reading: ZoneReading, settings: dict = None,
                              health_status=None, calibrated_thresholds: dict = None) -> RiskResult:
        from engine.chronos import compute_risk, SCORE_RED, SCORE_ORANGE, SCORE_YELLOW

        # 1. Compute raw risk result using unified chronos logic
        raw_res = compute_risk(reading, settings, health_status, calibrated_thresholds)

        if raw_res.status == 'offline':
            self._smoother.reset(reading.zone_id)
            return raw_res

        # Overrides logic - bypass smoothing for operator overrides
        overrides = settings.get('overrides', {}) if settings else {}
        if reading.zone_id in overrides:
            self._smoother.smooth(reading.zone_id, raw_res.score)
            return raw_res

        # 2. Apply local EMA smoothing
        smoothed_score = self._smoother.smooth(reading.zone_id, raw_res.score)

        # 3. Determine smoothed status
        if smoothed_score >= SCORE_RED:
            status = 'red'
        elif smoothed_score >= SCORE_ORANGE:
            status = 'orange'
        elif smoothed_score >= SCORE_YELLOW:
            status = 'yellow'
        else:
            status = 'green'

        reasons = list(raw_res.reasons)
        diff = abs(raw_res.score - smoothed_score)
        if diff >= 5:
            reasons.append(f"📊 EMA smoothed: raw {raw_res.score} → smoothed {smoothed_score} (delta {diff:+d})")

        return RiskResult(
            zone_id=reading.zone_id,
            score=smoothed_score,
            status=status,
            reasons=reasons,
            timestamp=raw_res.timestamp
        )

    def find_safest_exit(self, origin_zone: str, blocked_zones: List[str],
                         high_risk_zones: List[str], risk_scores: dict) -> Tuple[Optional[str], List[str], float]:
        from engine.recommender import find_safest_exit
        return find_safest_exit(origin_zone, blocked_zones, high_risk_zones, risk_scores)

    def get_all_evac_recommendations(self, risk_scores: dict, zones_data: dict) -> dict:
        blocked = [zid for zid, z in zones_data.items() if z.get('blocked')]
        high_risk = [zid for zid, r in risk_scores.items() if (r.get('score', 0) if isinstance(r, dict) else getattr(r, 'score', 0)) >= 60]

        recs = {}
        for zone_id in risk_scores:
            exit_id, path, cost = self.find_safest_exit(zone_id, blocked, high_risk, risk_scores)
            recs[zone_id] = {
                'exit': exit_id,
                'exit_name': self._zone_config.get(exit_id, {}).get('name', exit_id) if exit_id else 'Unknown',
                'path': path,
                'clear': exit_id is not None,
                'cost': cost,
            }
        return recs

    def generate_evac_tts_message(self, risk_scores: dict, zones_data: dict) -> str:
        from engine.recommender import generate_evacuation_message
        return generate_evacuation_message(risk_scores, zones_data)
