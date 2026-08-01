# Sentinel Twin v2 — 90-Second Demo Script

> **For judges / live demo walk-through at SyncHack 2026**
> Target time: 90 seconds. Practice this 3× before presenting.

---

## Before You Start (Setup — do this before judges arrive)

1. `python run.py --sim` → confirm dashboard is live at localhost:8000
2. Open the browser in **fullscreen** (F11)
3. Confirm all 10 zones show green on the map
4. Have the sidebar open to show the demo buttons

---

## The 90-Second Script

### 0–5s — Opening hook
*Point to the map:*
> "This is Sentinel Twin — a self-aware digital twin that monitors every zone
> of this building in real time. It doesn't just detect emergencies — it
> investigates, verifies, and recommends evacuation routes automatically."

---

### 5–20s — Normal state
*Point to the zone cards:*
> "Right now, all 10 zones are green. Temperature, smoke, and humidity are
> all within normal ranges. The CHRONOS engine computes a risk score for
> each zone every 2 seconds."

*Point to prediction panel:*
> "This is the 'self-aware' part — it tracks trends and predicts 30 seconds
> ahead. It will warn us *before* a zone hits critical."

---

### 20–35s — Trigger Lab Fire
*Click **🔥 Simulate Lab Fire** button:*
> "I'm simulating a chemical fire in the lab. Watch the map."

*Point to Chemistry Lab as it turns red:*
> "Temperature spikes to 68°C, smoke hits 650 PPM — both fire signatures.
> CHRONOS scores it 95/100. The system status just went RED."

*Point to prediction:*
> "The prediction engine is already showing 'Risk rising → CRITICAL in ~8s'."

---

### 35–55s — Rover investigation
*Point to the cyan dot moving on the map:*
> "The rover has been automatically dispatched — no human trigger needed.
> It's navigating through the Corridor North hub toward the Chemistry Lab."

*When rover arrives (watch the rover panel):*
> "Arrived. Now running AI visual verification — it checks the camera
> image for fire signatures: brightness, red channels, contrast."

*Point to verification result:*
> "Verdict: **CONFIRMED** at 94% confidence. This is a real emergency.
> The system would not falsely evacuate 500 students without visual confirmation."

---

### 55–70s — Recommendation + Voice
*Point to the status banner:*
> "The evacuation message: 'Emergency in Chemistry Lab. Evacuate via Exit B.
> Corridor North → Exit B.' This is spoken aloud automatically —
> hear the voice alert?"

*Point to incident timeline:*
> "Every step — detection, dispatch, arrival, verification, recommendation —
> is timestamped in the log. Exportable as CSV for incident review."

---

### 70–80s — "What if Wi-Fi dies?" (key resilience moment)
*Point to the AI tier pill in the header:*
> "Notice this pill — '☁️ Cloud (Gemini)' if I have internet.
> If I disconnect right now, it silently switches to '💻 Local fallback'
> — same fields, same format, zero downtime. The demo never breaks."

---

### 80–90s — Reset + closing
*Click **🔄 RESET ALL**:*
> "One click — everything returns to baseline. Fully repeatable for the next judge."

*Closing line:*
> "Sentinel Twin: real sensors, real risk scoring, real prediction,
> real rover, and real AI — all running right here, offline if needed.
> Detect → Analyze → Investigate → Verify → Recommend."

---

## Backup Lines (if asked to repeat or something goes slow)

- Rover taking longer than expected? Say: *"The rover is en route — this shows
  real travel time, not a jump-cut. Watch the ETA countdown."*
- AI pill shows Local? Say: *"This is the offline fallback — deliberately
  designed this way. You'll notice it reads identically to the cloud version."*
- Zone slow to turn red? Say: *"The ramp-up is intentionally gradual — real
  fires spread, they don't pop into existence. Great for showing the trend line."*

---

## Quick Reference — Button Effects

| Button | What changes |
|--------|-------------|
| 🔥 Lab Fire | Chem Lab temp→68°C, smoke→650 PPM, score→~95 |
| 💨 Corridor Smoke | Corridor smoke→420 PPM, spreads to classrooms |
| 🖥️ Server Overheat | Server room temp→55°C, smoke→180 PPM |
| 🚧 Block Main Exit | Exit A blocked flag → reroutes evacuation to Exit B |
| 🔄 RESET | All zones return to safe baseline |
