import asyncio

from rlstatsapi import StatsClient
from backend.database import get_settings, record_match, TRACKED_PLAYLISTS


# PlaylistId (int) -> gamemode name ("1v1" etc.) for quick lookup
PLAYLIST_NAMES = {
    playlist_id: name for name, playlist_id in TRACKED_PLAYLISTS.items()
}

my_team = None
current_playlist = None


def find_playlist_id(data):
    """Finds the first 'PlaylistId' value anywhere in the event payload.

    The exact location depends on the message shape, so we search
    recursively instead of hardcoding a path.
    Returns the PlaylistId (int) or None.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "PlaylistId" and isinstance(value, int):
                return value
            found = find_playlist_id(value)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_playlist_id(item)
            if found is not None:
                return found
    return None

async def main():
    global my_team, current_playlist

    user_name, launcher, user_id, _hotkey = get_settings()

    async with StatsClient() as client:
        async for message in client.events(
            "UpdateState",
            "MatchEnded"
        ):
            # print(message.data)
            if message.event == "UpdateState":


                players = message.data["Players"]

                for player in players:
                  if player["PrimaryId"] != user_id:
                    continue

                  if user_name and player["Name"] != user_name:
                    continue

                  my_team = player["TeamNum"]
                  break

                playlist_id = find_playlist_id(message.data)
                if playlist_id in PLAYLIST_NAMES:
                    current_playlist = PLAYLIST_NAMES[playlist_id]
                else:
                    # Not one of the tracked gamemodes (e.g. casual, dropshot)
                    current_playlist = None

            elif message.event == "MatchEnded":
                winner_team = message.data["WinnerTeamNum"]

                result = "W" if my_team == winner_team else "L"

                if current_playlist is not None:
                    record_match(current_playlist, result)
                    print(f"{result} in {current_playlist}!")
                else:
                    print(f"{result} - gamemode not tracked, not recorded.")

                my_team = None
                current_playlist = None

