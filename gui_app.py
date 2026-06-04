import sys
import cv2
import numpy as np
from collections import deque
import threading
import time
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QGridLayout,
    QTabWidget,
    QTextEdit,
    QSlider,
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread

try:
    import pyds4
except ImportError:
    pyds4 = None


class DetectionThread(QThread):
    """Thread for running shot meter detection without blocking GUI."""

    frame_ready = pyqtSignal(np.ndarray, dict)
    status_update = pyqtSignal(str)

    def __init__(self, camera_index=0, green_threshold=50, debug=True):
        super().__init__()
        self.camera_index = camera_index
        self.green_threshold = green_threshold
        self.debug = debug
        self.is_running = False
        self.cap = None
        self.controller = None
        self.green_detected_frames = deque(maxlen=5)
        self.last_release_time = 0

    def run(self):
        """Run detection loop."""
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 60)

        if not self.cap.isOpened():
            self.status_update.emit("ERROR: Cannot open camera")
            return

        self.init_controller()
        self.is_running = True
        self.status_update.emit("Detection started")

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                break

            green_intensity, meter_center, meter_radius, mask = self.detect_shot_meter(
                frame
            )
            self.green_detected_frames.append(green_intensity)

            # Check if meter is green
            is_green = self.is_meter_green()
            if is_green:
                self.auto_release_shot()

            detection_data = {
                "green_intensity": green_intensity,
                "meter_center": meter_center,
                "meter_radius": meter_radius,
                "is_green": is_green,
                "mask": mask,
            }

            self.frame_ready.emit(frame, detection_data)

    def detect_shot_meter(self, frame):
        """Detect shot meter in frame."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 100, 100])
        upper_green = np.array([85, 255, 255])

        mask = cv2.inRange(hsv, lower_green, upper_green)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        circles = cv2.HoughCircles(
            mask,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=30,
            maxRadius=150,
        )

        green_intensity = np.sum(mask) / 255
        meter_center = None
        meter_radius = None

        if circles is not None:
            circles = np.uint16(np.around(circles))
            if len(circles[0]) > 0:
                x, y, r = circles[0][0]
                meter_center = (int(x), int(y))
                meter_radius = int(r)

        return green_intensity, meter_center, meter_radius, mask

    def is_meter_green(self):
        """Check if meter is green."""
        if len(self.green_detected_frames) < 5:
            return False
        avg_green = np.mean(self.green_detected_frames)
        return avg_green > 500

    def auto_release_shot(self):
        """Auto-release shot."""
        if self.controller is None:
            return

        current_time = time.time()
        if current_time - self.last_release_time < 0.1:
            return

        try:
            self.controller.button_x.set_intensity(1.0)
            time.sleep(0.05)
            self.controller.button_x.set_intensity(0.0)
            self.last_release_time = current_time
            self.status_update.emit("SHOT RELEASED")
        except Exception as e:
            self.status_update.emit(f"Release error: {e}")

    def init_controller(self):
        """Initialize DS5 controller."""
        if pyds4 is None:
            self.status_update.emit("WARNING: pyds4 not available")
            return

        try:
            devices = pyds4.PyDS4.enumerate_devices()
            if devices:
                self.controller = pyds4.PyDS4(devices[0])
                self.status_update.emit(f"DS5 Connected")
            else:
                self.status_update.emit("WARNING: No DS5 found")
        except Exception as e:
            self.status_update.emit(f"Controller error: {e}")

    def stop(self):
        """Stop detection."""
        self.is_running = False
        if self.cap:
            self.cap.release()
        if self.controller:
            self.controller.close()


class ShotMeterGUI(QMainWindow):
    """Main GUI application window."""

    def __init__(self):
        super().__init__()
        self.detection_thread = None
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)

    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("2K Vision Hub - Shot Meter Detection")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(self.get_dark_theme())

        # Main container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()

        # Left panel - Controls
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)

        # Right panel - Video display
        right_panel = self.create_video_panel()
        main_layout.addWidget(right_panel, 3)

        main_widget.setLayout(main_layout)

    def create_control_panel(self):
        """Create left control panel."""
        group = QGroupBox("Controls")
        layout = QVBoxLayout()

        # Python Script section
        script_label = QLabel("CV Python")
        script_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(script_label)

        self.python_status = QLabel("✓ Python 3.11")
        self.python_status.setStyleSheet("color: #00FF00; font-weight: bold;")
        layout.addWidget(self.python_status)

        # Video Input section
        video_label = QLabel("Video Input")
        video_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(video_label)

        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Device:"))
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["Elgato Hi", "Camera 1", "Camera 2"])
        camera_layout.addWidget(self.camera_combo)
        layout.addLayout(camera_layout)

        # Settings section
        settings_label = QLabel("Settings")
        settings_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(settings_label)

        # Frame rate
        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("Frame Rate:"))
        self.frame_spin = QSpinBox()
        self.frame_spin.setValue(60)
        self.frame_spin.setSuffix(" FPS")
        frame_layout.addWidget(self.frame_spin)
        layout.addLayout(frame_layout)

        # Resolution
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        self.res_combo = QComboBox()
        self.res_combo.addItems(["1080p (1920)", "720p (1280)", "480p (640)"])
        self.res_combo.setCurrentIndex(1)
        res_layout.addWidget(self.res_combo)
        layout.addLayout(res_layout)

        # Green threshold slider
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Green Sensitivity:"))
        self.green_slider = QSlider(Qt.Horizontal)
        self.green_slider.setMinimum(10)
        self.green_slider.setMaximum(100)
        self.green_slider.setValue(50)
        thresh_layout.addWidget(self.green_slider)
        layout.addLayout(thresh_layout)

        # Auto-release checkbox
        self.auto_release_check = QCheckBox("Auto-Release Shot")
        self.auto_release_check.setChecked(True)
        layout.addWidget(self.auto_release_check)

        # Debug checkbox
        self.debug_check = QCheckBox("Debug Visualization")
        self.debug_check.setChecked(True)
        layout.addWidget(self.debug_check)

        # Control buttons
        control_label = QLabel("Control")
        control_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(control_label)

        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_detection)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #AA0000; color: white; font-weight: bold;")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        layout.addLayout(button_layout)

        # Status section
        status_label = QLabel("Status")
        status_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(status_label)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)
        self.status_text.setText("[INFO] Ready to start\n")
        layout.addWidget(self.status_text)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_video_panel(self):
        """Create right video display panel."""
        group = QGroupBox("Video Display")
        layout = QVBoxLayout()

        # Main video display
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Waiting for video feed...")
        layout.addWidget(self.video_label)

        # Stats
        stats_layout = QHBoxLayout()
        self.fps_label = QLabel("FPS: 0")
        self.green_label = QLabel("Green Intensity: 0")
        self.meter_label = QLabel("Meter: LOADING")
        self.meter_label.setStyleSheet("color: #FFA500;")

        stats_layout.addWidget(self.fps_label)
        stats_layout.addWidget(self.green_label)
        stats_layout.addWidget(self.meter_label)
        layout.addLayout(stats_layout)

        group.setLayout(layout)
        return group

    def start_detection(self):
        """Start shot meter detection."""
        camera_index = self.camera_combo.currentIndex()
        self.detection_thread = DetectionThread(camera_index=camera_index)
        self.detection_thread.frame_ready.connect(self.on_frame_ready)
        self.detection_thread.status_update.connect(self.on_status_update)
        self.detection_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_status("[START] Detection thread started")

    def stop_detection(self):
        """Stop shot meter detection."""
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread.wait()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_status("[STOP] Detection stopped")

    def on_frame_ready(self, frame, detection_data):
        """Handle new frame from detection thread."""
        # Draw detection info on frame
        frame = self.draw_frame_info(frame, detection_data)

        # Convert to QPixmap
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = 3 * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)

        # Scale to fit label
        scaled_pixmap = pixmap.scaledToWidth(
            self.video_label.width(), Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

        # Update stats
        green_intensity = detection_data["green_intensity"]
        is_green = detection_data["is_green"]

        self.green_label.setText(f"Green Intensity: {int(green_intensity)}")

        if is_green:
            self.meter_label.setText("Meter: GREEN ✓")
            self.meter_label.setStyleSheet("color: #00FF00; font-weight: bold;")
        else:
            self.meter_label.setText("Meter: LOADING")
            self.meter_label.setStyleSheet("color: #FFA500;")

    def on_status_update(self, message):
        """Handle status updates from detection thread."""
        self.log_status(f"[INFO] {message}")

    def draw_frame_info(self, frame, detection_data):
        """Draw detection info on frame."""
        meter_center = detection_data["meter_center"]
        meter_radius = detection_data["meter_radius"]
        green_intensity = detection_data["green_intensity"]
        is_green = detection_data["is_green"]

        # Draw meter status
        status = "METER: GREEN" if is_green else "METER: LOADING"
        color = (0, 255, 0) if is_green else (0, 165, 255)
        cv2.putText(
            frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2
        )

        # Draw green intensity
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

        return frame

    def log_status(self, message):
        """Log message to status text."""
        current_text = self.status_text.toPlainText()
        self.status_text.setText(current_text + message + "\n")
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    def update_ui(self):
        """Update UI periodically."""
        pass

    def get_dark_theme(self):
        """Return dark theme stylesheet."""
        return """
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QLabel {
            color: #ffffff;
        }
        QPushButton {
            background-color: #0d47a1;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0d3a8f;
        }
        QComboBox, QSpinBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 4px;
        }
        QTextEdit {
            background-color: #2d2d2d;
            color: #00ff00;
            border: 1px solid #444;
            border-radius: 4px;
            font-family: 'Courier New';
            font-size: 10px;
        }
        QCheckBox {
            color: #ffffff;
        }
        QSlider::groove:horizontal {
            background-color: #444;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background-color: #0d47a1;
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }
        """

    def closeEvent(self, event):
        """Handle window close."""
        self.stop_detection()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShotMeterGUI()
    window.show()
    sys.exit(app.exec_())
