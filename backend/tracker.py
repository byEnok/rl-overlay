import asyncio

from rlstatsapi import StatsClient
from backend.database import get_settings, record_match


my_team = None

async def main():
    global my_team

    user_name, launcher, user_id = get_settings()

    async with StatsClient() as client:
        async for message in client.events(
            "UpdateState",
            "MatchEnded"
        ):
            if message.event == "UpdateState":

                # print("UpdateState received")
                players = message.data["Players"]

                for player in players:
                  if player["PrimaryId"] != user_id:
                    continue

                  if user_name and player["Name"] != user_name:
                    continue

                  my_team = player["TeamNum"]
                  break

            elif message.event == "MatchEnded":
                winner_team = message.data["WinnerTeamNum"]

                if my_team == winner_team:
                    record_match("W")
                    print("WIN!")
                else:
                    record_match("L")
                    print("LOSS!")

                my_team = None

