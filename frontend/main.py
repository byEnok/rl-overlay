"""Rocket League Overlay - PySide6 frontend.

Two windows:
  * Session overlay - frameless, always-on-top, draggable, with a gear
    button to open settings.
  * Settings window - normal window, opens via the gear button or a
    global hotkey (configurable in the settings itself).

Talks to the backend only through frontend/api_client.py.
"""

import datetime
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette, QIcon, QAction
from PySide6.QtWidgets import (
  QApplication,
  QComboBox,
  QFormLayout,
  QGroupBox,
  QHBoxLayout,
  QLabel,
  QLineEdit,
  QPushButton,
  QScrollArea,
  QVBoxLayout,
  QWidget,
  QFrame,
  QSystemTrayIcon,
  QMenu
)

import frontend.api_client as api
import frontend.hotkey as hotkey

DEFAULT_HOTKEY = "F8"
DEFAULT_HISTORY_HOTKEY = "F9"

STATS_POLL_MS = 2000  # poll backend stats every 2 s

GAMEMODES = ["1v1", "2v2", "3v3"]

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


def style_mode_button(button: QPushButton):
  """Flat gamemode tab: hover tint, blue text while it is the active tab."""
  button.setStyleSheet(
    f"""
    QPushButton {{
      border: 0.5px solid gray;
      background: transparent;
      border-radius: 4px;
      color: palette(text);
    }}
    QPushButton:hover {{ background: {HOVER_WHITE}; }}
    QPushButton:pressed {{ background: rgba(255, 255, 255, 80); }}
    QPushButton:checked {{ color: {ACCENT_COLOR}; font-weight: bold; }}
    """
  )

LAUNCHERS = ["Steam", "Epic"]
HOTKEY_CHOICES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]

WIN_COLOR = "#50dc64"
LOSS_COLOR = "#ff5050"
STREAK_COLOR = "#ffc850"
ACCENT_COLOR = "#4db8ff"
# ACCENT_COLOR_MILD = "#6faed6"
ACCENT_COLOR_MILD = "#5f9fc7"
ERROR_COLOR = "#ff5050"
STATUS_OK_COLOR = "#96dc96"
# Shared window background (QColor 30, 30, 30) - also used as the
# "hollow" letter color inside the W/L squares.
WINDOW_BACKGROUND_COLOR = "#1e1e1e"


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
    header.addStretch()
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
    header.addStretch(5)

    # GAMEMODE TABS (one tab per tracked gamemode, left of the reset button)
    self.mode_buttons = {}
    for mode in GAMEMODES:
      mode_button = QPushButton(mode)
      mode_button.setCheckable(True)
      mode_button.setFixedSize(34, 20)
      style_mode_button(mode_button)
      mode_button.setToolTip(f"Show {mode} session stats")
      mode_button.clicked.connect(
        lambda _checked, m=mode: self.select_mode(m)
      )
      header.addWidget(mode_button)
      self.mode_buttons[mode] = mode_button

    # RESET SESSION BUTTON (resets the selected gamemode's session)
    reset_button = QPushButton("Reset")
    reset_button.setFixedSize(42, 20)
    reset_button.setToolTip("Reset selected gamemode's session")
    reset_button.clicked.connect(self.reset_session)
    header.addWidget(reset_button)

    # SETTINGS BUTTON
    gear = QPushButton("⚙")
    gear.setFixedSize(16, 16)
    gear.setToolTip("Settings")
    style_header_button(gear, HOVER_WHITE)
    gear.clicked.connect(self.app.show_settings)
    header.addWidget(gear)
    # Quit App Button
    quit_button = QPushButton("✕")
    quit_button.setFixedSize(16, 16)
    quit_button.setToolTip("Quit overlay")
    style_header_button(quit_button, HOVER_RED)
    quit_button.clicked.connect(self.app.quit)
    header.addWidget(quit_button)
    layout.addLayout(header)

    self.current_mode = "2v2"
    self._highlight_mode_button()

    self.wins_label = self._stat_label("Wins: 0", WIN_COLOR)
    self.losses_label = self._stat_label("Losses: 0", LOSS_COLOR)
    self.streak_label = self._stat_label("Streak: -", STREAK_COLOR)
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

  def _highlight_mode_button(self):
    for mode, button in self.mode_buttons.items():
      button.setChecked(mode == self.current_mode)

  def select_mode(self, mode: str):
    if mode == self.current_mode:
      return
    self.current_mode = mode
    self._highlight_mode_button()
    self.refresh_stats()

  # ---------- Backend data ----------

  def reset_session(self):
      try:
          api.reset_session(self.current_mode)
          self.refresh_stats()
      except Exception:
          self.connection_error_label.show()


  def refresh_stats(self):
    try:
      stats = api.get_stats()[self.current_mode]
      self.wins_label.setText(f"Wins: {stats['wins']}")
      self.losses_label.setText(f"Losses: {stats['losses']}")
      self.streak_label.setText(f"Streak: {format_streak(stats['streak'])}")
      self.connection_error_label.hide()
    except Exception:
      # Backend down or busy - keep last known values, show a hint.
      self.connection_error_label.show()


class MatchHistoryWindow(FramelessWindow):
  """Frameless overlay listing the stored match history, newest first.

  Hidden on startup; toggled with the match history hotkey.
  """

  def __init__(self, app):
    super().__init__()
    self.app = app
    self.setWindowFlags(
      Qt.WindowType.FramelessWindowHint
      | Qt.WindowType.WindowStaysOnTopHint
      | Qt.WindowType.Tool
    )
    self.setWindowTitle("RL Overlay - Match History")
    self.setMinimumWidth(180)
    # self.setMinimumWidth(220)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(10, 8, 5, 12)
    layout.setSpacing(4)

    layout.addLayout(self.make_header("Match History"))

    # Scrollable list so 50 entries never extend past the screen. The
    # scrollbar only appears when the rows exceed the available height.
    self.rows_container = QWidget()
    self.rows_layout = QVBoxLayout(self.rows_container)
    self.rows_layout.setContentsMargins(0, 0, 0, 0)
    # Decides spacing between matches in history
    self.rows_layout.setSpacing(20)
    self.rows_layout.addStretch()  # keeps short lists at the top

    self.scroll_area = QScrollArea()
    self.scroll_area.setWidget(self.rows_container)
    self.scroll_area.setWidgetResizable(True)
    self.scroll_area.setHorizontalScrollBarPolicy(
      Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    self.scroll_area.setVerticalScrollBarPolicy(
      Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
    self.scroll_area.setStyleSheet(
      "QScrollBar:vertical { width: 8px; background: transparent; }"
      "QScrollBar::handle:vertical { background: rgba(255,255,255,60);"
      " border-radius: 4px; min-height: 24px; }"
      "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical"
      " { height: 0; }"
      "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical"
      " { background: transparent; }"
    )
    layout.addWidget(self.scroll_area)

    self.connection_error_label = QLabel("Backend unreachable")
    self.connection_error_label.setStyleSheet(f"color: {ERROR_COLOR};")
    self.connection_error_label.hide()
    layout.addWidget(self.connection_error_label)

    self.refresh()

  def place_under_session(self, margin: int = 10):
    """Default position: top-right, directly under the session overlay."""
    session = self.app.session_window
    self.adjustSize()
    # Never taller than what fits between the session window and the
    # bottom of the screen.
    screen = self.screen() or QApplication.primaryScreen()
    available_height = screen.availableGeometry().height()
    max_height = (
      available_height - session.y() - session.height() - 2 * margin
    )
    self.setFixedHeight(min(self.sizeHint().height(), max_height))
    self.move(session.x(), session.y() + session.height() + margin)

  def refresh(self):
    """Reloads the match list from the backend."""
    while self.rows_layout.count() > 1:  # last item is the trailing stretch
      item = self.rows_layout.takeAt(0)
      if item.widget():
        item.widget().deleteLater()

    try:
      history = api.get_match_history()
      self.connection_error_label.hide()
    except Exception:
      self.connection_error_label.show()
      return

    if not history:
      empty = QLabel("No matches recorded yet")
      empty.setStyleSheet("color: gray;")
      self.rows_layout.addWidget(empty)
      return

    for match in history:
      self.rows_layout.insertWidget(self.rows_layout.count() - 1,
                                    self._match_row(match))
    self._apply_visible_entry_cap(len(history))
    self.adjustSize()

  def _apply_visible_entry_cap(self, entry_count: int):
    """Sizes the scroll area to show at most VISIBLE_ENTRIES entries.

    With more entries than that the area is fixed to the measured
    height of the first N rows and the rest is reached by scrolling;
    with fewer, the area is free so the window shrinks to its content.
    """
    if entry_count <= self.VISIBLE_ENTRIES:
      # Undo any previous cap - QWIDGETSIZE_MAX is Qt's "no limit".
      self.scroll_area.setMinimumHeight(0)
      self.scroll_area.setMaximumHeight(16777215)
      return

    # Measure the real first N rows instead of guessing a per-entry
    # height - stays correct if fonts or the row layout ever change.
    widgets = [self.rows_layout.itemAt(i).widget()
               for i in range(self.VISIBLE_ENTRIES)]
    entries_height = sum(
      widget.sizeHint().height() for widget in widgets
    ) + self.rows_layout.spacing() * (self.VISIBLE_ENTRIES - 1)
    self.scroll_area.setFixedHeight(entries_height)

  # Colored W/L square - same size and spacing for every entry.
  RESULT_SQUARE_SIZE = 22
  RESULT_SPACING = 8

  # How many match entries are visible before the list scrolls.
  VISIBLE_ENTRIES = 10

  @classmethod
  def _result_square(cls, result: str) -> QLabel:
    """Medium colored square with a centered white W or L."""
    color = WIN_COLOR if result == "W" else LOSS_COLOR
    square = QLabel(result)
    square.setFixedSize(cls.RESULT_SQUARE_SIZE, cls.RESULT_SQUARE_SIZE)
    square.setAlignment(Qt.AlignmentFlag.AlignCenter)
    square.setStyleSheet(
      f"""
      QLabel {{
        background: {color};
        color: {WINDOW_BACKGROUND_COLOR};
        font-weight: bold;
        border-radius: 4px;
      }}
      """
    )
    return square

  @staticmethod
  def _format_match_time(played_at: datetime.datetime) -> str:
    """Relative labels for today/yesterday (calendar-date based),
    otherwise e.g. 'Sep 14 - 21:03'."""
    now = datetime.datetime.now().astimezone()
    match_date = played_at.date()
    time_text = f"{played_at:%H:%M}"
    if match_date == now.date():
      return f"Today \u00b7 {time_text}"
    if match_date == (now.date() - datetime.timedelta(days=1)):
      return f"Yesterday \u00b7 {time_text}"
    return f"{played_at:%b} {played_at.day} - {time_text}"

  @staticmethod
  def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {ACCENT_COLOR_MILD}")
    # line.setStyleSheet("color: rgba(255, 255, 255, 40);")  # faint white
    return line


  @classmethod
  def _match_row(cls, match: dict) -> QWidget:
    """One entry: [square] score on top, date indented below the score."""
    row = QWidget()
    row_layout = QVBoxLayout(row)
    # Right margin keeps text (e.g. the gamemode label) clear of the
    # scrollbar and the window's right edge.
    row_layout.setContentsMargins(0, 0, 4, 0)
    # row_layout.setContentsMargins(0, 0, 0, 0)
    # row_layout.setContentsMargins(0, 3, 0, 0)
    row_layout.setSpacing(2)
    # row_layout.setSpacing(4)

    result = str(match.get("result") or "")

    # First line: W/L square followed by the match score.
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    # top_row.setContentsMargins(0, 0, 0, 4)
    # top_row.setAlignment

    top_row.setSpacing(cls.RESULT_SPACING)
    top_row.addWidget(cls._result_square(result))
    # top_row.addWidget(cls._result_square(result), 0, Qt.AlignmentFlag.AlignVCenter)

    player_score = match.get("player_score")
    opponent_score = match.get("opponent_score")

    if isinstance(player_score, int) and isinstance(opponent_score, int):
      # Player's score first, opponent's second.
      score_label = QLabel(f"{player_score}-{opponent_score}")
      score_label.setStyleSheet("font-weight: bold;")
      top_row.addWidget(score_label)
    # Missing scores are simply not shown - never invented.

    # Show gamemode to the far right
    top_row.addStretch()

    gamemode = match.get("gamemode_id")
    gamemode_names = {
      10: "1v1",
      11: "2v2",
      13: "3v3",
    }

    if isinstance(gamemode, int):
      gamemode_label = QLabel(gamemode_names.get(gamemode, "Unknown"))
      gamemode_label.setStyleSheet(f"""
          color: {ACCENT_COLOR};
          font-size: 12px;
          font-weight: 500;
      """)
      top_row.addWidget(gamemode_label)
    

    row_layout.addLayout(top_row)


    # Second line: date/time, aligned under the score (not the square).
    try:
      played_at = datetime.datetime.fromisoformat(match["played_at"])
      date_text = cls._format_match_time(played_at)
    except (KeyError, ValueError, TypeError):
      date_text = str(match.get("played_at") or "Unknown time")
    date_label = QLabel(date_text)
    indent = cls.RESULT_SQUARE_SIZE + cls.RESULT_SPACING
    date_label.setContentsMargins(indent, 0, 0, 0)
    date_label.setStyleSheet("color: gray;")
    row_layout.addWidget(date_label)

    # Trying to create thin clean separator between matches in history
    # Extra breathing room between the date and the line (row spacing is 2).
    # row_layout.addSpacing(6)
    row_layout.addSpacing(4)
    row_layout.addWidget(cls._separator())

    return row


class SettingsWindow(FramelessWindow):
  """Frameless settings window, styled like the session overlay."""

  def __init__(self, app):
    super().__init__()
    self.app = app
    self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    self.setWindowTitle("RL Overlay - Settings")
    # Set width of settings window
    # self.setMinimumWidth(330)
    self.setMinimumWidth(230)

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
    self.user_id_input.setPlaceholderText("SteamID / Epic Account ID")
    form.addRow("ID", self.user_id_input)

    outer.addWidget(id_group)
    button_row = QHBoxLayout()
    save_button = QPushButton("Save Settings")
    save_button.clicked.connect(self.on_save_settings)
    button_row.addWidget(save_button)
    self.settings_status_label = QLabel("")
    self.settings_status_label.setStyleSheet(f"color: {STATUS_OK_COLOR};")
    button_row.addWidget(self.settings_status_label)
    button_row.addStretch()
    outer.addLayout(button_row)



    ui_group = QGroupBox("Overlay")
    ui_form = QFormLayout(ui_group)
    self.hotkey_combo = QComboBox()
    self.hotkey_combo.addItems(HOTKEY_CHOICES)
    self.hotkey_combo.setCurrentText(app.hotkey)
    # Apply immediately when a new key is chosen.
    self.hotkey_combo.currentTextChanged.connect(app.set_hotkey)
    ui_form.addRow("Open settings hotkey", self.hotkey_combo)

    self.history_hotkey_combo = QComboBox()
    self.history_hotkey_combo.addItems(HOTKEY_CHOICES)
    self.history_hotkey_combo.setCurrentText(
      app.history_hotkey or DEFAULT_HISTORY_HOTKEY
    )
    self.history_hotkey_combo.currentTextChanged.connect(
      app.set_history_hotkey
    )
    ui_form.addRow("Match history hotkey", self.history_hotkey_combo)
    outer.addWidget(ui_group)

    # button_row = QHBoxLayout()
    # save_button = QPushButton("Save Settings")
    # save_button.clicked.connect(self.on_save_settings)
    # button_row.addWidget(save_button)
    # self.settings_status_label = QLabel("")
    # self.settings_status_label.setStyleSheet(f"color: {STATUS_OK_COLOR};")
    # button_row.addWidget(self.settings_status_label)
    # button_row.addStretch()
    # outer.addLayout(button_row)


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
      self.history_hotkey_combo.setCurrentText(
        settings.get("history_hotkey") or DEFAULT_HISTORY_HOTKEY
      )
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

    # Hotkeys come from the backend settings (DB); fall back to the defaults
    # when the backend is offline on startup.
    self.hotkey = DEFAULT_HOTKEY
    self.history_hotkey = DEFAULT_HISTORY_HOTKEY
    try:
      settings = api.get_settings()
      self.hotkey = settings.get("hotkey") or DEFAULT_HOTKEY
      self.history_hotkey = settings.get("history_hotkey") or DEFAULT_HISTORY_HOTKEY
    except Exception:
      pass

    self.session_window = SessionWindow(self)
    self.history_window = MatchHistoryWindow(self)
    self.history_window.place_under_session()
    self.settings_window = None  # created lazily on first open

    self.poll_timer = QTimer()
    self.poll_timer.setInterval(STATS_POLL_MS)
    self.poll_timer.timeout.connect(self.session_window.refresh_stats)
    self.poll_timer.start()
    self.session_window.refresh_stats()

    if not hotkey.register(self.hotkey, hotkey.HOTKEY_ID_SETTINGS):
      print(f"Warning: hotkey {self.hotkey} is already in use by another app.")
    if self.history_hotkey != self.hotkey and not hotkey.register(
      self.history_hotkey, hotkey.HOTKEY_ID_HISTORY
    ):
      print(
        f"Warning: hotkey {self.history_hotkey} is already in use "
        "by another app."
      )
    self.hotkey_filter = hotkey.HotkeyFilter(self.on_hotkey)
    self.qt_app.installNativeEventFilter(self.hotkey_filter)

  def on_hotkey(self, hotkey_id: int):
    """Dispatches a fired hotkey by its id."""
    if hotkey_id == hotkey.HOTKEY_ID_SETTINGS:
      self.show_settings()
    elif hotkey_id == hotkey.HOTKEY_ID_HISTORY:
      self.toggle_history()

  def toggle_history(self):
    """Shows or hides the match history window."""
    if self.history_window.isVisible():
      self.history_window.hide()
      return
    self.history_window.refresh()
    self.history_window.place_under_session()
    self.history_window.show()
    self.history_window.raise_()

  def show_settings(self):
    if self.settings_window is None:
      self.settings_window = SettingsWindow(self)
      self.settings_window.load_settings()
    self.settings_window.show()
    self.settings_window.raise_()
    self.settings_window.activateWindow()

  def _reassign_hotkey(self, key, hotkey_id, current_key, save_func,
                       success_text, combo, in_use_text):
    """Re-registers one hotkey slot; shared by both hotkey settings.

    current_key is a one-element list so the accepted key can be
    read back by the caller.
    """
    try:
      hotkey.unregister(hotkey_id)
    except Exception:
      pass
    if hotkey.register(key, hotkey_id):
      current_key[0] = key
      try:
        save_func(key)
      except Exception:
        if self.settings_window:
          self.settings_window._set_status(
            "Could not reach backend - hotkey not saved!", error=True
          )
          return
      if self.settings_window:
        self.settings_window._set_status(success_text)
      return
    if key == current_key[0]:
      hotkey.register(key, hotkey_id)  # re-register old key after unregister
      return
    # New key taken by another app - fall back to the old one.
    hotkey.register(current_key[0], hotkey_id)
    if self.settings_window:
      combo.setCurrentText(current_key[0])
      self.settings_window._set_status(
        in_use_text.format(key=key), error=True
      )

  def set_hotkey(self, key: str):
    """Called when the user picks a new settings hotkey in the settings window."""
    if key == self.history_hotkey:
      # Revert the combo - the match history hotkey already uses this key.
      if self.settings_window:
        self.settings_window.hotkey_combo.setCurrentText(self.hotkey)
        self.settings_window._set_status(
          f"'{key}' is already used by the match history hotkey!", error=True
        )
      return
    current = [self.hotkey]
    self._reassign_hotkey(
      key, hotkey.HOTKEY_ID_SETTINGS, current,
      api.update_settings_hotkey, "Hotkey updated!",
      self.settings_window.hotkey_combo if self.settings_window else None,
      "'{key}' is already in use by another app!",
    )
    self.hotkey = current[0]

  def set_history_hotkey(self, key: str):
    """Called when the user picks a new match history hotkey."""
    if key == self.hotkey:
      if self.settings_window:
        self.settings_window.history_hotkey_combo.setCurrentText(
          self.history_hotkey
        )
        self.settings_window._set_status(
          f"'{key}' is already used by the settings hotkey!", error=True
        )
      return
    current = [self.history_hotkey]
    self._reassign_hotkey(
      key, hotkey.HOTKEY_ID_HISTORY, current,
      api.update_settings_history_hotkey, "Match history hotkey updated!",
      self.settings_window.history_hotkey_combo if self.settings_window else None,
      "'{key}' is already in use by another app!",
    )
    self.history_hotkey = current[0]

  def quit(self):
    hotkey.unregister(hotkey.HOTKEY_ID_SETTINGS)
    hotkey.unregister(hotkey.HOTKEY_ID_HISTORY)
    self.qt_app.quit()


def run():
  app = QApplication(sys.argv)
  # The session overlay is a Qt.Tool window, which Qt does not count as a
  # "main window" - so we control quitting ourselves via the X button.
  app.setQuitOnLastWindowClosed(False)
  # Dark palette so the overlay fits Rocket League's look.
  app.setStyle("Fusion")
  palette = QPalette()
  palette.setColor(QPalette.ColorRole.Window, QColor(WINDOW_BACKGROUND_COLOR))
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
