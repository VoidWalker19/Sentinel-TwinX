"""
server/services/ai_service/modules/mission_report_generator.py — Mission Report & PDF Export AI Engine

Automatically generates comprehensive, structured incident post-mortem and mission reports
with timeline logs, empirical sensor evidence, AI decision rationales, and PDF readiness.
"""

import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class MissionReport:
    report_id: str
    title: str
    mission_id: Optional[str]
    incident_id: Optional[str]
    timestamp: float
    zone_id: Optional[str]
    zone_name: Optional[str]
    mission_type: str
    outcome: str                # 'SUCCESS', 'PARTIAL', 'FALSE_ALARM', 'ABORTED'
    summary: str
    timeline: List[dict]
    sensor_snapshots: Dict[str, dict]
    ai_decisions: List[dict]
    verification_result: Optional[dict]
    distance_traveled_m: float
    battery_consumed_pct: float
    recommendations: List[str]

    def to_markdown(self) -> str:
        date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))
        md = []
        md.append(f"# 📜 SENTINEL TWIN MISSION REPORT — {self.report_id}")
        md.append(f"**Generated:** {date_str} | **Outcome:** `{self.outcome}` | **Zone:** {self.zone_name or 'Facility-Wide'}\n")
        md.append("---")
        md.append("## 📌 Executive Summary")
        md.append(f"{self.summary}\n")
        md.append("## 📊 Mission Telemetry Metrics")
        md.append(f"- **Mission Type:** `{self.mission_type}`")
        md.append(f"- **Distance Traveled:** `{self.distance_traveled_m:.1f} meters`")
        md.append(f"- **Battery Consumed:** `{self.battery_consumed_pct:.1f}%`\n")

        if self.verification_result:
            vr = self.verification_result
            md.append("## 📷 Camera AI Verification Verdict")
            md.append(f"- **Verdict:** `{vr.get('verdict', 'N/A')}` ({vr.get('confidence', 0)}% confidence)")
            md.append(f"- **Method:** `{vr.get('method', 'CV Analysis')}`\n")

        if self.ai_decisions:
            md.append("## 🧠 AI Decision & Rationales (Explainability Log)")
            for d in self.ai_decisions:
                md.append(f"### {d.get('decision_title', 'AI Decision')}")
                md.append(f"- **Severity:** `{d.get('severity')}` | **Confidence:** `{d.get('confidence_pct')}`")
                md.append("- **Reasons:**")
                for r in d.get('reasons', []):
                    md.append(f"  - {r}")
                md.append("")

        if self.timeline:
            md.append("## ⏱️ Timeline of Events")
            md.append("| Time | Event Stage | Description |")
            md.append("| :--- | :--- | :--- |")
            for t in self.timeline:
                ts = time.strftime('%H:%M:%S', time.localtime(t.get('timestamp', time.time())))
                md.append(f"| {ts} | `{t.get('stage', 'INFO')}` | {t.get('message', t.get('description', ''))} |")
            md.append("")

        if self.recommendations:
            md.append("## 💡 Post-Mission Recommendations")
            for rec in self.recommendations:
                md.append(f"- {rec}")

        return "\n".join(md)

    def to_dict(self) -> dict:
        return {
            'report_id': self.report_id,
            'title': self.title,
            'mission_id': self.mission_id,
            'incident_id': self.incident_id,
            'timestamp': self.timestamp,
            'zone_id': self.zone_id,
            'zone_name': self.zone_name,
            'mission_type': self.mission_type,
            'outcome': self.outcome,
            'summary': self.summary,
            'timeline': self.timeline,
            'sensor_snapshots': self.sensor_snapshots,
            'ai_decisions': self.ai_decisions,
            'verification_result': self.verification_result,
            'distance_traveled_m': round(self.distance_traveled_m, 1),
            'battery_consumed_pct': round(self.battery_consumed_pct, 1),
            'recommendations': self.recommendations,
            'markdown': self.to_markdown(),
        }


class MissionReportGenerator:
    """
    Engine for generating structured post-mission reports.
    """

    def generate_report(
        self,
        mission_data: dict,
        timeline_events: List[dict],
        sensor_snapshots: Dict[str, dict],
        ai_decisions: List[dict],
        verification_result: Optional[dict] = None,
        recommendations: List[str] = None,
    ) -> MissionReport:
        mid = mission_data.get('mission_id', f"msn_{int(time.time())}")
        rid = f"rpt_{mid}"
        zname = mission_data.get('target_zone_name') or mission_data.get('target_zone', 'Facility')

        summary = (
            f"Autonomous safety mission '{mission_data.get('description', 'Inspection')}' in {zname} "
            f"completed with status `{mission_data.get('status', 'DONE')}`."
        )

        outcome = "SUCCESS"
        if verification_result:
            if verification_result.get('verdict') == 'FALSE_ALARM':
                outcome = "FALSE_ALARM"

        return MissionReport(
            report_id=rid,
            title=f"Incident Inspection Report — {zname}",
            mission_id=mid,
            incident_id=mission_data.get('incident_id'),
            timestamp=time.time(),
            zone_id=mission_data.get('target_zone'),
            zone_name=zname,
            mission_type=mission_data.get('mission_type', 'INSPECTION'),
            outcome=outcome,
            summary=summary,
            timeline=timeline_events,
            sensor_snapshots=sensor_snapshots,
            ai_decisions=ai_decisions,
            verification_result=verification_result,
            distance_traveled_m=float(mission_data.get('distance_m', 24.5)),
            battery_consumed_pct=float(mission_data.get('battery_consumed', 4.2)),
            recommendations=recommendations or ["Maintain standard monitoring posture."],
        )
