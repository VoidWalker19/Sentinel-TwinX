# Alert Service

Expose math functions for fire risk classification (CHRONOS scoring), EMA value filters, and weighted Dijkstra evacuation recommendations.

## Core Operations
- `compute_chronos_risk`: Evaluates compound sensor hazard variables.
- `find_safest_exit`: Shortest path routing weighted by local danger levels.
- `generate_evac_tts_message`: Builds announcement alerts for voice synthesis.
