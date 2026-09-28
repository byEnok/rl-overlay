import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from backend.tracker import main as tracker_main
from backend.database import (
  initialize_database, get_settings, update_settings, update_settings_hotkey,
  update_settings_history_hotkey, get_session_stats, reset_session,
  get_match_history, TRACKED_PLAYLISTS
)

def _on_tracker_done(task: asyncio.Task):
  """Warn loudly if the tracker task dies unexpectedly.

  A crashed asyncio task just disappears silently - this makes sure
  a bug in the tracker is visible in the backend output.
  """
  if task.cancelled():
    return  # normal shutdown via cancel()
  exc = task.exception()
  if exc is not None:
    print(f"!!! TRACKER CRASHED: {type(exc).__name__}: {exc}")
    print("!!! Match tracking is NOT running - restart the backend!")
  else:
    print("Tracker stopped unexpectedly (no error). Match tracking is NOT running!")


@asynccontextmanager
async def lifespan(app: FastAPI):
  initialize_database()

  tracker_task = asyncio.create_task(tracker_main())
  tracker_task.add_done_callback(_on_tracker_done)

  yield

  tracker_task.cancel()

  try:
    await tracker_task
  except asyncio.CancelledError:
    pass

class Settings(BaseModel):
  user_name: str | None = None
  launcher: str
  user_id: str
  hotkey: str | None = None  # frontend UI preference - key that opens settings
  history_hotkey: str | None = None  # key that toggles the match history window

class HotkeyUpdate(BaseModel):
  hotkey: str


app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
  return {"message": "Rocket League Overlay API is running!" }

@app.get("/settings")
def settings():
  user_name, launcher, user_id, hotkey, history_hotkey = get_settings()

  return {
    "user_name": user_name,
    "launcher": launcher,
    "user_id": user_id,
    "hotkey": hotkey,
    "history_hotkey": history_hotkey
  }

@app.post("/settings")
def update_user_settings(settings: Settings):
  full_user_id = f"{settings.launcher}|{settings.user_id}|0"

  # Keep the stored hotkeys when the request doesn't include one.
  stored = get_settings()
  hotkey = settings.hotkey if settings.hotkey is not None else stored[3]
  history_hotkey = (
    settings.history_hotkey if settings.history_hotkey is not None else stored[4]
  )

  update_settings(
    settings.user_name or "",
    settings.launcher,
    full_user_id,
    hotkey,
    history_hotkey,
  )

  return {
    "message": "Settings updated!"
  }

# SAVES ONLY THE HOTKEY - USED BY THE FRONTEND UI PREFERENCE
@app.patch("/settings/hotkey")
def update_hotkey(payload: HotkeyUpdate):
  update_settings_hotkey(payload.hotkey)

  return {
    "message": "Hotkey updated!"
  }

# SAVES ONLY THE MATCH HISTORY HOTKEY - USED BY THE FRONTEND UI PREFERENCE
@app.patch("/settings/history_hotkey")
def update_history_hotkey(payload: HotkeyUpdate):
  update_settings_history_hotkey(payload.hotkey)

  return {
    "message": "Match history hotkey updated!"
  }

# GETS THE MATCH HISTORY (NEWEST FIRST) - max 50 games
@app.get("/history")
def history():
  return [
    {
      "result": result,
      "played_at": played_at,
      "player_score": player_score,
      "opponent_score": opponent_score,
      "gamemode_id": gamemode_id
    }
    for result, played_at, player_score, opponent_score, gamemode_id in get_match_history()
  ]

# GETS THE CURRENT SESSION STATS (PER GAMEMODE)
@app.get("/stats")
def stats():
  return {
    mode: {
      "wins": wins,
      "losses": losses,
      "streak": streak
    }
    for mode, (wins, losses, streak) in (
      (mode, get_session_stats(mode)) for mode in TRACKED_PLAYLISTS
    )
  }

# RESETS ONE GAMEMODE'S SESSION STATS
@app.post("/session/reset")
def session_reset(mode: str):
  reset_session(mode)

  return {
    "message": f"{mode} session reset!"
  }

