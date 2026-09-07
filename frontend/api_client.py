"""HTTP client for talking to the backend.

The frontend must never touch SQLite directly - all data flows
through the backend API (see AGENTS.md).
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 3.0  # seconds; backend is local, this should never come close


def get_settings() -> dict:
  """Returns {'user_name': str, 'launcher': str, 'user_id': str} or raises."""
  response = httpx.get(f"{BASE_URL}/settings", timeout=TIMEOUT)
  response.raise_for_status()
  return response.json()


def update_settings(user_name: str, launcher: str, user_id: str) -> None:
  """Sends new settings to the backend."""
  response = httpx.post(
    f"{BASE_URL}/settings",
    json={"user_name": user_name, "launcher": launcher, "user_id": user_id},
    timeout=TIMEOUT,
  )
  response.raise_for_status()


def get_stats() -> dict:
  """Returns {'wins': int, 'losses': int, 'streak': int} or raises."""
  response = httpx.get(f"{BASE_URL}/stats", timeout=TIMEOUT)
  response.raise_for_status()
  return response.json()


def reset_session() -> None:
  """Resets the current session W/L and streak (history is kept)."""
  response = httpx.post(f"{BASE_URL}/session/reset", timeout=TIMEOUT)
  response.raise_for_status()
