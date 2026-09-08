import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from backend.tracker import main as tracker_main
from backend.database import initialize_database, get_settings, update_settings, update_settings_hotkey, get_session_stats, reset_session

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

class HotkeyUpdate(BaseModel):
  hotkey: str


app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
  return {"message": "Rocket League Overlay API is running!" }

@app.get("/settings")
def settings():
  user_name, launcher, user_id, hotkey = get_settings()

  return {
    "user_name": user_name,
    "launcher": launcher,
    "user_id": user_id,
    "hotkey": hotkey
  }

@app.post("/settings")
def update_user_settings(settings: Settings):
  full_user_id = f"{settings.launcher}|{settings.user_id}|0"

  # Keep the stored hotkey when the request doesn't include one.
  hotkey = settings.hotkey
  if hotkey is None:
    hotkey = get_settings()[3]

  update_settings(
    settings.user_name or "",
    settings.launcher,
    full_user_id,
    hotkey,
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

# GETS THE CURRENT SESSION STATS
@app.get("/stats")
def stats():
  wins, losses, streak = get_session_stats()

  return {
    "wins": wins,
    "losses": losses,
    "streak": streak
  }

# RESETS THE CURRENT SESSION STATS
@app.post("/session/reset")
def session_reset():
  reset_session()

  return {
    "message": "Session reset!"
  }

