import asyncio

from rlstatsapi import StatsClient
from backend.database import get_settings, record_match, TRACKED_PLAYLISTS


# PlaylistId (int) -> gamemode name ("1v1" etc.) for quick lookup
PLAYLIST_NAMES = {
    playlist_id: name for name, playlist_id in TRACKED_PLAYLISTS.items()
}

my_team = None
current_playlist = None
# Last known team scores from UpdateState (Game.Teams).
# None means unknown - e.g. malformed payloads or pre-feature history rows.
my_team_score = None
opp_team_score = None


def extract_team_scores(data, team_num):
    """Finds (player_team_score, opponent_team_score) in an UpdateState payload.

    Scores come from Game.Teams entries ({TeamNum, Score, ...}). Returns
    (None, None) when the payload is malformed or the player's team has
    no score yet - callers must not display invented values.
    """
    try:
        teams = data["Game"]["Teams"]
        player_score = None
        opponent_score = None
        for team in teams:
            if team.get("TeamNum") == team_num:
                player_score = team.get("Score")
            else:
                opponent_score = team.get("Score")
        if not isinstance(player_score, int):
            player_score = None
        if not isinstance(opponent_score, int):
            opponent_score = None
        return player_score, opponent_score
    except (KeyError, TypeError, AttributeError):
        return None, None


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
    global my_team, current_playlist, my_team_score, opp_team_score

    user_name, launcher, user_id, *_ = get_settings()

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

                if my_team is not None:
                    my_team_score, opp_team_score = extract_team_scores(
                        message.data, my_team
                    )

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
                    record_match(current_playlist, result,
                                 my_team_score, opp_team_score)
                    print(f"{result} {my_team_score}-{opp_team_score} "
                          f"in {current_playlist}!")
                else:
                    print(f"{result} - gamemode not tracked, not recorded.")

                my_team = None
                current_playlist = None
                my_team_score = None
                opp_team_score = None

