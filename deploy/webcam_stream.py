"""
deploy/webcam_stream.py — Standalone Flask MJPEG Webcam Streaming Server

Use this script if you wish to run an independent webcam server on a Raspberry Pi
or secondary laptop at port 9001.

Usage:
  python deploy/webcam_stream.py
"""

import os
import time
import threading
import cv2
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# Initialize OpenCV camera at index 0 and thread lock
camera_lock = threading.Lock()
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def generate_frames():
    global camera
    while True:
        with camera_lock:
            if camera is None or not camera.isOpened():
                camera = cv2.VideoCapture(0)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                time.sleep(0.2)

            success, frame = camera.read()
            if not success:
                time.sleep(0.1)
                if camera is not None:
                    camera.release()
                    camera = None
                continue

            ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame_bytes +
            b'\r\n'
        )

@app.route('/video_feed')
@app.route('/api/video-feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Sentinel Twin — Standalone Webcam Stream</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        h1 { margin-bottom: 20px; font-size: 24px; color: #38bdf8; }
        .stream-container { border: 2px solid #0284c7; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        img { width: 640px; height: 480px; display: block; }
    </style>
</head>
<body>
    <h1>📹 Sentinel Twin — Live Webcam Feed</h1>
    <div class="stream-container">
        <img src="/video_feed" alt="Live Camera Stream">
    </div>
</body>
</html>
    ''')

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    print(f"📹 Starting Standalone MJPEG Webcam Server on http://0.0.0.0:{port}...")
    app.run(
        host='0.0.0.0',
        port=port,
        threaded=True
    )
