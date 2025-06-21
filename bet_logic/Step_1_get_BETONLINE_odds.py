import requests
import pandas as pd
import time
import os
import json

API_KEY = "3550559967b78da8856f5c4192697b32"
SPORT = "baseball_mlb"
ODDS_FORMAT = "american"
DATE_FORMAT = "iso"
REGION = "us"
BOOKMAKER_FILTER = ""

# === Market groups ===
PITCHER_MARKETS = ["pitcher_strikeouts"]
BATTER_MARKETS = ["batter_hits", "batter_home_runs"]  # Add more if needed
TEAM_MARKETS = ["totals", "spreads", "h2h"]  # h2h = moneyline

ALL_MARKETS = PITCHER_MARKETS + BATTER_MARKETS + TEAM_MARKETS

# === Step 1: Fetch all MLB events ===
events_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
params = {
    "apiKey": API_KEY,
    "dateFormat": DATE_FORMAT
}
print("--- Fetching MLB events ---")
resp = requests.get(events_url, params=params)
if resp.status_code != 200:
    raise Exception(f" Events error: {resp.status_code} - {resp.text}")

events = resp.json()
print(f" Found {len(events)} events")

# === Containers for props ===
pitcher_rows = []
batter_rows = []
team_rows = []

# === Step 2: Loop through events and collect odds ===
for event in events:
    event_id = event.get("id")
    home = event.get("home_team")
    away = event.get("away_team")
    game_time = event.get("commence_time")

    print(f"\n {away} @ {home} | {game_time}")

    odds_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"
    odds_params = {
        "apiKey": API_KEY,
        "markets": ",".join(ALL_MARKETS),
        "regions": REGION,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": DATE_FORMAT
    }

    odds_resp = requests.get(odds_url, params=odds_params)
    if odds_resp.status_code != 200:
        print(f" Odds error: {odds_resp.status_code} - {odds_resp.text}")
        continue

    event_odds = odds_resp.json()

    for bookmaker in event_odds.get("bookmakers", []):
        #ALLOWED_BOOKS = {"BetOnline.ag", "DraftKings", "FanDuel", "PointsBet (US)"}
        #if bookmaker.get("title") not in ALLOWED_BOOKS:
        #    continue


        for market in bookmaker.get("markets", []):
            market_key = market.get("key")
            for outcome in market.get("outcomes", []):
                row = {
                    "event_id": event_id,
                    "home_team": home,
                    "away_team": away,
                    "commence_time": game_time,
                    "bookmaker": bookmaker.get("title"),
                    "last_update": market.get("last_update"),
                    "market": market_key,
                    "participant": outcome.get("participant"),
                    "description": outcome.get("description"),
                    "raw_name": outcome.get("name"),
                    "line": outcome.get("point"),
                    "odds": outcome.get("price")
                }

                if market_key in PITCHER_MARKETS:
                    pitcher_rows.append(row)
                elif market_key in BATTER_MARKETS:
                    batter_rows.append(row)
                elif market_key in TEAM_MARKETS:
                    team_rows.append(row)

    time.sleep(1)

# === Save to separate files ===
os.makedirs("data", exist_ok=True)

if pitcher_rows:
    pd.DataFrame(pitcher_rows).to_csv("data/betonline_pitcher_props.csv", index=False)
    print(f" Saved pitcher props: {len(pitcher_rows)} rows")
else:
    print(" No pitcher props found.")

if batter_rows:
    pd.DataFrame(batter_rows).to_csv("data/betonline_batter_props.csv", index=False)
    print(f" Saved batter props: {len(batter_rows)} rows")
else:
    print(" No batter props found.")

if team_rows:
    pd.DataFrame(team_rows).to_csv("data/betonline_team_lines.csv", index=False)
    print(f" Saved team lines: {len(team_rows)} rows")
else:
    print(" No team lines found.")

