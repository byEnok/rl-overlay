import sqlite3
from datetime import datetime

DATABASE = "overlay.db"

# GAMEMODES WE TRACK (API PlaylistId)
TRACKED_PLAYLISTS = {"1v1": 10, "2v2": 11, "3v3": 13}

# CREATES THE DATABASE TABLES IF THEY DON'T EXIST
def initialize_database():
  connection = sqlite3.connect(DATABASE)

# CREATE MATCH HISTORY TABLE
  connection.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result TEXT NOT NULL,
            played_at TEXT NOT NULL
            )
        """)

# CREATE SESSION STATS TABLE - ONE ROW PER GAMEMODE
# (old schema had a single row with id=1; dev-era data is dropped)
  old_columns = connection.execute(
    "PRAGMA table_info(session_stats)"
  ).fetchall()
  if "id" in [column[1] for column in old_columns]:
    connection.execute("DROP TABLE session_stats")

  connection.execute("""
        CREATE TABLE IF NOT EXISTS session_stats (
            playlist TEXT PRIMARY KEY,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0
            )
        """)

# CREATE USER NAME AND USER ID TABLE
  connection.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            user_name TEXT NOT NULL DEFAULT '',
            launcher TEXT NOT NULL DEFAULT 'Steam',
            user_id TEXT NOT NULL DEFAULT '',
            hotkey TEXT NOT NULL DEFAULT 'F8'
            )
        """)

# ADD HOTKEY COLUMN TO EXISTING DATABASES CREATED BEFORE IT EXISTED
  existing_columns = connection.execute(
    "PRAGMA table_info(settings)"
  ).fetchall()
  if "hotkey" not in [column[1] for column in existing_columns]:
    connection.execute(
      "ALTER TABLE settings ADD COLUMN hotkey TEXT NOT NULL DEFAULT 'F8'"
    )

# KEEP USER INFO AFTER APP SHUTDOWN
  connection.execute("""
        INSERT OR IGNORE INTO settings (id)
        VALUES (1)
  """)

# KEEP SESSION STATS AFTER APP SHUTDOWN (ONE SEED ROW PER GAMEMODE)
  for playlist in TRACKED_PLAYLISTS:
    connection.execute(
      "INSERT OR IGNORE INTO session_stats (playlist) VALUES (?)",
      (playlist,)
    )

  connection.commit()
  connection.close()


# GETS THE SAVED USER NAME AND USER ID
# RETURNS (user_name, launcher, user_id, hotkey)
def get_settings():
  connection = sqlite3.connect(DATABASE)

  settings = connection.execute(
    "SELECT user_name, launcher, user_id, hotkey FROM settings WHERE id = 1"
  ).fetchone()

  connection.close()

  return settings


# UPDATES THE SAVED USER NAME, LAUNCHER, USER ID AND HOTKEY
def update_settings(user_name, launcher, user_id, hotkey):
  connection = sqlite3.connect(DATABASE)

  connection.execute(
    """
    UPDATE settings
    SET user_name = ?, launcher = ?, user_id = ?, hotkey = ?
    WHERE id = 1
    """,
    (user_name, launcher, user_id, hotkey)
  )

  connection.commit()
  connection.close()


# UPDATES ONLY THE SAVED HOTKEY (FRONTEND UI PREFERENCE)
def update_settings_hotkey(hotkey):
  connection = sqlite3.connect(DATABASE)

  connection.execute(
    "UPDATE settings SET hotkey = ? WHERE id = 1",
    (hotkey,)
  )

  connection.commit()
  connection.close()


# SAVES MATCH RESULT FOR MATCH HISTOR VIEWING
def save_match(result):
  connection = sqlite3.connect(DATABASE)
  played_at = datetime.now().astimezone().isoformat()

  connection.execute(
    "INSERT INTO matches (result, played_at) VALUES (?, ?)",
    (result, played_at)
    )

  connection.commit()
  connection.close()


# GETS THE CURRENT SESSION W/L AND WIN STREAK FOR ONE GAMEMODE
def get_session_stats(playlist):
  connection = sqlite3.connect(DATABASE)
  stats = connection.execute(
    "SELECT wins, losses, streak FROM session_stats WHERE playlist = ?",
    (playlist,)
  ).fetchone()

  connection.close()

  return stats


# UPDATES THE CURRENT SESSION W/L AND WIN STREAK FOR ONE GAMEMODE
def update_session_stats(playlist, wins, losses, streak):
  connection = sqlite3.connect(DATABASE)

  connection.execute(
    """
    UPDATE session_stats
    SET wins = ?, losses = ?, streak = ?
    WHERE playlist = ?
    """,
    (wins, losses, streak, playlist)
  )

  connection.commit()
  connection.close()


# RECORDS A MATCH AND UPDATES THE CURRENT SESSION FOR ONE GAMEMODE
def record_match(playlist, result):
  wins, losses, streak = get_session_stats(playlist)

  if result == "W":
    wins += 1
    streak += 1

  elif result == "L":
    losses += 1
    streak = 0

  save_match(result)
  update_session_stats(playlist, wins, losses, streak)


# RESETS ONE GAMEMODE'S SESSION WITHOUT DELETING MATCH HISTORY
def reset_session(playlist):
  connection = sqlite3.connect(DATABASE)

  connection.execute(
    """
    UPDATE session_stats
    SET wins = 0, losses = 0, streak = 0
    WHERE playlist = ?
    """,
    (playlist,)
  )

  connection.commit()
  connection.close()


