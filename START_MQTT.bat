@echo off
title Sentinel Twin v2 — SyncHack 2026 (MQTT Mode)
color 0B
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   SENTINEL TWIN v2  —  SyncHack 2026        ║
echo  ║   AI + IoT Emergency Intelligence System    ║
echo  ║   MQTT Live Mode (Raspberry Pi Broker)      ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  [1] Starting server in MQTT mode...
echo  [2] Connecting to broker at 10.10.0.213...
echo  [3] Dashboard will open at http://localhost:8000/
echo.
cd /d "%~dp0"
py run.py --mqtt
pause
