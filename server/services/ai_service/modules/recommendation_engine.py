"""
server/services/ai_service/modules/recommendation_engine.py — Safety Recommendation Engine

Generates prioritized occupant evacuation directions and operator safety recommendations.
"""

from typing import Dict, List, Optional, Any
from engine.config_loader import ZONE_CONFIG, EXIT_ZONES

class RecommendationEngine:
    """
    Generates situation-specific safety recommendations for occupants and operators.
    """

    def generate_recommendations(
        self,
        snapshot: dict,
        hazards: Dict[str, Any],
        predictive_insights: List[Any],
    ) -> List[str]:
        recs: List[str] = []

        system_status = snapshot.get('system_status', 'green')
        overall_risk = snapshot.get('overall_risk', 0)
        risk_scores = snapshot.get('risk_scores', {})
        zones = snapshot.get('zones', {})

        # 1. Immediate Critical Evacuation Directives
        if system_status == 'red':
            # Check for blocked exits
            blocked_exits = [z for z in EXIT_ZONES if zones.get(z, {}).get('blocked')]
            if blocked_exits:
                b_names = [ZONE_CONFIG.get(b, {}).get('name', b) for b in blocked_exits]
                recs.append(f"🚨 EXITS BLOCKED ({', '.join(b_names)}) — Route occupants to secondary emergency exits immediately.")
            else:
                recs.append("🚨 Initiate full building evacuation — broadcast voice alerts on all floors.")
            recs.append("📞 Dispatch emergency fire and rescue services to building location.")

        # 2. Per-Hazard Specific Directives
        for zid, hclass in hazards.items():
            htype = getattr(hclass, 'hazard_type', 'NOMINAL')
            zname = getattr(hclass, 'zone_name', zid)
            sev = getattr(hclass, 'severity', 'NONE')

            if htype == 'FIRE' and sev in ('CRITICAL', 'HIGH'):
                recs.append(f"🔥 {zname}: Cut electrical mains & isolate HVAC ventilation dampers to restrict smoke propagation.")
            elif htype == 'GAS_LEAK':
                recs.append(f"💨 {zname}: Eliminate open ignition sources and activate secondary exhaust fans.")
            elif htype == 'THERMAL_OVERHEAT':
                recs.append(f"🌡️ {zname}: Verify HVAC cooling loop & inspect server/power distribution racks.")
            elif htype == 'CO_HAZARD':
                recs.append(f"⚠️ {zname}: Carbon Monoxide spike — require SCBA respirators for inspection personnel.")
            elif htype == 'PATH_OBSTRUCTION':
                recs.append(f"🚪 {zname}: Physical corridor blockage — dispatch ground team to clear emergency route.")

        # 3. Predictive Maintenance Directives
        for insight in predictive_insights:
            itype = getattr(insight, 'insight_type', '')
            if itype == 'BATTERY_DECAY':
                recs.append("🔋 Rover battery draining rapidly — schedule battery cell replacement.")
            elif itype == 'WEAK_WIFI':
                target = getattr(insight, 'target_zone_name', 'Zone')
                recs.append(f"📶 Weak WiFi link in {target} — verify wireless access point coverage.")
            elif itype == 'SENSOR_FREEZE':
                target = getattr(insight, 'target_zone_name', 'Zone')
                recs.append(f"🔧 Frozen sensor output in {target} — schedule sensor module replacement.")

        # 4. Fallback Safe Operating State
        if not recs:
            recs.append("✅ All building zones operating within normal safety limits.")
            recs.append("🔧 Maintain routine preventive maintenance and surveillance sweeps.")

        return recs[:5]
