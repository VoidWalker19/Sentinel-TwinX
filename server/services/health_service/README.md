# Health Service

Monages sensor data integrity checking and enforces the Honesty Rule (staleness connection thresholds).

## Configuration
- `staleness_timeout`: Duration in seconds before marked offline (default: `10.0`).

## Detection Methods
- stuck: Consecutive identical values.
- spike: Multi-sigma jumps relative to rolling average.
- out_of_range: Physically impossible thresholds.
- flatline: Zero-variance detection.
- staleness: Updates tracked timestamps and triggers offline gray-out events.
