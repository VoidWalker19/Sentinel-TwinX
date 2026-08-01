# Sentinel Twin X — Demo and Presentation Modes Guide

This document describes how to leverage **Demo Mode** and **Presentation Mode** during judging, live audits, or team presentations.

---

## 1. Demo Mode

Demo Mode allows you to run the entire digital twin pipeline without any physical hardware attached. The software simulator runs in the background, feeding realistic mock telemetry, path obstructions, and battery discharge rates.

### How to Start
Run the launcher with the `--sim` flag:
```bash
python run.py --sim
```

### Scripted Walkthrough for Judges (30-Second Flow)
1. Open the dashboard (automatically launches at `http://localhost:8000`).
2. Navigate to **Mission Control** tab.
3. Click **🔥 Simulate Lab Fire** in the simulation controller panel.
4. **Observe**:
   - The chemistry lab zone turns **red** indicating a high-risk score computed by the CHRONOS engine.
   - The AI narrator synthesizes an incident description and recommends dispatch.
   - The rover transitions to `en_route` and visualizes its path dynamically on the digital twin map.
   - Once the rover arrives, CV person/motion/fire detection overlays verify the event status.
   - Occupants are recommended a safe evacuation route bypassing the chemistry lab corridor, computed via the Dijkstra pathfinder.

---

## 2. Presentation Mode

Presentation Mode optimizes the dashboard interface for projection, showing large-screen visualizations, interactive slide overlays, and fullscreen layouts.

### How to Enable
On the Dashboard's **Settings** tab:
1. Toggle **Presentation Mode Layout** to `Enabled`.
2. Under theme settings, select the **High-Contrast Dark Mode** palette.
3. Toggle **Text-to-Speech Voice Synthesis** to `On` so the AI evacuation directions are announced aloud through the room speakers.
4. Adjust the **Sensor Poll Rate** slider to `0.5 seconds` to show highly dynamic telemetry line charts.
