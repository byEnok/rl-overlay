"""Global hotkey support for Windows.

Uses RegisterHotKey so the hotkey works even when Rocket League
(or any other app) has focus - QShortcut would only work while our
own window is focused.
"""

import ctypes
import ctypes.wintypes as wt

from PySide6.QtCore import QAbstractNativeEventFilter

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004

# F1-F12 virtual key codes (0x70-0x7B)
VK_FKEYS = {f"F{i}": 0x70 + i - 1 for i in range(1, 13)}

HOTKEY_ID = 1  # id within our application - only one hotkey needed

_user32 = ctypes.windll.user32


def _modifiers_value(modifiers: list[str]) -> int:
  value = 0
  if "Ctrl" in modifiers:
    value |= MOD_CONTROL
  if "Alt" in modifiers:
    value |= MOD_ALT
  if "Shift" in modifiers:
    value |= MOD_SHIFT
  return value


def register(hotkey: str, modifiers: list[str] | None = None) -> bool:
  """Registers e.g. 'F8' or 'Ctrl+F8'. Returns False if already taken."""
  key = hotkey.upper()
  if key not in VK_FKEYS:
    return False
  if not _user32.RegisterHotKey(
    None, HOTKEY_ID, _modifiers_value(modifiers or []), VK_FKEYS[key]
  ):
    return False
  return True


def unregister() -> None:
  _user32.UnregisterHotKey(None, HOTKEY_ID)


class HotkeyFilter(QAbstractNativeEventFilter):
  """Qt native event filter that turns WM_HOTKEY messages into a callback."""

  def __init__(self, on_hotkey):
    super().__init__()
    self.on_hotkey = on_hotkey

  def nativeEventFilter(self, event_type, message):  # noqa: N802 (Qt naming)
    if event_type == b"windows_generic_MSG":
      msg = wt.MSG.from_address(int(message))
      if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
        self.on_hotkey()
    return False, 0
