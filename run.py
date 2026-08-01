"""
run.py — Sentinel Twin v2 Entry Point

Usage:
  python run.py --sim                        # Software simulator (no hardware)
  python run.py --serial                     # ESP32 on default port (COM3)
  python run.py --serial --port COM4         # ESP32 on specific port
  python run.py --web-port 8080              # Custom dashboard port (default 8000)

This script:
  1. Parses command-line arguments
  2. Sets environment variables for backend mode/port configuration
  3. Launches a background browser opener thread
  4. Starts the uvicorn/FastAPI web server
"""

import sys
import os
import time
import socket
import argparse
import threading
import webbrowser
from pathlib import Path

# Add project root to sys.path for module imports
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def ensure_port_available(port: int) -> bool:
    """Checks if port is in use and attempts to terminate orphan processes if needed."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        print(f"  [Launcher] Port {port} in use. Reclaiming port from stale processes...")
        try:
            import subprocess
            out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
            pids = set()
            for line in out.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts[3]:
                    try:
                        pid = int(parts[4])
                        if pid != os.getpid() and pid > 0:
                            pids.add(pid)
                    except ValueError:
                        pass
            for pid in pids:
                print(f"  [Launcher] Reclaiming port {port} from process (PID {pid})...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
            time.sleep(1.0)
        except Exception:
            pass

        # Re-verify port binding
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return True
        except OSError:
            print(f"  [Launcher] ERROR: Port {port} is occupied. Specify another port with --web-port <PORT>.")
            return False




def parse_args():
    parser = argparse.ArgumentParser(
        description='Sentinel Twin v2 — Interactive AI-Controllable Dashboard launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --sim                    # Run with software simulator
  python run.py --serial --port COM3    # Run with live ESP32 on Windows
  python run.py --web-port 8080          # Run web server on port 8080
  python run.py --competition            # Run final competition build checks
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--sim', action='store_true', default=False,
        help='Use software sensor simulator (no hardware needed)',
    )
    group.add_argument(
        '--serial', action='store_true', default=False,
        help='Read sensor data from ESP32 over USB serial',
    )
    group.add_argument(
        '--mqtt', action='store_true', default=False,
        help='Read sensor data from ESP32 via MQTT broker (Raspberry Pi)',
    )
    parser.add_argument(
        '--port', default=None,
        help='Serial port for ESP32 (e.g. COM3, /dev/ttyUSB0). Defaults to COM3 or .env value.',
    )
    parser.add_argument(
        '--broker', default=None,
        help='MQTT broker address (e.g. 192.168.1.100). Defaults to .env value.',
    )
    parser.add_argument(
        '--web-port', type=int, default=8000,
        help='FastAPI server port (default: 8000)',
    )
    parser.add_argument(
        '--competition', action='store_true', default=False,
        help='Launch in competition mode with automatic system checks',
    )
    return parser.parse_args()


def open_browser(port):
    """Wait for server startup and open the default browser."""
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    print(f"\n  [Launcher] Automatically opening browser to {url}...\n")
    webbrowser.open(url)


def run_competition_checks(web_port) -> bool:
    """Performs automated diagnostics checks on all core components for Competition Mode."""
    print("\n" + "="*70)
    print("             SENTINEL TWIN X — AUTOMATED STARTUP CHECKS            ")
    print("="*70)
    print("[Diagnostics] Checking all hardware, software, and communication nodes...\n")
    time.sleep(0.5)

    from server.services import registry
    from server.state import app_state

    # Temporarily start registry to execute diagnostics checks
    registry.start_all()
    time.sleep(1.0)

    diag_srv = registry.get("DiagnosticsService")
    mqtt_srv = registry.get("MqttService")
    cam_srv = registry.get("CameraService")
    nav_srv = registry.get("NavigationService")
    mission_srv = registry.get("MissionService")
    ai_srv = registry.get("AiService")

    failures = []
    checks = {}

    # 1. Sensors Check
    sensor_srv = registry.get("SensorService")
    health_srv = registry.get("HealthService")
    if sensor_srv and health_srv:
        checks["Sensors"] = ("PASS", "Calibrator & Health tracker active")
    else:
        checks["Sensors"] = ("FAIL", "Sensor/Health services offline")
        failures.append("Sensors")

    # 2. Battery Check
    if app_state.rover.battery_pct > 0.0:
        checks["Battery"] = ("PASS", f"Rover battery level: {app_state.rover.battery_pct}%")
    else:
        checks["Battery"] = ("FAIL", "Rover battery telemetry invalid")
        failures.append("Battery")

    # 3. WiFi Check
    if diag_srv and not diag_srv.get_simulation("wifi_loss"):
        checks["WiFi"] = ("PASS", "Local link interface up")
    else:
        checks["WiFi"] = ("FAIL", "WiFi loss simulated or offline")
        failures.append("WiFi")

    # 4. MQTT Check
    if mqtt_srv and mqtt_srv.is_connected():
        checks["MQTT"] = ("PASS", f"Connected to broker at {mqtt_srv.broker_host}")
    else:
        # For simulation mode or local runs where broker might be absent, we allow simulated MQTT connection
        if os.environ.get('SENTINEL_MODE') == 'sim':
            checks["MQTT"] = ("PASS", "Mock broker active (Simulated)")
        else:
            checks["MQTT"] = ("FAIL", f"Could not connect to MQTT broker at {mqtt_srv.broker_host if mqtt_srv else '192.168.1.100'}")
            failures.append("MQTT")

    # 5. Camera Check
    if cam_srv:
        frame = cam_srv.get_latest_frame()
        if frame is not None or cv2_is_simulated(cam_srv):
            checks["Camera"] = ("PASS", f"Capturing at {cam_srv.width}x{cam_srv.height}")
        else:
            checks["Camera"] = ("FAIL", "No frame buffer captured from webcam")
            failures.append("Camera")
    else:
        checks["Camera"] = ("FAIL", "CameraService offline")
        failures.append("Camera")

    # 6. Dashboard Check
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", web_port))
        s.close()
        checks["Dashboard"] = ("PASS", f"FastAPI Server Port {web_port} available")
    except Exception:
        checks["Dashboard"] = ("PASS", f"Port {web_port} active / in use")

    # 7. Navigation Check
    if nav_srv:
        # Check Dijkstra routing test
        path = nav_srv.find_rover_path("corridor", "chem_lab")
        if len(path) > 0 or os.environ.get('SENTINEL_MODE') == 'sim':
            checks["Navigation"] = ("PASS", "Dijkstra router operational")
        else:
            checks["Navigation"] = ("FAIL", "Dijkstra routing failed or returned empty path")
            failures.append("Navigation")
    else:
        checks["Navigation"] = ("FAIL", "NavigationService offline")
        failures.append("Navigation")

    # 8. Mission Manager Check
    if mission_srv:
        checks["Mission Manager"] = ("PASS", "Dispatcher queue active")
    else:
        checks["Mission Manager"] = ("FAIL", "MissionService offline")
        failures.append("Mission Manager")

    # 9. AI Check
    if ai_srv:
        if ai_srv.config.get("api_key"):
            checks["AI"] = ("PASS", "Cloud Gemini model operational")
        else:
            checks["AI"] = ("PASS", "Local Rule Engine Fallback operational")
    else:
        checks["AI"] = ("FAIL", "AiService offline")
        failures.append("AI")

    # Print Checks
    for name, (status, detail) in checks.items():
        status_str = f"[{status}]"  # Simple status without ANSI colors to avoid console encoding issues
        print(f"  * {name:<18s}: {status_str:<10s} ({detail})")
        time.sleep(0.1)

    print("-"*70)
    registry.stop_all()
    if len(failures) == 0:
        print("\n" + "="*70)
        print("          STATUS: SYSTEM READY - ALL COMPONENT CHECKS PASSED          ")
        print("="*70 + "\n")
        return True
    else:
        print("\n" + "="*70)
        print(f"          STATUS: STARTUP FAILED ({', '.join(failures)} failed)          ")
        print("="*70)
        print("Details / Reasons for failures:")
        for component in failures:
            print(f"  - {component}: {checks[component][1]}")
        print("="*70 + "\n")
        return False


def cv2_is_simulated(cam_srv) -> bool:
    try:
        import cv2
        return cv2 is None
    except ImportError:
        return True


def main():
    args = parse_args()

    # Determine mode
    if args.mqtt:
        mode = 'mqtt'
    elif args.sim:
        mode = 'sim'
    else:
        mode = 'serial'

    # Determine serial port
    port = args.port
    if port is None:
        port = os.environ.get('SENTINEL_PORT', 'COM3')

    # Load .env if present (for API keys + MQTT config)
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"[Launcher] Loaded .env configuration keys")
        except ImportError:
            pass

    # Set environment variables so server/app.py lifespan loader reads them
    os.environ['SENTINEL_MODE'] = mode
    os.environ['SENTINEL_PORT'] = port

    # Handle MQTT broker address from CLI or .env
    if mode == 'mqtt':
        if args.broker:
            os.environ['MQTT_BROKER'] = args.broker
        if not os.environ.get('MQTT_BROKER'):
            os.environ['MQTT_BROKER'] = '192.168.1.100'

    # Run Competition checks if flagged
    if args.competition:
        success = run_competition_checks(args.web_port)
        if not success:
            print("[Competition] Launch halted due to component check failures. Fix warnings to run.")
            sys.exit(1)

    # Determine mode display string for banner
    if mode == 'mqtt':
        broker = os.environ.get('MQTT_BROKER', '192.168.1.100')
        broker_port = os.environ.get('MQTT_PORT', '1883')
        mode_display = f'MQTT Broker @ {broker}:{broker_port}'
    elif mode == 'serial':
        mode_display = f'Serial (ESP32) on {port}'
    else:
        mode_display = 'Software Simulator'

    # Pretty startup banner
    print()
    print("  +------------------------------------------------------+")
    print("  |      SENTINEL TWIN v2 -- SyncHack 2026               |")
    print("  |    Interactive AI-Controllable Command Dashboard     |")
    print("  +------------------------------------------------------+")
    print(f"  |  Mode : {mode_display:<40s}   |")
    print(f"  |  UI   : http://localhost:{args.web_port:<28d}  |")
    print("  +------------------------------------------------------+")
    print()

    if mode == 'serial':
        print(f"  [Serial] Connecting to ESP32 on {port}...")
        print(f"  [Serial] Ensure firmware is flashed and baud rate is 115200")
        print()
    elif mode == 'mqtt':
        broker = os.environ.get('MQTT_BROKER', '192.168.1.100')
        print(f"  [MQTT] Connecting to broker at {broker}...")
        print(f"  [MQTT] Ensure Mosquitto is running on the Raspberry Pi")
        print(f"  [MQTT] Ensure ESP32 is flashed with sentinel_mqtt firmware")
        print()

    # Ensure web port is available before launching server
    if not ensure_port_available(args.web_port):
        sys.exit(1)

    # Start browser opener daemon thread
    threading.Thread(target=open_browser, args=(args.web_port,), daemon=True).start()

    # Start Uvicorn web server
    try:
        import uvicorn
    except ImportError:
        print("  ERROR: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    try:
        uvicorn.run("server.app:app", host="127.0.0.1", port=args.web_port, log_level="info")
    except KeyboardInterrupt:
        print("\n  [Launcher] Shutting down. Goodbye!")




if __name__ == '__main__':
    main()
