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
            played_at TEXT NOT NULL,
            player_score INTEGER,
            opponent_score INTEGER
            )
        """)

# ADD SCORE COLUMNS TO DATABASES CREATED BEFORE THEY EXISTED (NULLABLE -
# OLD ROWS SIMPLY HAVE NO SCORE, WHICH THE UI HANDLES)
  match_columns = connection.execute(
    "PRAGMA table_info(matches)"
  ).fetchall()
  match_column_names = [column[1] for column in match_columns]
  if "player_score" not in match_column_names:
    connection.execute("ALTER TABLE matches ADD COLUMN player_score INTEGER")
  if "opponent_score" not in match_column_names:
    connection.execute("ALTER TABLE matches ADD COLUMN opponent_score INTEGER")

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

# ADD HISTORY HOTKEY COLUMN TO EXISTING DATABASES CREATED BEFORE IT EXISTED
  if "history_hotkey" not in [column[1] for column in existing_columns]:
    connection.execute(
      "ALTER TABLE settings ADD COLUMN history_hotkey TEXT NOT NULL DEFAULT 'F9'"
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
# RETURNS (user_name, launcher, user_id, hotkey, history_hotkey)
def get_settings():
  connection = sqlite3.connect(DATABASE)

  settings = connection.execute(
    "SELECT user_name, launcher, user_id, hotkey, history_hotkey "
    "FROM settings WHERE id = 1"
  ).fetchone()

  connection.close()

  return settings


# UPDATES SETTINGS WITHOUT TOUCHING EITHER HOTKEY (FULL SETTINGS SAVE)
def update_settings(user_name, launcher, user_id,
                    hotkey, history_hotkey):
  connection = sqlite3.connect(DATABASE)

  connection.execute(
    """
    UPDATE settings
    SET user_name = ?, launcher = ?, user_id = ?, hotkey = ?, history_hotkey = ?
    WHERE id = 1
    """,
    (user_name, launcher, user_id, hotkey, history_hotkey)
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


# UPDATES ONLY THE MATCH HISTORY HOTKEY (FRONTEND UI PREFERENCE)
def update_settings_history_hotkey(hotkey):
  connection = sqlite3.connect(DATABASE)

  connection.execute(
    "UPDATE settings SET history_hotkey = ? WHERE id = 1",
    (hotkey,)
  )

  connection.commit()
  connection.close()


# SAVES MATCH RESULT FOR MATCH HISTORY VIEWING
# SCORES MAY BE None WHEN THE API DID NOT PROVIDE THEM - NEVER INVENTED
def save_match(result, player_score, opponent_score):
  connection = sqlite3.connect(DATABASE)
  played_at = datetime.now().astimezone().isoformat()

  connection.execute(
    "INSERT INTO matches (result, played_at, player_score, opponent_score) "
    "VALUES (?, ?, ?, ?)",
    (result, played_at, player_score, opponent_score)
    )

  connection.commit()
  connection.close()


# GETS THE MATCH HISTORY, NEWEST FIRST - USED FOR THE HISTORY WINDOW
MAX_HISTORY = 50

def get_match_history():
  connection = sqlite3.connect(DATABASE)

  rows = connection.execute(
    "SELECT result, played_at, player_score, opponent_score FROM matches "
    "ORDER BY id DESC LIMIT ?",
    (MAX_HISTORY,)
  ).fetchall()

  connection.close()

  return rows


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
def record_match(playlist, result, player_score=None, opponent_score=None):
  wins, losses, streak = get_session_stats(playlist)

  if result == "W":
    wins += 1
    streak += 1

  elif result == "L":
    losses += 1
    streak = 0

  save_match(result, player_score, opponent_score)
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


