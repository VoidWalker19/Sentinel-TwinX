# Configuration Service

Responsible for managing environmental settings and parsing the building configuration schema.

## Configuration
- `config_path`: Path to `building.json` (defaults to `config/building.json`).

## Features
- Dynamic retrieval of zones, adjacent neighbor graphs, thresholds, and pin maps.
- System env values queries.

## Errors Handled
- Missing `building.json`: Throws detailed FileNotFoundError at startup to prevent application from loading invalid defaults.
