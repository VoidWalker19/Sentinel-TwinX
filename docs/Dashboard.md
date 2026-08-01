# Sentinel Twin X — Web Dashboard Documentation

This document covers the UI/UX architecture, visual design tokens, single-page application (SPA) routing, and dynamic data binding configurations of the operator dashboard.

## Visual Design & Aesthetics

The Sentinel Twin X dashboard utilizes a custom, modern design system optimized for dark ambient control centers:
*   **Theme:** Sleek glassmorphism using card layers, blurred backdrops (`backdrop-filter: blur(12px)`), and thin glowing border indicators matching status states.
*   **Accents:** Emerald green for nominal operations, amber/orange for active warnings, and crimson red for critical alarms.
*   **Typography:** Space Grotesk (geometric/modern headers) combined with JetBrains Mono (precision monospace reading readouts).

## Page Navigation Architecture

The interface is built as a single-page application (SPA) driven by local JavaScript tab management:
*   **Home:** Displays max risk KPI charts, egress path summaries, connection status badges, and the live scrolling event log.
*   **Mission Control:** Controls rover mission dispatches (Patrol, zone inspections, and home docking) and renders state machine indicators.
*   **Digital Twin:** Shows a configuration-driven building layout. Rooms, waypoints, and connectivity lines are constructed on the fly.
*   **Live Camera:** Feeds MJPEG streams showing computer vision object/siren detection overlays.
*   **Alerts:** Lists historical risk alert alerts.
*   **Analytics:** Plots Temperature, Humidity, Gas, and Battery decay charts.
*   **History:** Renders completed rover missions, diagnostic printable reports, and CSV exports.
*   **AI Assistant:** Direct natural-language query interface with Gemini safety models.
*   **Settings:** Allows manual configuration adjustments (such as safe risk score bounds).

## Dynamic SVG Floor Map Renderer

Rather than rendering static coordinate elements, `map_renderer.js` initializes the floor plan dynamically:
1.  **Config Retrieval:** Fetches building settings via `/api/building-config` on startup.
2.  **Connections:** Renders line segments representing valid path transitions.
3.  **Rooms & Labels:** Centers rectangles and labels dynamically using configuration coordinates, adjusting width/height metrics according to zone properties.
4.  **Heatmap Overlays:** Maps risk scores directly to room fills (e.g. glowing red for critical risks).
