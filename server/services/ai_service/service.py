import os
import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, List, Dict, Tuple, Any

from server.services.base_service import BaseService
from server.state import app_state, AIReport, TimelineEvent
from server.action_system import validate_action, action_needs_approval, execute_action
from ai.templates import generate_report as template_report
from engine.config_loader import ZONE_CONFIG

# Import Modular AI Engines
from server.services.ai_service.modules.hazard_detection import HazardDetectionEngine
from server.services.ai_service.modules.decision_engine import DecisionEngine
from server.services.ai_service.modules.mission_intelligence import MissionIntelligenceEngine
from server.services.ai_service.modules.incident_engine import IncidentEngine
from server.services.ai_service.modules.predictive_analysis import PredictiveAnalysisEngine
from server.services.ai_service.modules.navigation_intelligence import NavigationIntelligenceEngine
from server.services.ai_service.modules.recommendation_engine import RecommendationEngine
from server.services.ai_service.modules.mission_report_generator import MissionReportGenerator
from server.services.ai_service.modules.analytics_engine import AnalyticsAIEngine

_SYSTEM_PROMPT = """You are SENTINEL AI, the central AI decision and incident management engine of the Sentinel Twin building digital twin.
You receive real-time multi-sensor telemetry, classified hazard signatures, and predictive trend analysis.

Valid Zone IDs in this building:
- "chem_lab" (Chemistry Lab)
- "cad_lab" (CAD Lab)
- "kitchen" (Kitchen)
- "corridor" (Main Corridor)
- "classroom_1" (Classroom 1)
- "atl_lab" (ATL Lab)
- "classroom_2" (Classroom 2)

Available actions you can propose (ONLY use these exact action names and required parameters):
- "dispatch_rover": {"zone": "<valid_zone_id>", "reason": "<why>"}
- "recall_rover": {"reason": "<why>"}
- "set_zone_status": {"zone": "<valid_zone_id>", "status": "green"|"yellow"|"red", "reason": "<why>"}
- "set_alarm": {"status": true|false, "reason": "<why>"}
- "tune_threshold": {"key": "<setting_key>", "value": <number>, "reason": "<why>"}
- "focus_ui": {"zone": "<valid_zone_id>", "reason": "<why>"}
- "set_layout": {"layout_mode": "standard"|"crisis"|"focus", "reason": "<why>"}

CRITICAL RULES:
1. Do NOT invent action names (e.g. do NOT use "continue_rover_patrol").
2. "set_zone_status" MUST include BOTH "zone" and "status".
3. Use ONLY valid Zone IDs listed above for "zone" parameters.

You MUST respond ONLY with a single JSON object. No markdown formatting, no code block tickmarks.


JSON format:
{
  "summary": "One sentence, max 40 words summarizing the status.",
  "analysis": "2-3 sentences analyzing sensor values and hazards.",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "confidence": "e.g. 95%",
  "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3", "Recommendation 4", "Recommendation 5"],
  "reasoning": "A paragraph explaining the rationales for proposing actions.",
  "actions": [
    {
      "action": "action_name",
      "params": {
        "key1": "val1",
        "reason": "mandatory justification"
      }
    }
  ]
}"""

_USER_PROMPT_TEMPLATE = """Current building status:
- Overall risk score: {overall_risk}/100
- System status: {system_status}
- Number of zones monitored: {zone_count}
- Zones in CRITICAL (>=80): {critical_count} | Zones in HIGH (>=60): {high_count} | Zones ELEVATED (>=30): {elevated_count}

Most critical zone: {worst_zone} (score {worst_score}/100)
- Temperature: {temp}°C | Smoke/Gas: {smoke} PPM | Humidity: {humidity}% | Path blocked: {blocked}
- CHRONOS risk reasons: {reasons}

All elevated zone details:
{zone_details}

- Rover status: {rover_status} (target: {rover_target}, position: {rover_pos})
- UI Layout: {layout_mode} | Focused Zone: {focused_zone}

Generate the analysis and actions JSON. Include specific recommendations for EACH elevated zone."""


class AiService(BaseService):
    """
    Central AI Orchestrator coordinating specialized modular AI engines with a 4-tier AI cascade:
      Tier 1: Google Gemini (Gemini 3.1 Flash Lite)
      Tier 2: Groq Cloud (Llama 3.3 70B ultra-fast)
      Tier 3: OpenRouter API (Multi-model routing)
      Tier 4: Local Modular AI Engine (100% Offline, zero downtime)
    """
    def __init__(self, config: dict = None):
        super().__init__("AiService", config)
        self._executor = None
        self._lock = threading.Lock()
        self._pending: Optional[Future] = None
        self._gemini_key: str = ""
        self._groq_key: str = ""
        self._openrouter_key: str = ""
        self.websocket_broadcast_callback = None

        # Modular Engines
        self.hazard_engine = HazardDetectionEngine()
        self.decision_engine = DecisionEngine()
        self.mission_intel = MissionIntelligenceEngine()
        self.incident_engine = IncidentEngine()
        self.predictive_engine = PredictiveAnalysisEngine()
        self.nav_intel = NavigationIntelligenceEngine()
        self.recommendation_engine = RecommendationEngine()
        self.report_generator = MissionReportGenerator()
        self.analytics_engine = AnalyticsAIEngine()

        # Cache for live explanations
        self.latest_decision_explanations: List[dict] = []
        self.latest_predictive_insights: List[dict] = []

    def _on_start(self) -> bool:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='AiService')
        
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        if cfg_srv:
            self._gemini_key = cfg_srv.get_env_var("GEMINI_API_KEY", "").strip()
            self._groq_key = cfg_srv.get_env_var("GROQ_API_KEY", "").strip()
            self._openrouter_key = cfg_srv.get_env_var("OPENROUTER_API_KEY", "").strip()
        
        if not self._gemini_key:
            self._gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not self._groq_key:
            self._groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if not self._openrouter_key:
            self._openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()

        self.logger.info(f"AiService initialized (Gemini={'YES' if self._gemini_key else 'NO'}, Groq={'YES' if self._groq_key else 'NO'}, OpenRouter={'YES' if self._openrouter_key else 'NO'}).")
        return True

    def _on_stop(self) -> bool:
        if self._executor:
            self.logger.info("Stopping AiService thread pool executor...")
            self._executor.shutdown(wait=False)
            self._executor = None
        return True

    def set_gemini_key(self, gemini_key: str):
        with self._lock:
            self._gemini_key = gemini_key.strip()

    def set_groq_key(self, groq_key: str):
        with self._lock:
            self._groq_key = groq_key.strip()

    def set_openrouter_key(self, openrouter_key: str):
        with self._lock:
            self._openrouter_key = openrouter_key.strip()

    def request_update(self, snapshot: dict):
        """Dispatches AI generation task in a background thread."""
        if not self.is_running:
            self.logger.warning("Cannot request AI update: AiService is not running.")
            return

        with self._lock:
            if self._pending and not self._pending.done():
                return  # Skip if already running
            app_state.set_ai_thinking(True)
            self._pending = self._executor.submit(self._run_agent_cycle, snapshot)

    def _build_prompt(self, snapshot: dict) -> str:
        risk_scores = snapshot.get('risk_scores', {})
        zones = snapshot.get('zones', {})

        if risk_scores:
            valid_keys = [z for z in risk_scores if 'score' in risk_scores[z]]
            if valid_keys:
                worst_id = max(valid_keys, key=lambda z: risk_scores[z]['score'])
                worst = risk_scores[worst_id]
                worst_score = worst['score']
                reasons = '; '.join(worst.get('reasons', []))
                worst_name = ZONE_CONFIG.get(worst_id, {}).get('name', worst_id)
                worst_zone_data = zones.get(worst_id, {})
            else:
                worst_name, worst_score, reasons, worst_zone_data = 'N/A', 0, 'None', {}
        else:
            worst_name, worst_score, reasons, worst_zone_data = 'N/A', 0, 'None', {}

        zone_detail_lines = []
        critical_count = 0
        high_count = 0
        elevated_count = 0
        for zid, r in sorted(risk_scores.items(), key=lambda x: x[1].get('score', 0), reverse=True):
            score = r.get('score', 0)
            if score >= 80:
                critical_count += 1
            if score >= 60:
                high_count += 1
            if score >= 30:
                elevated_count += 1
                zname = ZONE_CONFIG.get(zid, {}).get('name', zid)
                zdata = zones.get(zid, {})
                z_reasons = '; '.join(r.get('reasons', [])[:2])
                zone_detail_lines.append(
                    f"  • {zname}: score {score}/100, temp {zdata.get('temp', 0) or 0:.1f}°C, "
                    f"smoke {zdata.get('smoke', 0) or 0} PPM, humidity {zdata.get('humidity', 60) or 60:.0f}%, "
                    f"blocked={zdata.get('blocked', False)}. Reasons: {z_reasons}"
                )

        zone_details = '\n'.join(zone_detail_lines) if zone_detail_lines else 'No elevated zones.'
        rover = snapshot.get('rover', {})
        position = rover.get('position', (0,0))
        rover_pos_str = f"({position[0]}, {position[1]})"

        return _USER_PROMPT_TEMPLATE.format(
            overall_risk=snapshot.get('overall_risk', 0),
            system_status=str(snapshot.get('system_status', 'green')).upper(),
            zone_count=len(zones),
            critical_count=critical_count,
            high_count=high_count,
            elevated_count=elevated_count,
            worst_zone=worst_name,
            worst_score=worst_score,
            temp=f"{worst_zone_data.get('temp', 0) or 0:.1f}",
            smoke=worst_zone_data.get('smoke', 0) or 0,
            humidity=f"{worst_zone_data.get('humidity', 60) or 60:.0f}",
            blocked=worst_zone_data.get('blocked', False),
            reasons=reasons or 'All normal',
            zone_details=zone_details,
            rover_status=rover.get('status', 'idle'),
            rover_target=rover.get('target_zone') or 'None',
            rover_pos=rover_pos_str,
            layout_mode=snapshot.get('layout_mode', 'standard'),
            focused_zone=snapshot.get('focused_zone') or 'None'
        )

    def _query_gemini(self, system_prompt: str, user_prompt: str, mime_type: str = "text/plain") -> Optional[str]:
        with self._lock:
            api_key = self._gemini_key
        if not api_key:
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 512,
                "responseMimeType": mime_type
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            self.logger.warning(f"Gemini query call failed: {e}")
            return None

    def _query_groq(self, system_prompt: str, user_prompt: str, mime_type: str = "text/plain") -> Optional[str]:
        with self._lock:
            api_key = self._groq_key
        if not api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 512
        }
        if mime_type == "application/json":
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            self.logger.warning(f"Groq query call failed: {e}")
            return None

    def _query_openrouter(self, system_prompt: str, user_prompt: str, mime_type: str = "text/plain") -> Optional[str]:
        with self._lock:
            api_key = self._openrouter_key
        if not api_key:
            return None

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sentineltwin.org",
            "X-Title": "Sentinel Twin X"
        }
        payload = {
            "model": "google/gemma-2-9b-it:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 512
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            self.logger.warning(f"OpenRouter query call failed: {e}")
            return None

    def _parse_json(self, text: str) -> Optional[dict]:
        try:
            text = text.strip()
            if text.startswith('```'):
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            return json.loads(text)
        except Exception as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            return None

    def _run_agent_cycle(self, snapshot: dict):
        try:
            # 1. Run Modular AI Engines
            hazards = self.hazard_engine.analyze_snapshot(snapshot)
            predictive_insights = self.predictive_engine.analyze_system_trends(snapshot)
            decision_explanations = self.decision_engine.evaluate_actions(snapshot, hazards)
            recommendations = self.recommendation_engine.generate_recommendations(snapshot, hazards, predictive_insights)

            with self._lock:
                self.latest_decision_explanations = [d.to_dict() for d in decision_explanations]
                self.latest_predictive_insights = [p.to_dict() for p in predictive_insights]

            prompt = self._build_prompt(snapshot)
            
            with self._lock:
                gemini_key = self._gemini_key
                groq_key = self._groq_key
                openrouter_key = self._openrouter_key

            response_dict = None
            tier = 'local_fallback'
            tier_label = '💻 Local fallback'

            # Tier 1: Try Gemini Cloud AI
            if gemini_key:
                try:
                    text = self._query_gemini(_SYSTEM_PROMPT, prompt, "application/json")
                    if text:
                        response_dict = self._parse_json(text)
                        if response_dict:
                            tier = 'cloud_gemini'
                            tier_label = '☁️ Cloud (Gemini)'
                except Exception as e:
                    self.logger.warning(f"Gemini call failed: {e}")

            # Tier 2: Try Groq Ultra-Fast AI (Llama 3.3 70B)
            if response_dict is None and groq_key:
                try:
                    text = self._query_groq(_SYSTEM_PROMPT, prompt, "application/json")
                    if text:
                        response_dict = self._parse_json(text)
                        if response_dict:
                            tier = 'cloud_groq'
                            tier_label = '⚡ Cloud (Groq Llama 3.3 70B)'
                except Exception as e:
                    self.logger.warning(f"Groq call failed: {e}")

            # Tier 3: Try OpenRouter AI
            if response_dict is None and openrouter_key:
                try:
                    text = self._query_openrouter(_SYSTEM_PROMPT, prompt, "application/json")
                    if text:
                        response_dict = self._parse_json(text)
                        if response_dict:
                            tier = 'cloud_openrouter'
                            tier_label = '🌐 Cloud (OpenRouter)'
                except Exception as e:
                    self.logger.warning(f"OpenRouter call failed: {e}")

            # Tier 4: Fallback to Local Modular AI Engine (100% Offline)
            if response_dict is None:
                report_fallback = template_report(snapshot)
                proposed_acts = [
                    {'action': de.action_name, 'params': de.params}
                    for de in decision_explanations
                ]
                reasoning_str = "; ".join(
                    [r for de in decision_explanations for r in de.reasons[:1]]
                ) or "System nominal. Continuous surveillance active."

                response_dict = {
                    'summary': report_fallback.summary,
                    'analysis': report_fallback.analysis,
                    'severity': report_fallback.severity,
                    'confidence': report_fallback.confidence,
                    'recommendations': recommendations,
                    'reasoning': reasoning_str,
                    'actions': proposed_acts
                }
                tier = 'local_fallback'
                tier_label = '💻 Local fallback'

            # Update report on state
            report = AIReport(
                summary=response_dict.get('summary', 'No summary available.'),
                analysis=response_dict.get('analysis', 'No analysis available.'),
                severity=response_dict.get('severity', 'UNKNOWN'),
                confidence=response_dict.get('confidence', 'N/A'),
                recommendations=response_dict.get('recommendations', recommendations),
                tier=tier,
                tier_label=tier_label
            )
            app_state.update_ai_report(report)

            # Sync AI Report to Convex
            from server.services import registry
            convex_srv = registry.get("ConvexService")
            if convex_srv:
                convex_srv.sync_ai_report(
                    summary=report.summary,
                    analysis=report.analysis,
                    severity=report.severity,
                    confidence=report.confidence,
                    recommendations_json=json.dumps(report.recommendations)
                )

            # Process proposed actions
            proposed_actions = response_dict.get('actions', [])
            reasoning = response_dict.get('reasoning', '')

            # Clear out duplicate pending actions first to prevent UI flooding
            with app_state._lock:
                app_state.pending_actions.clear()

            for act_obj in proposed_actions:
                action = act_obj.get('action')
                params = act_obj.get('params', {})
                if 'reason' not in params and reasoning:
                    params['reason'] = reasoning

                # Verify against safety schema
                is_valid, err = validate_action(action, params)
                if not is_valid:
                    self.logger.warning(f"AI proposed invalid action '{action}': {err}")
                    continue

                # Check policy: auto-run vs. request approval
                duplicate = False
                for pending in app_state.pending_actions:
                    if pending.action == action and pending.params == params:
                        duplicate = True
                        break
                if duplicate:
                    continue

                if action_needs_approval(action, params):
                    app_state.add_pending_action(action, params, params.get('reason', reasoning))
                    self.logger.info(f"Gated critical action: {action}")
                else:
                    execute_action(action, params, source="AI (Auto)")

        except Exception as e:
            self.logger.error(f"Error in agent background loop: {e}", exc_info=True)
        finally:
            app_state.set_ai_thinking(False)
            if self.websocket_broadcast_callback:
                self.websocket_broadcast_callback()

    def generate_chat_response(self, query: str) -> str:
        snapshot = app_state.get_snapshot()
        context_str = json.dumps(snapshot, indent=2)
        
        system_prompt = (
            "You are SENTINEL AI, the emergency safety copilot. "
            "You have access to the building's live digital twin sensor telemetry context. "
            "Your job is to answer the operator's query accurately using ONLY the provided telemetry data. "
            "Never hallucinate sensor values or state. If a zone is safe, confirm it. "
            "If there is an active hazard, explain it clearly and suggest safety recommendations. "
            "Keep your response concise (max 100 words), professional, and direct."
        )
        
        user_prompt = f"Live Telemetry Context:\n{context_str}\n\nOperator Query: {query}"
        
        # 1. Try Gemini
        response = self._query_gemini(system_prompt, user_prompt, "text/plain")
        if response:
            return response

        # 2. Try Groq
        response = self._query_groq(system_prompt, user_prompt, "text/plain")
        if response:
            return response

        # 3. Try OpenRouter
        response = self._query_openrouter(system_prompt, user_prompt, "text/plain")
        if response:
            return response
            
        # 4. Local Fallback
        return self._generate_local_chat_fallback(query, snapshot)

    def _generate_local_chat_fallback(self, query: str, snapshot: dict) -> str:
        q = query.lower()
        zones = snapshot.get('zones', {})
        risk_scores = snapshot.get('risk_scores', {})
        rover = snapshot.get('rover', {})

        for zone_id, zdata in zones.items():
            name = ZONE_CONFIG.get(zone_id, {}).get('name', zone_id).lower()
            is_match = False
            matched_name = ZONE_CONFIG.get(zone_id, {}).get('name', zone_id)
            
            if name in q or zone_id in q:
                is_match = True
            elif zone_id == "classroom_1" and ("classroom a" in q or "classroom_a" in q):
                is_match = True
                matched_name = "Classroom A"
            elif zone_id == "classroom_2" and ("classroom b" in q or "classroom_b" in q):
                is_match = True
                matched_name = "Classroom B"
                
            if is_match:
                score = risk_scores.get(zone_id, {}).get('score', 0)
                status = "SAFE" if score < 30 else "ELEVATED RISK" if score < 60 else "CRITICAL RISK"
                reasons = ", ".join(risk_scores.get(zone_id, {}).get('reasons', []))
                reason_str = f" due to {reasons}" if reasons else ""
                return (
                    f"Local fallback report for {matched_name}: Status is {status} (score {score}/100) "
                    f"with temp {zdata.get('temp')}°C, smoke {zdata.get('smoke')} PPM, and humidity {zdata.get('humidity')}%.{reason_str}"
                )

        if 'rover' in q or 'status' in q:
            return (
                f"Rover status is '{rover.get('status')}' located in zone '{rover.get('current_zone')}'. "
                f"Battery level is {rover.get('battery_pct')}%. Target zone is '{rover.get('target_zone')}'."
            )

        if 'exit' in q or 'route' in q:
            from server.services import registry
            alert_srv = registry.get("AlertService")
            if alert_srv:
                recs = alert_srv.get_all_evac_recommendations(risk_scores, zones)
                routes = []
                for zid, r in recs.items():
                    if r.get('path'):
                        routes.append(f"{ZONE_CONFIG.get(zid, {}).get('name', zid)} -> {r.get('exit_name')}")
                return "Egress routing recommendations: " + "; ".join(routes[:3])

        return (
            f"All Systems Summary: Overall building status is {snapshot.get('system_status').upper()} "
            f"with risk index {snapshot.get('overall_risk')}/100."
        )

    def get_explanations(self) -> List[dict]:
        with self._lock:
            return self.latest_decision_explanations

    def get_insights(self) -> List[dict]:
        with self._lock:
            return self.latest_predictive_insights
