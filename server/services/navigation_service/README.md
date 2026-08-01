# Navigation Service

Exposes pathfinding and coordinate interpolation algorithms over building blueprint coordinates.

## Configuration
- `travel_speed`: Travel rate in pixels per second (default: `45.0`).

## Features
- Dijkstra pathfinding: routes between adjacent neighbor points.
- Collision avoidance: routes around zones marked as blocked by ultrasonic sensors.
- Interpolation: calculates frame positions along routing vectors for clean UI movements.
