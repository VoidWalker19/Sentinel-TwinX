#!/bin/bash
# start_pi_camera.sh — Launch Raspberry Pi Camera Stream for Sentinel Twin
# Run this script on your Raspberry Pi:
#   chmod +x start_pi_camera.sh
#   ./start_pi_camera.sh

echo "=========================================================="
echo "      SENTINEL TWIN — RASPBERRY PI CAMERA STREAMER        "
echo "=========================================================="
echo "[Pi Camera] Installing dependencies if needed..."

pip install flask opencv-python-headless 2>/dev/null || pip install flask opencv-python

echo "[Pi Camera] Starting MJPEG stream server on port 5000..."
echo "[Pi Camera] Stream URL: http://$(hostname -I | awk '{print $1}'):5000/video_feed"

python3 deploy/webcam_stream.py
