# 2K Vision Hub - Shot Meter Detection

Automated shot meter detection and auto-release for NBA 2K using computer vision and DS5 controller integration.

## Features

✅ **Video Capture** - Captures video from Elgato card or any USB video device  
✅ **Shot Meter Detection** - Detects the shooting meter using color detection and circle Hough transform  
✅ **Green Detection** - Identifies when the meter enters the green zone  
✅ **DS5 Controller Integration** - Auto-releases shots via DS5 X button when meter is green  
✅ **Frame Smoothing** - Reduces false positives with multi-frame detection averaging  
✅ **Debug Visualization** - Real-time display of detected meter and intensity levels  

## Requirements

- Python 3.8+
- OpenCV (cv2)
- NumPy
- PyDS4 (for DS5 controller)

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/asirebrown052-byte/2kVision-Hub.git
cd 2kVision-Hub
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Connect Devices
- Connect your Elgato capture card via USB
- Connect your DS5 controller via Bluetooth or USB

## Usage

### Basic Usage
```bash
python shot_meter_detector.py
```

### Controls
- **q** - Quit the detection script
- **r** - Reset detection (clear frame buffer)

### Configuration

Edit `shot_meter_detector.py` to adjust parameters:

```python
detector = ShotMeterDetector(
    camera_index=0,              # Video device index (0 for default)
    green_threshold=50,          # Green color sensitivity
    meter_radius_range=(30, 150),# Min/max radius for circle detection
    smoothing_frames=3,          # Frames to average for stability
    debug=True                   # Show visualization
)
```

## How It Works

1. **Capture Frame** - Reads video from Elgato card
2. **Color Detection** - Converts to HSV and masks green colors
3. **Circle Detection** - Uses Hough Circle Transform to find meter
4. **Intensity Tracking** - Accumulates green pixel intensity over frames
5. **Auto-Release** - When intensity threshold is met, triggers DS5 X button
6. **Cooldown** - Prevents rapid repeated releases (100ms default)

## Troubleshooting

### Camera not detected
- Check device index: `camera_index=0` for first device, `camera_index=1` for second, etc.
- List available devices:
```python
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera {i} available")
```

### Controller not connecting
- Ensure DS5 is connected via Bluetooth or USB
- On Windows, install the DS4Windows driver
- Check PyDS4 compatibility with your OS

### Shot meter not detected
- Adjust `green_threshold` value
- Check lighting conditions
- Modify `meter_radius_range` if meter size differs
- Enable debug mode to visualize detection

## Performance Tips

- Lower resolution (1280x720) for faster processing
- Increase `smoothing_frames` for stability (trades responsiveness for accuracy)
- Use `debug=False` in production to improve FPS
- Test with `green_threshold` values between 30-70

## Contributing

Feel free to submit issues or pull requests to improve detection accuracy!

## License

MIT License - See LICENSE file for details
