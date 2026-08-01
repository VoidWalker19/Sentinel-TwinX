"""
server/action_system.py — Sentinel Twin Action System

This module handles allow-listed JSON actions emitted by the AI agent or manual controls.
It validates the action schema, decides whether the action requires human approval based
on the current Autonomous Mode status, and executes authorized actions on the system state.
"""

import logging
from typing import Tuple
from server.state import app_state, TimelineEvent
from rover.rover_sim import rover_simulator
from engine.chronos import ZONE_CONFIG

logger = logging.getLogger(__name__)

# Allowlisted actions and their expected parameter keys
ALLOWED_ACTIONS = {
    'dispatch_rover': {'zone'},
    'recall_rover': set(),
    'set_zone_status': {'zone', 'status'},
    'set_alarm': {'status'},
    'tune_threshold': {'key', 'value'},
    'focus_ui': {'zone'},
    'set_layout': {'layout_mode'},
    'move_forward': set(),
    'move_backward': set(),
    'turn_left': set(),
    'turn_right': set(),
    'stop_rover': set()
}

CRITICAL_ACTIONS = {'dispatch_rover', 'set_zone_status', 'set_alarm'}
CRITICAL_SETTINGS = {'temp_threshold_red', 'smoke_threshold_red', 'blocked_threshold', 'rover_auto_dispatch_level'}


ZONE_NAME_MAP = {
    "chem lab": "chem_lab",
    "chemistry lab": "chem_lab",
    "cad lab": "cad_lab",
    "computer lab": "cad_lab",
    "kitchen": "kitchen",
    "pantry": "kitchen",
    "corridor": "corridor",
    "main corridor": "corridor",
    "hallway": "corridor",
    "classroom 1": "classroom_1",
    "class 1": "classroom_1",
    "atl lab": "atl_lab",
    "robotics lab": "atl_lab",
    "electronics lab": "atl_lab",
    "classroom 2": "classroom_2",
    "class 2": "classroom_2",
    "server": "atl_lab",
    "server room": "atl_lab",
}


def normalize_zone(zone_name: str) -> str:
    if not zone_name:
        return zone_name
    s = zone_name.strip().lower().replace("_", " ").replace("-", " ")
    return ZONE_NAME_MAP.get(s, zone_name)


def validate_action(action: str, params: dict) -> Tuple[bool, str]:
    """
    Validates if the action is allowlisted and parameters conform to expectations.
    Returns (is_valid, error_message).
    """
    if action not in ALLOWED_ACTIONS:
        return False, f"Unknown action: '{action}'"

    expected_keys = ALLOWED_ACTIONS[action]
    for key in expected_keys:
        if key not in params:
            return False, f"Action '{action}' requires parameter '{key}'"

    # Deep validate parameters
    if 'zone' in params:
        zone = params['zone']
        if isinstance(zone, str):
            normalized = normalize_zone(zone)
            if normalized in ZONE_CONFIG:
                params['zone'] = normalized
                zone = normalized
        if zone not in ZONE_CONFIG and zone is not None:
            return False, f"Invalid zone identifier: '{zone}'"

    if 'status' in params and action == 'set_zone_status':
        status = params['status']
        if status not in ['green', 'yellow', 'orange', 'red']:
            return False, f"Invalid risk status: '{status}'"

    if 'layout_mode' in params:
        mode = params['layout_mode']
        if mode not in ['standard', 'crisis', 'focus', 'rover']:
            return False, f"Invalid layout mode: '{mode}'"

    if 'key' in params:
        key = params['key']
        if key not in app_state.settings:
            return False, f"Invalid setting key: '{key}'"

    return True, ""


def action_needs_approval(action: str, params: dict) -> bool:
    """
    Determines if an action is safety-critical and requires human approval
    under the current state of autonomous mode.
    """
    # If autonomous mode is on, nothing needs approval
    if app_state.autonomous_mode:
        return False

    # Dispatch, status overrides, and alarms are critical
    if action in CRITICAL_ACTIONS:
        return True

    # Adjusting safety-critical thresholds is also critical
    if action == 'tune_threshold':
        key = params.get('key')
        if key in CRITICAL_SETTINGS:
            return True

    return False


def execute_action(action: str, params: dict, source: str) -> Tuple[bool, str]:
    """
    Executes the validated action on the system state, records the timeline event,
    and logs the action in the immutable audit log.
    Returns (success, message).
    """
    is_valid, err = validate_action(action, params)
    if not is_valid:
        app_state.log_audit(action, params, source, f"Rejected: {err}", "Failed")
        logger.warning(f"[ActionSystem] Rejected {action} from {source}: {err}")
        return False, err

    reason = params.get('reason', 'No rationale provided')
    logger.info(f"[ActionSystem] Executing {action} from {source}. Reason: {reason}")

    try:
        if action == 'dispatch_rover':
            zone = params['zone']
            rover_simulator.force_dispatch(zone)
            app_state.update_layout('focus', focused_zone=zone)
            msg = f"Dispatched rover to {ZONE_CONFIG[zone]['name']}"

        elif action == 'recall_rover':
            rover_simulator.recall()
            app_state.update_layout('standard')
            msg = "Recalled rover to home base"

        elif action == 'move_forward':
            msg = "Sent FORWARD command to rover"
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                mqtt_srv.publish_command("rover", "forward")

        elif action == 'move_backward':
            msg = "Sent BACKWARD command to rover"
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                mqtt_srv.publish_command("rover", "backward")

        elif action == 'turn_left':
            msg = "Sent LEFT command to rover"
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                mqtt_srv.publish_command("rover", "left")

        elif action == 'turn_right':
            msg = "Sent RIGHT command to rover"
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                mqtt_srv.publish_command("rover", "right")

        elif action == 'stop_rover':
            msg = "Sent STOP command to rover"
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                mqtt_srv.publish_command("rover", "stop")

        elif action == 'set_zone_status':
            zone = params['zone']
            status = params['status']
            # We bypass the normal chronos rule logic for this zone by setting an override
            # In server/scheduler.py, we will check if there is an active zone override
            if 'overrides' not in app_state.settings:
                app_state.settings['overrides'] = {}
            
            with app_state._lock:
                app_state.settings['overrides'][zone] = status
            
            # Immediately add timeline event
            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description=f"⚠️ Zone {ZONE_CONFIG[zone]['name']} status overridden to {status.upper()} by {source}",
                severity='critical' if status in ['orange', 'red'] else 'info',
                zone_id=zone
            ))
            msg = f"Overrode zone {zone} status to {status.upper()}"

        elif action == 'set_alarm':
            status = params['status']
            app_state.alert_active = bool(status)
            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description=f"🚨 Alarm system manually {'ACTIVATED' if status else 'SILENCED'} by {source}",
                severity='critical' if status else 'info'
            ))
            msg = f"Alarm system {'activated' if status else 'silenced'}"

        elif action == 'tune_threshold':
            key = params['key']
            val = params['value']
            old_val = app_state.settings[key]
            app_state.update_settings(key, val)
            
            app_state.add_timeline_event(TimelineEvent(
                event_type='reset',
                description=f"⚙️ Setting '{key}' tuned from {old_val} to {val}",
                severity='info'
            ))
            msg = f"Tuned setting '{key}' to {val}"

        elif action == 'focus_ui':
            zone = params['zone']
            app_state.update_layout(app_state.layout_mode, focused_zone=zone)
            msg = f"Focused UI display on zone: {ZONE_CONFIG[zone]['name'] if zone else 'None'}"

        elif action == 'set_layout':
            mode = params['layout_mode']
            app_state.update_layout(mode, focused_zone=app_state.focused_zone)
            msg = f"Switched dashboard layout to {mode.upper()}"

        else:
            raise NotImplementedError(f"Action '{action}' validation passed but execution not defined")

        # Success! Log to audit log
        app_state.log_audit(action, params, source, reason, "Executed")

        try:
            from server.services import registry
            mqtt_srv = registry.get("MqttService")
            if mqtt_srv and mqtt_srv.is_connected():
                if action == 'set_alarm':
                    # Tell ALL known zones to activate/deactivate buzzer
                    for zone_id in ZONE_CONFIG:
                        status = params.get('status', False)
                        mqtt_srv.publish_command(zone_id, "buzzer_on" if status else "buzzer_off")

                elif action == 'dispatch_rover':
                    # Notify the target zone's ESP32 that a rover is coming
                    zone = params.get('zone')
                    if zone:
                        mqtt_srv.publish_command(zone, "rover_dispatched", {"zone": zone})
        except Exception as e:
            logger.debug(f"[ActionSystem] MQTT forward skipped: {e}")

        return True, msg

    except Exception as e:
        err_msg = f"Execution error: {str(e)}"
        logger.error(f"[ActionSystem] Failed executing {action}: {err_msg}")
        app_state.log_audit(action, params, source, f"Failed: {err_msg} (Reason: {reason})", "Failed")
        return False, err_msg
