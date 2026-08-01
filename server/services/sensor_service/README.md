# Sensor Service

Manages dynamic calibrations of thresholds and linear regressions of risk trend predictions.

## Features
- Zone calibration: accumulates 20 readings to define standard deviation and mean offsets.
- Trend predictor: fits slope parameters to track direction (rising, stable, falling) and project critical times.

## Errors Handled
- NaN DHT sensor measurements: Handled defensively when feeding the calibrator.
- Insufficient history counts: Bypasses slope computations and returns stable fallback predictions.
