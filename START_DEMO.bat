@echo off
title Sentinel Twin v2 — SyncHack 2026
color 0A
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   SENTINEL TWIN v2  —  SyncHack 2026        ║
echo  ║   AI + IoT Emergency Intelligence System    ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  [1] Starting server in SIMULATOR mode...
echo  [2] Dashboard will open at http://localhost:8000/
echo.
cd /d "%~dp0"
py run.py --sim
pause
