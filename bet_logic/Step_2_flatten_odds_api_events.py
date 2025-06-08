import pandas as pd
import ast
from datetime import date
import os

# === Load and parse the merged props file ===
df = pd.read_csv("data/merged_game_props.csv")

def safe_parse(val):
    try:
        return ast.literal_eval(val) if isinstance(val, str) else []
    except Exception:
        return []

df["pitcher_props"] = df["pitcher_props"].apply(safe_parse)
df["batter_props"] = df["batter_props"].apply(safe_parse)

# === Convert date and filter old games ===
df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")
df["game_date"] = df["commence_time"].dt.date
df = df[df["game_date"] >= date.today()]

# === Filter out empty or invalid props ===
def clean_props(props_list):
    cleaned = []
    for prop in props_list:
        name = prop.get("description") or prop.get("participant") or prop.get("raw_name")
        if name and str(name).lower() not in ["over", "under"]:
            cleaned.append({
                "player": name,
                "market": prop.get("market"),
                "line": prop.get("line"),
                "odds": prop.get("odds")
            })
    return cleaned

df["pitcher_props"] = df["pitcher_props"].apply(clean_props)
df["batter_props"] = df["batter_props"].apply(clean_props)

# === Flatten into one row per team, pitcher group, batter group ===
flat_rows = []

for _, row in df.iterrows():
    base = {
        "event_id": row["event_id"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "commence_time": row["commence_time"],
        "game_date": row["game_date"]
    }

    # TEAM ROW
    team_row = base.copy()
    team_row["type"] = "team"
    for col in df.columns:
        if col.startswith(("totals_", "spreads_", "h2h_")):
            team_row[col] = row[col]
    flat_rows.append(team_row)

    # PITCHERS ROW
    pitcher_row = base.copy()
    pitcher_row["type"] = "pitcher"
    pitcher_row["props"] = row["pitcher_props"]
    flat_rows.append(pitcher_row)

    # BATTERS ROW
    batter_row = base.copy()
    batter_row["type"] = "batter"
    batter_row["props"] = row["batter_props"]
    flat_rows.append(batter_row)

# === Save the final flat output ===
final_df = pd.DataFrame(flat_rows)
output_file = "data/flat_combined_teams_pitchers_batters.csv"
final_df.to_csv(output_file, index=False)

print(f"✅ Saved 3x per game format to:\n📄 {os.path.abspath(output_file)}")
