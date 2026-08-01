import math
import time
import logging
from collections import deque
from typing import Dict, Optional, List, Tuple
from server.services.base_service import BaseService
from server.state import ZoneReading, PredictionResult

# --- Constants for Calibrator ---
CALIBRATION_WINDOW = 20
MIN_READINGS = 5
K_YELLOW = 2.0
K_RED = 4.0

MAX_TEMP_YELLOW = 45.0
MAX_TEMP_RED = 65.0
MAX_SMOKE_YELLOW = 200
MAX_SMOKE_RED = 600

MIN_TEMP_YELLOW = 30.0
MIN_TEMP_RED = 40.0
MIN_SMOKE_YELLOW = 50
MIN_SMOKE_RED = 150

# --- Constants for Predictor ---
HISTORY_SIZE = 30
SLOPE_STABLE_THRESHOLD = 0.05
LOOKAHEAD_SECONDS = 30
SCORE_RED = 80

RISK_BANDS = [
    (15,  'Safe',     'All readings within normal parameters. No action required.', 'green'),
    (30,  'Caution',  'Minor elevation detected. Continue routine monitoring.', 'teal'),
    (50,  'Warning',  'Moderate hazard indicators present. Increased monitoring advised.', 'yellow'),
    (70,  'Danger',   'Significant hazard detected. Active investigation required.', 'orange'),
    (100, 'Critical', 'Severe hazard confirmed. Immediate evacuation and emergency response required.', 'red'),
]

RECOMMENDATIONS = {
    ('Safe',     'stable'):  'No action needed. System operating normally.',
    ('Safe',     'rising'):  'Monitor — slight upward trend from baseline.',
    ('Safe',     'falling'): 'Conditions improving. No action needed.',
    ('Caution',  'stable'):  'Continue monitoring. Review sensor readings periodically.',
    ('Caution',  'rising'):  'Increasing trend detected. Prepare for possible escalation.',
    ('Caution',  'falling'): 'Conditions stabilizing. Continue observation.',
    ('Warning',  'stable'):  'Sustained warning levels. Consider visual inspection of the area.',
    ('Warning',  'rising'):  'Escalating hazard. Dispatch rover for automated investigation.',
    ('Warning',  'falling'): 'Hazard decreasing. Maintain monitoring until fully cleared.',
    ('Danger',   'stable'):  'Danger zone sustained. Rover investigation and staff alert recommended.',
    ('Danger',   'rising'):  'URGENT: Rapidly escalating danger. Initiate evacuation preparations.',
    ('Danger',   'falling'): 'Danger decreasing. Continue monitoring — do not cancel alerts prematurely.',
    ('Critical', 'stable'):  'CRITICAL: Sustained emergency. Execute full evacuation protocol NOW.',
    ('Critical', 'rising'):  'CRITICAL ESCALATION: Maximum emergency response. All personnel evacuate.',
    ('Critical', 'falling'): 'Critical conditions easing. Maintain evacuation until fully clear.',
}

class ZoneCalibration:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self._temp_history = deque(maxlen=CALIBRATION_WINDOW)
        self._smoke_history = deque(maxlen=CALIBRATION_WINDOW)
        self._humidity_history = deque(maxlen=CALIBRATION_WINDOW)

        self.temp_mean = None
        self.temp_std = None
        self.smoke_mean = None
        self.smoke_std = None
        self.humidity_mean = None
        self.humidity_std = None

        self.temp_threshold_yellow = None
        self.temp_threshold_red = None
        self.smoke_threshold_yellow = None
        self.smoke_threshold_red = None

    @property
    def status(self) -> str:
        count = len(self._temp_history)
        if count < MIN_READINGS:
            return 'pending'
        elif count < CALIBRATION_WINDOW:
            return 'calibrating'
        else:
            return 'calibrated'

    @property
    def progress(self) -> float:
        return min(1.0, len(self._temp_history) / CALIBRATION_WINDOW)

    def feed(self, reading: ZoneReading):
        if reading.temp is not None:
            self._temp_history.append(reading.temp)
        if reading.smoke is not None:
            self._smoke_history.append(reading.smoke)
        if reading.humidity is not None:
            self._humidity_history.append(reading.humidity)

        if len(self._temp_history) >= MIN_READINGS:
            self._recompute()

    def _recompute(self):
        self.temp_mean = self._calc_mean(self._temp_history)
        self.temp_std = self._calc_std(self._temp_history, self.temp_mean)

        self.smoke_mean = self._calc_mean(self._smoke_history)
        self.smoke_std = self._calc_std(self._smoke_history, self.smoke_mean)

        self.humidity_mean = self._calc_mean(self._humidity_history)
        self.humidity_std = self._calc_std(self._humidity_history, self.humidity_mean)

        t_std = max(1.0, self.temp_std)
        s_std = max(5.0, self.smoke_std)

        self.temp_threshold_yellow = self._clamp(
            self.temp_mean + K_YELLOW * t_std, MIN_TEMP_YELLOW, MAX_TEMP_YELLOW
        )
        self.temp_threshold_red = self._clamp(
            self.temp_mean + K_RED * t_std, MIN_TEMP_RED, MAX_TEMP_RED
        )
        self.smoke_threshold_yellow = int(self._clamp(
            self.smoke_mean + K_YELLOW * s_std, MIN_SMOKE_YELLOW, MAX_SMOKE_YELLOW
        ))
        self.smoke_threshold_red = int(self._clamp(
            self.smoke_mean + K_RED * s_std, MIN_SMOKE_RED, MAX_SMOKE_RED
        ))

    def _calc_mean(self, data) -> float:
        return sum(data) / len(data) if data else 0.0

    def _calc_std(self, data, mean_val: float) -> float:
        n = len(data)
        if n < 2:
            return 0.0
        variance = sum((x - mean_val) ** 2 for x in data) / n
        return math.sqrt(variance)

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def get_thresholds(self) -> Optional[dict]:
        if self.temp_threshold_yellow is None:
            return None
        return {
            'temp_yellow': round(self.temp_threshold_yellow, 1),
            'temp_red': round(self.temp_threshold_red, 1),
            'smoke_yellow': self.smoke_threshold_yellow,
            'smoke_red': self.smoke_threshold_red,
        }

    def to_dict(self) -> dict:
        thresholds = self.get_thresholds()
        return {
            'zone_id': self.zone_id,
            'status': self.status,
            'progress': round(self.progress, 2),
            'baseline': {
                'temp_mean': round(self.temp_mean, 1) if self.temp_mean is not None else None,
                'smoke_mean': round(self.smoke_mean, 1) if self.smoke_mean is not None else None,
                'humidity_mean': round(self.humidity_mean, 1) if self.humidity_mean is not None else None,
            },
            'thresholds': thresholds,
        }

class ZoneHistory:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self._history = deque(maxlen=HISTORY_SIZE)

    def add(self, score: int):
        self._history.append((time.time(), score))

    def compute(self) -> PredictionResult:
        data = list(self._history)
        current_score = data[-1][1]
        data_count = len(data)

        # Get risk band
        band_name = 'Safe'
        band_detail = ''
        for max_score, name, detail, _ in RISK_BANDS:
            if current_score <= max_score:
                band_name = name
                band_detail = detail
                break
        risk_band_detail = f"Score {current_score}/100 — {band_name} zone. {band_detail}"

        if data_count < 5:
            rec = RECOMMENDATIONS.get((band_name, 'stable'), 'Monitor.')
            return PredictionResult(
                zone_id=self.zone_id, trend='stable', slope=0.0, projected_score_30s=current_score,
                projected_critical_in=None, current_score=current_score, risk_band=band_name,
                risk_band_detail=risk_band_detail, trend_description='Insufficient data.',
                confidence='low', recommendation=rec
            )

        # Fit simple linear regression without numpy to keep service light
        x = [d[0] - data[0][0] for d in data]
        y = [d[1] for d in data]
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xx = sum(xi * xi for xi in x)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        
        denom = (n * sum_xx - sum_x * sum_x)
        slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0.0

        projected_30 = int(max(0, min(100, current_score + slope * LOOKAHEAD_SECONDS)))

        if slope > SLOPE_STABLE_THRESHOLD:
            trend = 'rising'
        elif slope < -SLOPE_STABLE_THRESHOLD:
            trend = 'falling'
        else:
            trend = 'stable'

        projected_critical_in = None
        if slope > SLOPE_STABLE_THRESHOLD and current_score < SCORE_RED:
            sec = (SCORE_RED - current_score) / slope
            if 0 < sec <= 300:
                projected_critical_in = int(sec)

        rec = RECOMMENDATIONS.get((band_name, trend), 'Monitor.')
        trend_desc = f"{'⬆️' if trend=='rising' else '⬇️' if trend=='falling' else '➡️'} {trend.capitalize()} trend."

        return PredictionResult(
            zone_id=self.zone_id, trend=trend, slope=slope, projected_score_30s=projected_30,
            projected_critical_in=projected_critical_in, current_score=current_score, risk_band=band_name,
            risk_band_detail=risk_band_detail, trend_description=trend_desc,
            confidence='medium', recommendation=rec
        )

class SensorService(BaseService):
    """
    Sensor Service that manages dynamic zone calibration baselines and linear regression forecasting.
    """
    def __init__(self, config: dict = None):
        super().__init__("SensorService", config)
        self._calibrators: Dict[str, ZoneCalibration] = {}
        self._histories: Dict[str, ZoneHistory] = {}

    def _on_start(self) -> bool:
        self.logger.info("Sensor service initialized.")
        return True

    def process_reading(self, reading: ZoneReading):
        zone_id = reading.zone_id
        if zone_id not in self._calibrators:
            self._calibrators[zone_id] = ZoneCalibration(zone_id)
        if zone_id not in self._histories:
            self._histories[zone_id] = ZoneHistory(zone_id)

        self._calibrators[zone_id].feed(reading)

    def get_thresholds(self, zone_id: str) -> Optional[dict]:
        cal = self._calibrators.get(zone_id)
        return cal.get_thresholds() if cal else None

    def get_all_calibration_status(self) -> Dict[str, dict]:
        return {zid: cal.to_dict() for zid, cal in self._calibrators.items()}

    def update_risk_trend(self, zone_id: str, current_risk: int) -> Optional[PredictionResult]:
        if zone_id not in self._histories:
            self._histories[zone_id] = ZoneHistory(zone_id)
        self._histories[zone_id].add(current_risk)
        return self._histories[zone_id].compute()
