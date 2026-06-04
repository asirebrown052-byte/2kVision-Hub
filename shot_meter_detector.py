import cv2
import numpy as np
from collections import deque
import threading
import time

try:
    import pyds4
except ImportError:
    print("Warning: pyds4 not installed. Controller input will be disabled.")
    print("Install with: pip install pyds4")
    pyds4 = None


class ShotMeterDetector:
    """
    Detects the shot meter in NBA 2K and auto-releases when it turns green.
    """

    def __init__(
        self,
        camera_index=0,
        green_threshold=50,
        meter_radius_range=(30, 150),
        smoothing_frames=3,
        debug=True,
    ):
        """
        Initialize the shot meter detector.

        Args:
            camera_index: Video capture device index (0 for default Elgato)
            green_threshold: Sensitivity for green color detection (0-255)
            meter_radius_range: (min_radius, max_radius) for circle detection
            smoothing_frames: Number of frames to smooth detection
            debug: Enable debug visualization
        """
        self.camera_index = camera_index
        self.green_threshold = green_threshold
        self.meter_radius_range = meter_radius_range
        self.smoothing_frames = smoothing_frames
        self.debug = debug

        # Video capture
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 60)

        # Controller
        self.controller = None
        self.init_controller()

        # Detection state
        self.is_running = False
        self.green_detected_frames = deque(maxlen=smoothing_frames)
        self.meter_center = None
        self.meter_radius = None
        self.green_intensity = 0
        self.last_release_time = 0
        self.release_cooldown = 0.1  # Prevent rapid repeated releases

    def init_controller(self):
        """
        Initialize DS5 controller connection.
        """
        if pyds4 is None:
            print("[WARNING] pyds4 not available. Controller features disabled.")
            return

        try:
            devices = pyds4.PyDS4.enumerate_devices()
            if devices:
                self.controller = pyds4.PyDS4(devices[0])
                print(f"[SUCCESS] Connected to DS5 controller: {devices[0]}")
            else:
                print("[WARNING] No DS5 controllers found.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize controller: {e}")

    def detect_shot_meter(self, frame):
        """
        Detect the shot meter in the frame using color detection.

        Args:
            frame: Input frame from video capture

        Returns:
            tuple: (green_intensity, meter_center, meter_radius, processed_frame)
        """
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define green color range in HSV
        # Bright green for the meter indicator
        lower_green = np.array([35, 100, 100])
        upper_green = np.array([85, 255, 255])

        # Create mask for green colors
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # Apply morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Detect circles using Hough Circle Detection
        circles = cv2.HoughCircles(
            mask,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=self.meter_radius_range[0],
            maxRadius=self.meter_radius_range[1],
        )

        green_intensity = np.sum(mask) / 255  # Total green pixel count
        meter_center = None
        meter_radius = None

        if circles is not None:
            circles = np.uint16(np.around(circles))
            # Use the most prominent circle (first one)
            if len(circles[0]) > 0:
                x, y, r = circles[0][0]
                meter_center = (int(x), int(y))
                meter_radius = int(r)

        return green_intensity, meter_center, meter_radius, mask

    def is_meter_green(self):
        """
        Determine if the meter is in the green zone based on recent frames.

        Returns:
            bool: True if meter is green
        """
        if len(self.green_detected_frames) < self.smoothing_frames:
            return False

        # Check if recent frames consistently show high green intensity
        avg_green = np.mean(self.green_detected_frames)
        green_threshold_value = 500  # Adjust based on testing
        return avg_green > green_threshold_value

    def auto_release_shot(self):
        """
        Simulate pressing and releasing the shoot button on DS5.
        """
        if self.controller is None:
            print("[INFO] Controller not available for auto-release")
            return

        current_time = time.time()
        if current_time - self.last_release_time < self.release_cooldown:
            return  # Still in cooldown period

        try:
            print("[ACTION] Auto-releasing shot...")
            # Press X button (shoot in 2K)
            self.controller.button_x.set_intensity(1.0)
            time.sleep(0.05)  # Hold for 50ms
            self.controller.button_x.set_intensity(0.0)
            self.last_release_time = current_time
        except Exception as e:
            print(f"[ERROR] Failed to auto-release: {e}")

    def run(self):
        """
        Main detection loop.
        """
        if not self.cap.isOpened():
            print("[ERROR] Failed to open video capture device")
            return

        self.is_running = True
        print("[START] Shot meter detection running. Press 'q' to quit.")

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("[ERROR] Failed to read from camera")
                break

            # Detect shot meter
            green_intensity, meter_center, meter_radius, mask = self.detect_shot_meter(
                frame
            )
            self.green_detected_frames.append(green_intensity)
            self.meter_center = meter_center
            self.meter_radius = meter_radius
            self.green_intensity = green_intensity

            # Check if meter is green and auto-release
            if self.is_meter_green():
                self.auto_release_shot()

            # Debug visualization
            if self.debug:
                self._draw_debug_info(frame, meter_center, meter_radius, green_intensity)
                cv2.imshow("Shot Meter Detection", frame)
                cv2.imshow("Green Mask", mask)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                self.is_running = False
            elif key == ord("r"):
                print("[INFO] Resetting detection...")
                self.green_detected_frames.clear()

        self.cleanup()

    def _draw_debug_info(self, frame, meter_center, meter_radius, green_intensity):
        """
        Draw debug information on the frame.
        """
        # Display meter status
        status = "METER: GREEN" if self.is_meter_green() else "METER: LOADING"
        color = (0, 255, 0) if self.is_meter_green() else (0, 165, 255)
        cv2.putText(
            frame,
            status,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2,
        )

        # Display green intensity
        cv2.putText(
            frame,
            f"Green Intensity: {int(green_intensity)}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        # Draw detected circle
        if meter_center and meter_radius:
            cv2.circle(frame, meter_center, meter_radius, (0, 255, 0), 2)
            cv2.circle(frame, meter_center, 5, (0, 0, 255), -1)

        # Display FPS
        cv2.putText(
            frame,
            "Press 'q' to quit, 'r' to reset",
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

    def cleanup(self):
        """
        Clean up resources.
        """
        self.is_running = False
        self.cap.release()
        cv2.destroyAllWindows()
        if self.controller:
            self.controller.close()
        print("[STOP] Detection stopped.")


if __name__ == "__main__":
    # Initialize detector
    detector = ShotMeterDetector(
        camera_index=0,  # Change to your Elgato capture device index
        green_threshold=50,
        debug=True,
    )

    # Run detection
    try:
        detector.run()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user.")
        detector.cleanup()
