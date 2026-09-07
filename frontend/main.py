"""Rocket League Overlay - Dear PyGui frontend.

Talks to the backend only through frontend/api_client.py.
Never touches SQLite directly.
"""

import dearpygui.dearpygui as dpg

import frontend.api_client as api

STATS_POLL_FRAMES = 120  # ~2s at 60 fps

LAUNCHERS = ["Steam", "Epic"]


def on_stats_poll():
  """Called periodically from the render loop to refresh stats."""
  try:
    stats = api.get_stats()
    streak = stats["streak"]
    streak_text = f"{abs(streak)}W" if streak >= 0 else f"{abs(streak)}L"
    if streak == 0:
      streak_text = "-"
    dpg.configure_item("wins_text", default_value=f"Wins: {stats['wins']}")
    dpg.configure_item("losses_text", default_value=f"Losses: {stats['losses']}")
    dpg.configure_item("streak_text", default_value=f"Streak: {streak_text}")
    dpg.hide_item("connection_error_text")
  except Exception:
    # Backend down or busy - keep last known values, show a hint.
    dpg.show_item("connection_error_text")


def on_save_settings():
  user_name = dpg.get_value("user_name_input")
  launcher = dpg.get_value("launcher_combo")
  user_id = dpg.get_value("user_id_input").strip()

  if not user_id:
    dpg.set_value("settings_status_text", "User ID is required!")
    return

  try:
    api.update_settings(user_name, launcher, user_id)
    dpg.set_value("settings_status_text", "Settings saved!")
  except Exception:
    dpg.set_value("settings_status_text", "Could not reach backend!")


def on_reset_session():
  try:
    api.reset_session()
    on_stats_poll()  # refresh immediately instead of waiting for the next poll
  except Exception:
    dpg.set_value("settings_status_text", "Could not reach backend!")


def load_settings_into_ui():
  """Pre-fills the settings window with values from the backend."""
  try:
    settings = api.get_settings()
    dpg.set_value("user_name_input", settings["user_name"] or "")
    dpg.set_value("launcher_combo", settings["launcher"] or LAUNCHERS[0])
    # user_id is stored as "launcher|id|0" - show only the raw id part.
    user_id = settings["user_id"] or ""
    dpg.set_value("user_id_input", user_id.split("|")[1] if "|" in user_id else user_id)
  except Exception:
    dpg.set_value("settings_status_text", "Backend offline - start it first!")


def build_ui():
  dpg.create_context()
  # dpg.create_viewport(title="RL Overlay", width=320, height=420, decorated=True)
  dpg.create_viewport(title="RL Overlay", width=30, height=50, decorated=True)

  dpg.add_window(tag="main_window")
  # dpg.add_window(tag="main_window", width=100, height=50, no_title_bar=True)

  dpg.add_text("Session", color=(77, 184, 255), parent="main_window")
  dpg.add_text("Wins: 0", color=(80, 220, 100), tag="wins_text", parent="main_window")
  dpg.add_text("Losses: 0", color=(255, 80, 80), tag="losses_text", parent="main_window")
  dpg.add_text("Streak: -", color=(255, 200, 80), tag="streak_text", parent="main_window")
  dpg.add_text("Backend unreachable", tag="connection_error_text",
               color=(255, 80, 80), show=False, parent="main_window")
  dpg.add_spacer(parent="main_window")
  dpg.add_button(label="Reset Session", callback=on_reset_session,
                 parent="main_window")
  # dpg.add_spacer(parent="main_window")
  # dpg.add_separator(parent="main_window")
  # dpg.add_spacer(parent="main_window")

  # dpg.add_text("Settings", color=(77, 184, 255), parent="main_window")

  # dpg.add_group(tag="name_group", horizontal=True, parent="main_window")
  # dpg.add_text("Name", parent="name_group")
  # dpg.add_input_text(tag="user_name_input", width=220, parent="name_group")

  # dpg.add_group(tag="launcher_group", horizontal=True, parent="main_window")
  # dpg.add_text("Launcher", parent="launcher_group")
  # dpg.add_combo(LAUNCHERS, tag="launcher_combo", default_value=LAUNCHERS[0],
  #               width=220, parent="launcher_group")

  # dpg.add_group(tag="id_group", horizontal=True, parent="main_window")
  # dpg.add_text("ID", parent="id_group")
  # dpg.add_input_text(tag="user_id_input", width=220,
  #                    hint="SteamID3 / Epic Account ID", parent="id_group")

  # dpg.add_spacer(parent="main_window")
  # dpg.add_group(tag="save_group", horizontal=True, parent="main_window")
  # dpg.add_button(label="Save Settings", callback=on_save_settings,
  #                parent="save_group")
  # dpg.add_text("", tag="settings_status_text", color=(150, 220, 150),
  #              parent="save_group")

  dpg.set_primary_window("main_window", True)


def run():
  build_ui()
  dpg.setup_dearpygui()
  dpg.show_viewport()
  # load_settings_into_ui()

  frame_count = 0
  while dpg.is_dearpygui_running():
    frame_count += 1
    if frame_count % STATS_POLL_FRAMES == 0:
      on_stats_poll()
    dpg.render_dearpygui_frame()

  dpg.destroy_context()


if __name__ == "__main__":
  run()
