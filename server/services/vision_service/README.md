# Vision Service

Coordinates computer vision algorithms (motion, HSV color fire filters, HOG SVM pedestrian search) on video frames.

## Configuration
- `motion_threshold`: Percentage of frame change to register motion (default: `1.5%`).
- `fire_pixel_threshold`: Red/orange pixel ratio in HSV space before fire alert (default: `0.005` or 0.5%).

## Algorithms
- motion: Frame differencing.
- fire: HSV segmentation.
- person: HOG + Linear SVM.
- Future placeholders: smoke, faces, general object classifications.
