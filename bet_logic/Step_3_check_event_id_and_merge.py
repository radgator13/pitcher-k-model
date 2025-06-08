import pandas as pd
import os
import shutil
from datetime import datetime, date

# === Load all data ===
pitcher_df = pd.read_csv("data/betonline_pitcher_props.csv")
batter_df = pd.read_csv("data/betonline_batter_props.csv")
team_df = pd.read_csv("data/betonline_team_lines.csv")  # Use unfiltered, fresh file

# Ensure event_id is str
for df in [pitcher_df, batter_df, team_df]:
    df["event_id"] = df["event_id"].astype(str)

# === Add commence_time and filter stale rows ===
def normalize_and_filter(df, label):
    df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")
    df["game_date"] = df["commence_time"].dt.date

    today = date.today()
    fresh_df = df[df["game_date"] >= today].copy()

    print(f"\n📅 {label} — game dates:")
    print(fresh_df["game_date"].value_counts().sort_index())
    print(f"✅ Retained rows for {fresh_df['game_date'].nunique()} game dates (≥ {today})")

    return fresh_df


# === Flatten team lines ===
def flatten_team_props(df):
    game_rows = []
    for event_id, group in df.groupby("event_id"):
        row = {
            "event_id": event_id,
            "home_team": group["home_team"].iloc[0],
            "away_team": group["away_team"].iloc[0],
            "commence_time": group["commence_time"].iloc[0],
        }

        for _, market_row in group.iterrows():
            market = market_row["market"]
            name = str(market_row["raw_name"]).lower().replace(" ", "_")
            line = market_row["line"]
            odds = market_row["odds"]
            key = f"{market}_{name}"
            row[f"{key}_line"] = line
            row[f"{key}_odds"] = odds

        game_rows.append(row)
    return pd.DataFrame(game_rows)

team_flat = flatten_team_props(team_df)

# === Group props
def group_props(df, role):
    def clean_name(row):
        for field in ["description", "participant", "raw_name"]:
            name = row.get(field)
            if isinstance(name, str) and name.strip().lower() not in ["over", "under"]:
                return name.strip()
        return None

    def extract_props(group):
        records = []
        for _, row in group.iterrows():
            name = clean_name(row)
            if name:
                records.append({
                    "player": name,
                    "market": row["market"],
                    "line": row["line"],
                    "odds": row["odds"]
                })
        return records

    grouped = df.groupby("event_id", group_keys=False).apply(extract_props).reset_index()
    grouped.columns = ["event_id", f"{role}_props"]
    return grouped

pitcher_grouped = group_props(pitcher_df, "pitcher")
batter_grouped = group_props(batter_df, "batter")

# === Merge all three
merged = team_flat.merge(pitcher_grouped, on="event_id", how="left")
merged = merged.merge(batter_grouped, on="event_id", how="left")

# === Add game_date and check
merged["commence_time"] = pd.to_datetime(merged["commence_time"], errors="coerce")
merged["game_date"] = merged["commence_time"].dt.date

if merged["game_date"].max() < date.today():
    raise ValueError("❌ STOP: All merged games are from the past. Check your input files.")

# === Auto-backup old file
backup_dir = "data/backups"
os.makedirs(backup_dir, exist_ok=True)
if os.path.exists("data/merged_game_props.csv"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"merged_game_props_backup_{timestamp}.csv")
    shutil.copy("data/merged_game_props.csv", backup_path)
    print(f"\n📦 Previous merged_game_props.csv backed up to:\n   {backup_path}")

# === Save new output
merged.to_json("data/merged_game_props.json", orient="records", indent=2)
merged.to_csv("data/merged_game_props.csv", index=False)

print(f"\n✅ Merged game-level file saved with {len(merged)} rows")
print(f"📄 JSON: {os.path.abspath('data/merged_game_props.json')}")
print(f"📄 CSV:  {os.path.abspath('data/merged_game_props.csv')}")
