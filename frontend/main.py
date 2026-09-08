"""Rocket League Overlay - PySide6 frontend.

Two windows:
  * Session overlay - frameless, always-on-top, draggable, with a gear
    button to open settings.
  * Settings window - normal window, opens via the gear button or a
    global hotkey (configurable in the settings itself).

Talks to the backend only through frontend/api_client.py.
"""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
  QApplication,
  QComboBox,
  QFormLayout,
  QGroupBox,
  QHBoxLayout,
  QLabel,
  QLineEdit,
  QPushButton,
  QVBoxLayout,
  QWidget,
)

import frontend.api_client as api
import frontend.hotkey as hotkey

DEFAULT_HOTKEY = "F8"

STATS_POLL_MS = 2000  # poll backend stats every 2 s

# Hover backgrounds for small header buttons (mild, transparent tints).
HOVER_WHITE = "rgba(255, 255, 255, 40)"
HOVER_RED = "rgba(240, 45, 45, 60)"
# HOVER_RED = "rgba(255, 80, 80, 60)"


def style_header_button(button: QPushButton, hover_color: str):
  """Flat header button that shows a transparent tint when hovered."""
  button.setStyleSheet(
    f"""
    QPushButton {{
      border: none;
      background: transparent;
      border-radius: 4px;
    }}
    QPushButton:hover {{ background: {hover_color}; }}
    QPushButton:pressed {{ background: rgba(255, 255, 255, 80); }}
    """
  )

LAUNCHERS = ["Steam", "Epic"]
HOTKEY_CHOICES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]

WIN_COLOR = "#50dc64"
LOSS_COLOR = "#ff5050"
STREAK_COLOR = "#ffc850"
ACCENT_COLOR = "#4db8ff"
ERROR_COLOR = "#ff5050"
STATUS_OK_COLOR = "#96dc96"


def format_streak(streak: int) -> str:
  if streak == 0:
    return "-"
  return f"{abs(streak)}{'W' if streak > 0 else 'L'}"


class FramelessWindow(QWidget):
  """Frameless window base with click-and-drag moving."""

  def __init__(self):
    super().__init__()
    self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    self._drag_offset = None

  def make_header(self, title_text: str) -> QHBoxLayout:
    """Header row with a colored title and a close button."""
    header = QHBoxLayout()
    title = QLabel(title_text)
    title.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: bold;")
    header.addWidget(title)
    header.addStretch()
    close_button = QPushButton("✕")
    close_button.setFixedSize(24, 24)
    close_button.setToolTip("Close")
    style_header_button(close_button, HOVER_WHITE)
    close_button.clicked.connect(self.close)
    header.addWidget(close_button)
    return header

  # Frameless window dragging
  def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
      self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

  def mouseMoveEvent(self, event):
    if (
      event.buttons() & Qt.MouseButton.LeftButton
      and self._drag_offset is not None
    ):
      self.move(event.globalPosition().toPoint() - self._drag_offset)

  def mouseReleaseEvent(self, event):
    self._drag_offset = None


class SessionWindow(FramelessWindow):
  """Small frameless overlay showing current session stats."""

  def __init__(self, app):
    super().__init__()
    self.app = app
    self.setWindowFlags(
      Qt.WindowType.FramelessWindowHint
      | Qt.WindowType.WindowStaysOnTopHint
      | Qt.WindowType.Tool
    )
    self.setWindowTitle("RL Overlay - Session")
    # self.setFixedWidth(150)
    self.setMinimumWidth(100)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(10, 8, 10, 12)
    layout.setSpacing(6)

    header = QHBoxLayout()
    # title = QLabel("Session")
    # title.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: bold;")
    # header.addWidget(title)
    header.addStretch(5)

    # RESET SESSION BUTTON 
    reset_button = QPushButton("Reset")
    reset_button.setFixedSize(42, 20)
    reset_button.setToolTip("Reset session")
    reset_button.clicked.connect(self.reset_session)
    header.addWidget(reset_button)

    # SETTINGS BUTTON
    gear = QPushButton("⚙")
    gear.setFixedSize(16, 16)
    gear.setToolTip("Settings")
    style_header_button(gear, HOVER_WHITE)
    gear.clicked.connect(self.app.show_settings)
    header.addWidget(gear)
    quit_button = QPushButton("✕")
    quit_button.setFixedSize(16, 16)
    quit_button.setToolTip("Quit overlay")
    style_header_button(quit_button, HOVER_RED)
    quit_button.clicked.connect(self.app.quit)
    header.addWidget(quit_button)
    layout.addLayout(header)

    self.wins_label = self._stat_label("Wins: 0", WIN_COLOR)
    self.losses_label = self._stat_label("Losses: 0", LOSS_COLOR)
    self.streak_label = self._stat_label("Streak: -", STREAK_COLOR)
    # layout.addWidget(self.wins_label)
    # layout.addWidget(self.losses_label)
    # layout.addWidget(self.streak_label)
    stats_row = QHBoxLayout()
    stats_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

    stats_row.addWidget(self.wins_label)
    stats_row.addSpacing(12)
    stats_row.addWidget(self.losses_label)

    layout.addLayout(stats_row)     # horizontal row inside the vertical column
    layout.addWidget(self.streak_label, alignment=Qt.AlignmentFlag.AlignCenter)  # streak stays below, full width

    self.connection_error_label = QLabel("Backend unreachable")
    self.connection_error_label.setStyleSheet(f"color: {ERROR_COLOR};")
    self.connection_error_label.hide()
    layout.addWidget(self.connection_error_label)

    self.place_top_right()

  def place_top_right(self, margin: int = 10):
    """Default position: top-right corner of the primary screen."""
    screen = self.screen() or QApplication.primaryScreen()
    geometry = screen.availableGeometry()
    self.adjustSize()
    self.move(
      geometry.right() - self.width() - margin,
      geometry.top() + margin,
    )

  @staticmethod
  def _stat_label(text: str, color: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"color: {color}; font-size: 15px;")
    return label

  # ---------- Backend data ----------

  def reset_session(self):
      try:
          api.reset_session()
          self.refresh_stats()
      except Exception:
          self.connection_error_label.show()


  def refresh_stats(self):
    try:
      stats = api.get_stats()
      self.wins_label.setText(f"Wins: {stats['wins']}")
      self.losses_label.setText(f"Losses: {stats['losses']}")
      self.streak_label.setText(f"Streak: {format_streak(stats['streak'])}")
      self.connection_error_label.hide()
    except Exception:
      # Backend down or busy - keep last known values, show a hint.
      self.connection_error_label.show()


class SettingsWindow(FramelessWindow):
  """Frameless settings window, styled like the session overlay."""

  def __init__(self, app):
    super().__init__()
    self.app = app
    self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    self.setWindowTitle("RL Overlay - Settings")

    outer = QVBoxLayout(self)
    outer.setContentsMargins(16, 8, 16, 16)
    outer.setSpacing(10)

    outer.addLayout(self.make_header("Settings"))

    id_group = QGroupBox("Player identification")
    form = QFormLayout(id_group)

    self.user_name_input = QLineEdit()
    self.user_name_input.setPlaceholderText("Display name")
    form.addRow("Name", self.user_name_input)

    self.launcher_combo = QComboBox()
    self.launcher_combo.addItems(LAUNCHERS)
    form.addRow("Launcher", self.launcher_combo)

    self.user_id_input = QLineEdit()
    self.user_id_input.setPlaceholderText("SteamID3 / Epic Account ID")
    form.addRow("ID", self.user_id_input)

    outer.addWidget(id_group)

    ui_group = QGroupBox("Overlay")
    ui_form = QFormLayout(ui_group)
    self.hotkey_combo = QComboBox()
    self.hotkey_combo.addItems(HOTKEY_CHOICES)
    self.hotkey_combo.setCurrentText(app.hotkey)
    # Apply immediately when a new key is chosen.
    self.hotkey_combo.currentTextChanged.connect(app.set_hotkey)
    ui_form.addRow("Open settings hotkey", self.hotkey_combo)
    outer.addWidget(ui_group)

    button_row = QHBoxLayout()
    save_button = QPushButton("Save Settings")
    save_button.clicked.connect(self.on_save_settings)
    button_row.addWidget(save_button)
    self.settings_status_label = QLabel("")
    self.settings_status_label.setStyleSheet(f"color: {STATUS_OK_COLOR};")
    button_row.addWidget(self.settings_status_label)
    button_row.addStretch()
    outer.addLayout(button_row)


  def on_save_settings(self):
    user_name = self.user_name_input.text()
    launcher = self.launcher_combo.currentText()
    user_id = self.user_id_input.text().strip()

    if not user_id:
      self._set_status("User ID is required!", error=True)
      return

    try:
      api.update_settings(user_name, launcher, user_id)
      self._set_status("Settings saved!")
    except Exception:
      self._set_status("Could not reach backend!", error=True)

  def load_settings(self):
    """Pre-fills the fields with values from the backend."""
    try:
      settings = api.get_settings()
      self.user_name_input.setText(settings["user_name"] or "")
      self.launcher_combo.setCurrentText(settings["launcher"] or LAUNCHERS[0])
      # user_id is stored as "launcher|id|0" - show only the raw id part.
      user_id = settings["user_id"] or ""
      self.user_id_input.setText(
        user_id.split("|")[1] if "|" in user_id else user_id
      )
      self.hotkey_combo.setCurrentText(settings.get("hotkey") or DEFAULT_HOTKEY)
    except Exception:
      self._set_status("Backend offline - start it first!", error=True)

  def _set_status(self, text: str, error: bool = False):
    self.settings_status_label.setText(text)
    color = ERROR_COLOR if error else STATUS_OK_COLOR
    self.settings_status_label.setStyleSheet(f"color: {color};")


class OverlayApp:
  """Owns both windows, the poll timer and the global hotkey."""

  def __init__(self, qt_app: QApplication):
    self.qt_app = qt_app

    # Hotkey comes from the backend settings (DB); fall back to the default
    # when the backend is offline on startup.
    self.hotkey = DEFAULT_HOTKEY
    try:
      self.hotkey = api.get_settings().get("hotkey") or DEFAULT_HOTKEY
    except Exception:
      pass

    self.session_window = SessionWindow(self)
    self.settings_window = None  # created lazily on first open

    self.poll_timer = QTimer()
    self.poll_timer.setInterval(STATS_POLL_MS)
    self.poll_timer.timeout.connect(self.session_window.refresh_stats)
    self.poll_timer.start()
    self.session_window.refresh_stats()

    if not hotkey.register(self.hotkey):
      print(f"Warning: hotkey {self.hotkey} is already in use by another app.")
    self.hotkey_filter = hotkey.HotkeyFilter(self.show_settings)
    self.qt_app.installNativeEventFilter(self.hotkey_filter)

  def show_settings(self):
    if self.settings_window is None:
      self.settings_window = SettingsWindow(self)
      self.settings_window.load_settings()
    self.settings_window.show()
    self.settings_window.raise_()
    self.settings_window.activateWindow()

  def set_hotkey(self, key: str):
    """Called when the user picks a new hotkey in the settings window."""
    try:
      hotkey.unregister()
    except Exception:
      pass
    if hotkey.register(key):
      self.hotkey = key
      self._save_hotkey(key)
      if self.settings_window:
        self.settings_window._set_status("Hotkey updated!")
    elif key == self.hotkey:
      hotkey.register(key)  # re-register old key after unregister
    else:
      # New key taken by another app - fall back to the old one.
      hotkey.register(self.hotkey)
      if self.settings_window:
        self.settings_window.hotkey_combo.setCurrentText(self.hotkey)
        self.settings_window._set_status(
          f"'{key}' is already in use by another app!", error=True
        )

  def _save_hotkey(self, key: str):
    """Persists the hotkey via the backend; keeps old value on failure."""
    try:
      api.update_settings_hotkey(key)
    except Exception:
      if self.settings_window:
        self.settings_window._set_status(
          "Could not reach backend - hotkey not saved!", error=True
        )

  def quit(self):
    hotkey.unregister()
    self.qt_app.quit()


def run():
  app = QApplication(sys.argv)
  # The session overlay is a Qt.Tool window, which Qt does not count as a
  # "main window" - so we control quitting ourselves via the X button.
  app.setQuitOnLastWindowClosed(False)
  # Dark palette so the overlay fits Rocket League's look.
  app.setStyle("Fusion")
  palette = QPalette()
  palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
  palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
  palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
  palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
  palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
  palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
  palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
  palette.setColor(QPalette.ColorRole.Highlight, QColor(77, 184, 255))
  palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
  app.setPalette(palette)

  overlay = OverlayApp(app)
  overlay.session_window.show()

  sys.exit(app.exec())


if __name__ == "__main__":
  run()
