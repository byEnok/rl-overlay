import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from backend.tracker import main as tracker_main
from backend.database import initialize_database, get_settings, update_settings, get_session_stats, reset_session

@asynccontextmanager
async def lifespan(app: FastAPI):
  initialize_database()

  tracker_task = asyncio.create_task(tracker_main())

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


app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
  return {"message": "Rocket League Overlay API is running!" }

@app.get("/settings")
def settings():
  user_name, launcher, user_id = get_settings()

  return {
    "user_name": user_name,
    "launcher": launcher,
    "user_id": user_id
  }

@app.post("/settings")
def update_user_settings(settings: Settings):
  full_user_id = f"{settings.launcher}|{settings.user_id}|0"

  update_settings(settings.user_name or "", settings.launcher, full_user_id)

  return {
    "message": "Settings updated!"
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

