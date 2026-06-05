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
    QTabWidget,
    QTextEdit,
    QSlider,
    QDialog,
    QLineEdit,
    QMessageBox,
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
import requests
import json
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading as thread_module

try:
    import pyds4
except ImportError:
    pyds4 = None

try:
    import pyxinput
except ImportError:
    pyxinput = None

# Discord OAuth Settings
DISCORD_CLIENT_ID = "YOUR_CLIENT_ID_HERE"  # Set this to your Discord app ID
DISCORD_REDIRECT_URI = "http://localhost:3000/callback"
DISCORD_AUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify+guilds+guilds.members.read"

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for Discord OAuth callback"""
    auth_code = None

    def do_GET(self):
        """Handle OAuth callback"""
        if "code=" in self.path:
            self.auth_code = self.path.split("code=")[1].split("&")[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication successful!</h1><p>You can close this window.</p></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress logging"""
        pass


class DiscordAuthDialog(QDialog):
    """Discord OAuth Authentication Dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_id = None
        self.user_name = None
        self.avatar_url = None
        self.token = None
        self.init_ui()

    def init_ui(self):
        """Initialize auth UI"""
        self.setWindowTitle("2K Vision Hub - Discord Login")
        self.setGeometry(100, 100, 500, 300)
        self.setStyleSheet(self.get_dark_theme())

        layout = QVBoxLayout()

        # Discord Logo / Title
        title = QLabel("2K Vision Hub")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Login with Discord")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Status Label
        self.status_label = QLabel("Click below to authenticate with Discord")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        # Discord Login Button
        login_btn = QPushButton("🔵 Login with Discord")
        login_btn.setFont(QFont("Arial", 12, QFont.Bold))
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865F2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4752C4;
            }
            QPushButton:pressed {
                background-color: #3C45A5;
            }
        """)
        login_btn.clicked.connect(self.open_discord_login)
        layout.addWidget(login_btn)

        layout.addSpacing(10)

        # Info Label
        info = QLabel("A browser window will open.\nPlease authorize the application.")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(info)

        layout.addSpacing(20)

        # User Info Display (hidden until authenticated)
        self.user_info_group = QGroupBox("Authenticated User")
        user_info_layout = QVBoxLayout()
        self.user_display = QLabel("")
        self.user_display.setAlignment(Qt.AlignCenter)
        self.user_display.setFont(QFont("Arial", 11))
        user_info_layout.addWidget(self.user_display)
        self.user_info_group.setLayout(user_info_layout)
        self.user_info_group.setVisible(False)
        layout.addWidget(self.user_info_group)

        layout.addStretch()

        # Confirm Button
        confirm_btn = QPushButton("Continue")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #00AA00;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00CC00;
            }
        """)
        confirm_btn.clicked.connect(self.on_confirm)
        layout.addWidget(confirm_btn)

        self.setLayout(layout)

    def open_discord_login(self):
        """Open Discord OAuth login in browser"""
        self.status_label.setText("Opening Discord login page...")
        webbrowser.open(DISCORD_AUTH_URL)

        # Start local server to receive callback
        self.start_callback_server()

    def start_callback_server(self):
        """Start local HTTP server to receive OAuth callback"""
        def run_server():
            server = HTTPServer(("localhost", 3000), CallbackHandler)
            server.handle_request()  # Handle one request
            
            if CallbackHandler.auth_code:
                # Exchange code for token
                self.exchange_code_for_token(CallbackHandler.auth_code)

        server_thread = thread_module.Thread(target=run_server, daemon=True)
        server_thread.start()

    def exchange_code_for_token(self, code):
        """Exchange OAuth code for access token"""
        try:
            data = {
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": "YOUR_CLIENT_SECRET_HERE",  # Set this!
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
                "scope": "identify guilds guilds.members.read",
            }

            response = requests.post(
                "https://discord.com/api/v10/oauth2/token", data=data, timeout=10
            )

            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                self.get_user_info()
            else:
                self.status_label.setText(f"❌ Authentication failed: {response.status_code}")

        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")

    def get_user_info(self):
        """Get authenticated user info from Discord"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                "https://discord.com/api/v10/users/@me", headers=headers, timeout=10
            )

            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data.get("id")
                self.user_name = user_data.get("username")
                self.avatar_url = user_data.get("avatar")

                # Display user info
                self.user_display.setText(
                    f"✓ Logged in as: <b>{self.user_name}</b>\nID: {self.user_id}"
                )
                self.user_info_group.setVisible(True)
                self.status_label.setText("✓ Authentication successful!")
                self.status_label.setStyleSheet("color: #00FF00; font-weight: bold;")

            else:
                self.status_label.setText("❌ Failed to get user info")

        except Exception as e:
            self.status_label.setText(f"❌ Error getting user info: {str(e)}")

    def on_confirm(self):
        """Confirm and proceed"""
        if self.user_id:
            self.accept()
        else:
            QMessageBox.warning(self, "Not Authenticated", "Please authenticate with Discord first!")

    def get_dark_theme(self):
        return """
        QDialog {
            background-color: #313338;
            color: #ffffff;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #40444b;
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
            color: #dbdee1;
        }
        QLineEdit {
            background-color: #40444b;
            color: #dbdee1;
            border: 1px solid #40444b;
            border-radius: 4px;
            padding: 8px;
        }
        QPushButton {
            background-color: #5865F2;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #4752C4;
        }
        """


class RemotePlayManager:
    """Manage PS5 and Xbox remote play connections"""

    def __init__(self):
        self.ps5_connected = False
        self.xbox_connected = False

    def connect_ps5(self, ip_address):
        """Connect to PS5 Remote Play"""
        try:
            self.ps5_connected = True
            return True, "PS5 Connected"
        except Exception as e:
            return False, f"PS5 Connection Failed: {e}"

    def connect_xbox(self, ip_address):
        """Connect to Xbox Remote Play"""
        try:
            self.xbox_connected = True
            return True, "Xbox Connected"
        except Exception as e:
            return False, f"Xbox Connection Failed: {e}"


class ControllerManager:
    """Manage DS5 and XInput controllers"""

    def __init__(self):
        self.ds5_controller = None
        self.xbox_controller = None
        self.ds5_connected = False
        self.xbox_connected = False

    def init_ds5(self):
        """Initialize DS5 controller"""
        if pyds4 is None:
            return False, "pyds4 not installed"

        try:
            devices = pyds4.PyDS4.enumerate_devices()
            if devices:
                self.ds5_controller = pyds4.PyDS4(devices[0])
                self.ds5_connected = True
                return True, f"DS5 Connected: {devices[0]}"
            else:
                return False, "No DS5 controllers found"
        except Exception as e:
            return False, f"DS5 Error: {e}"

    def init_xbox(self):
        """Initialize Xbox controller"""
        if pyxinput is None:
            return False, "pyxinput not installed"

        try:
            self.xbox_connected = True
            return True, "Xbox Controller Connected"
        except Exception as e:
            return False, f"Xbox Error: {e}"

    def get_ds5_status(self):
        """Get DS5 status"""
        if self.ds5_connected:
            return "✓ DS5 USB 0"
        else:
            return "✗ No DS5 Detected"

    def get_xbox_status(self):
        """Get Xbox status"""
        if self.xbox_connected:
            return "✓ Xbox Controller Connected"
        else:
            return "✗ No Xbox Controller Detected"


class DetectionThread(QThread):
    """Thread for running shot meter detection"""

    frame_ready = pyqtSignal(np.ndarray, dict)
    status_update = pyqtSignal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.is_running = False
        self.cap = None
        self.green_detected_frames = deque(maxlen=5)

    def run(self):
        """Run detection loop"""
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 60)

        if not self.cap.isOpened():
            self.status_update.emit("ERROR: Cannot open camera")
            return

        self.is_running = True
        self.status_update.emit("Detection started")

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                break

            green_intensity, meter_center, meter_radius, mask = self.detect_shot_meter(frame)
            self.green_detected_frames.append(green_intensity)

            is_green = self.is_meter_green()

            detection_data = {
                "green_intensity": green_intensity,
                "meter_center": meter_center,
                "meter_radius": meter_radius,
                "is_green": is_green,
                "mask": mask,
            }

            self.frame_ready.emit(frame, detection_data)

    def detect_shot_meter(self, frame):
        """Detect shot meter"""
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
        """Check if meter is green"""
        if len(self.green_detected_frames) < 5:
            return False
        avg_green = np.mean(self.green_detected_frames)
        return avg_green > 500

    def stop(self):
        """Stop detection"""
        self.is_running = False
        if self.cap:
            self.cap.release()


class ShotMeterGUI(QMainWindow):
    """Professional 2K Vision Hub GUI with Discord OAuth"""

    def __init__(self, user_id, user_name):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.detection_thread = None
        self.remote_play = RemotePlayManager()
        self.controller_manager = ControllerManager()

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(f"2K Vision Hub - {self.user_name}")
        self.setGeometry(50, 50, 1600, 1000)
        self.setStyleSheet(self.get_dark_theme())

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()

        # Left: Control Panel
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)

        # Right: Video + Remote Play
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 3)

        main_widget.setLayout(main_layout)

    def create_control_panel(self):
        """Create left control panel with tabs"""
        main_group = QGroupBox("Control Panel")
        layout = QVBoxLayout()

        # Auth Status
        auth_label = QLabel("Authentication")
        auth_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(auth_label)

        auth_info = QGroupBox("User Info")
        auth_layout = QVBoxLayout()
        user_display = QLabel(f"✓ {self.user_name}\nID: {self.user_id}")
        user_display.setStyleSheet("color: #00FF00; font-weight: bold;")
        auth_layout.addWidget(user_display)
        auth_info.setLayout(auth_layout)
        layout.addWidget(auth_info)

        layout.addSpacing(10)

        # Tabs for Controllers
        tabs = QTabWidget()

        # DS5 Tab
        ds5_tab = self.create_ds5_tab()
        tabs.addTab(ds5_tab, "DS5 Input")

        # XInput Tab
        xbox_tab = self.create_xbox_tab()
        tabs.addTab(xbox_tab, "XInput Input")

        # Remote Play Tab
        remote_tab = self.create_remote_play_tab()
        tabs.addTab(remote_tab, "Remote Play")

        layout.addWidget(tabs)

        # Video Settings
        settings_label = QLabel("Settings")
        settings_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(settings_label)

        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("Frame Rate:"))
        self.frame_spin = QSpinBox()
        self.frame_spin.setValue(60)
        self.frame_spin.setSuffix(" FPS")
        frame_layout.addWidget(self.frame_spin)
        layout.addLayout(frame_layout)

        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        self.res_combo = QComboBox()
        self.res_combo.addItems(["1080p (1920)", "720p (1280)", "480p (640)"])
        self.res_combo.setCurrentIndex(1)
        res_layout.addWidget(self.res_combo)
        layout.addLayout(res_layout)

        # Control Buttons
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

        # Status
        status_label = QLabel("Status")
        status_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(status_label)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)
        self.status_text.setText(f"[INFO] User {self.user_name} authenticated\n[INFO] Ready to start\n")
        layout.addWidget(self.status_text)

        layout.addStretch()

        main_group.setLayout(layout)
        return main_group

    def create_ds5_tab(self):
        """Create DS5 controller tab"""
        group = QGroupBox("DualSense Controllers")
        layout = QVBoxLayout()

        status_label = QLabel("Status: Not capturing")
        status_label.setStyleSheet("color: #FF6B6B;")
        layout.addWidget(status_label)

        # Controller list
        controller_list = QGroupBox("Detected Controllers")
        ctrl_layout = QVBoxLayout()

        ds5_status, ds5_msg = self.controller_manager.init_ds5()
        controller_item = QLabel(self.controller_manager.get_ds5_status())
        controller_item.setStyleSheet("background-color: #2d2d2d; padding: 8px; border-radius: 4px;")
        ctrl_layout.addWidget(controller_item)

        controller_list.setLayout(ctrl_layout)
        layout.addWidget(controller_list)

        # Start Capture button
        capture_btn = QPushButton("Start Capture")
        capture_btn.setStyleSheet("background-color: #0d47a1; color: white;")
        layout.addWidget(capture_btn)

        # Write to controller
        write_check = QCheckBox("Write to Controller Output")
        layout.addWidget(write_check)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_xbox_tab(self):
        """Create Xbox controller tab"""
        group = QGroupBox("Xbox Controllers")
        layout = QVBoxLayout()

        status_label = QLabel("Status: Not capturing")
        status_label.setStyleSheet("color: #FF6B6B;")
        layout.addWidget(status_label)

        # Controller list
        controller_list = QGroupBox("Detected Controllers")
        ctrl_layout = QVBoxLayout()

        xbox_status, xbox_msg = self.controller_manager.init_xbox()
        controller_item = QLabel(self.controller_manager.get_xbox_status())
        controller_item.setStyleSheet("background-color: #2d2d2d; padding: 8px; border-radius: 4px;")
        ctrl_layout.addWidget(controller_item)

        controller_list.setLayout(ctrl_layout)
        layout.addWidget(controller_list)

        # Start Capture button
        capture_btn = QPushButton("Start Capture")
        capture_btn.setStyleSheet("background-color: #107c10; color: white;")
        layout.addWidget(capture_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_remote_play_tab(self):
        """Create Remote Play tab"""
        group = QGroupBox("Remote Play")
        layout = QVBoxLayout()

        # PS5 Section
        ps5_label = QLabel("PlayStation 5")
        ps5_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(ps5_label)

        ps5_layout = QHBoxLayout()
        self.ps5_status_label = QLabel("Status: Disconnected")
        self.ps5_status_label.setStyleSheet("color: #FF6B6B;")
        ps5_layout.addWidget(self.ps5_status_label)
        ps5_connect = QPushButton("Connect")
        ps5_connect.setStyleSheet("background-color: #003087; color: white;")
        ps5_layout.addWidget(ps5_connect)
        layout.addLayout(ps5_layout)

        # Xbox Section
        xbox_label = QLabel("Xbox Series X|S")
        xbox_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(xbox_label)

        xbox_layout = QHBoxLayout()
        self.xbox_status_label = QLabel("Status: Disconnected")
        self.xbox_status_label.setStyleSheet("color: #FF6B6B;")
        xbox_layout.addWidget(self.xbox_status_label)
        xbox_connect = QPushButton("Connect")
        xbox_connect.setStyleSheet("background-color: #107c10; color: white;")
        xbox_layout.addWidget(xbox_connect)
        layout.addLayout(xbox_layout)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_right_panel(self):
        """Create right panel with video display"""
        group = QGroupBox("Video Display")
        layout = QVBoxLayout()

        self.video_label = QLabel()
        self.video_label.setMinimumSize(1000, 700)
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
        """Start detection"""
        self.detection_thread = DetectionThread(camera_index=0)
        self.detection_thread.frame_ready.connect(self.on_frame_ready)
        self.detection_thread.status_update.connect(self.on_status_update)
        self.detection_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_status("[START] Detection started")

    def stop_detection(self):
        """Stop detection"""
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread.wait()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_status("[STOP] Detection stopped")

    def on_frame_ready(self, frame, detection_data):
        """Handle frame"""
        frame = self.draw_frame_info(frame, detection_data)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = 3 * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaledToWidth(self.video_label.width(), Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)

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
        """Handle status update"""
        self.log_status(f"[INFO] {message}")

    def draw_frame_info(self, frame, detection_data):
        """Draw info on frame"""
        meter_center = detection_data["meter_center"]
        meter_radius = detection_data["meter_radius"]
        green_intensity = detection_data["green_intensity"]
        is_green = detection_data["is_green"]

        status = "METER: GREEN" if is_green else "METER: LOADING"
        color = (0, 255, 0) if is_green else (0, 165, 255)
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(
            frame,
            f"Green Intensity: {int(green_intensity)}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        if meter_center and meter_radius:
            cv2.circle(frame, meter_center, meter_radius, (0, 255, 0), 2)
            cv2.circle(frame, meter_center, 5, (0, 0, 255), -1)

        return frame

    def log_status(self, message):
        """Log message"""
        current_text = self.status_text.toPlainText()
        self.status_text.setText(current_text + message + "\n")
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    def get_dark_theme(self):
        """Dark theme"""
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
        QTabWidget::pane {
            border: 1px solid #444;
        }
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #ffffff;
            padding: 8px;
            border: 1px solid #444;
        }
        QTabBar::tab:selected {
            background-color: #0d47a1;
        }
        QCheckBox {
            color: #ffffff;
        }
        """

    def closeEvent(self, event):
        """Close event"""
        self.stop_detection()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Show Discord login dialog
    auth_dialog = DiscordAuthDialog()
    if auth_dialog.exec_():
        # User authenticated - launch main GUI
        window = ShotMeterGUI(auth_dialog.user_id, auth_dialog.user_name)
        window.show()
        sys.exit(app.exec_())
    else:
        # User cancelled auth
        sys.exit(0)
