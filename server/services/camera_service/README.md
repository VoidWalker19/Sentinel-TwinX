# Camera Service

Acquires images from local USB Webcams in a background thread to prevent latency.

## Configuration
- `camera_index`: System device identifier index (default: `0`).
- `frame_rate`: Capture speed in FPS (default: `5.0`).
- `width`: Resolution horizontal pixel width (default: `640`).
- `height`: Resolution vertical pixel height (default: `480`).

## Errors Handled
- OpenCV missing or Webcam offline: Rather than raising tracebacks or halting server boot, the service automatically initiates a simulated colored test pattern.
