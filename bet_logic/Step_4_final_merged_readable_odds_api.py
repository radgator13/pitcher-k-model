import pandas as pd
import ast

# === Load the merged file ===
df = pd.read_csv("data/merged_game_props.csv")

# === Parse JSON-like prop columns ===
def safe_parse(val):
    try:
        return ast.literal_eval(val) if isinstance(val, str) else []
    except Exception:
        return []

df["pitcher_props"] = df["pitcher_props"].apply(safe_parse)
df["batter_props"] = df["batter_props"].apply(safe_parse)

# === Flatten into long rows ===
rows = []

for _, row in df.iterrows():
    context = {
        "event_id": row["event_id"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "commence_time": row["commence_time"],
    }

    # 1. TEAM markets: 1 row per team market line (h2h, spreads, totals)
    for col in df.columns:
        if col.startswith(("totals_", "spreads_", "h2h_")) and col.endswith("_line"):
            base = col.replace("_line", "")
            odds_col = f"{base}_odds"
            rows.append({
                **context,
                "type": "team",
                "player": base.replace("_", " "),  # e.g., spreads_chicago_cubs
                "market": base.split("_")[0],      # spreads, totals, h2h
                "line": row[col],
                "odds": row.get(odds_col)
            })

    # 2. Pitcher props
    for prop in row["pitcher_props"]:
        rows.append({
            **context,
            "type": "pitcher",
            "player": prop.get("player"),
            "market": prop.get("market"),
            "line": prop.get("line"),
            "odds": prop.get("odds")
        })

    # 3. Batter props
    for prop in row["batter_props"]:
        rows.append({
            **context,
            "type": "batter",
            "player": prop.get("player"),
            "market": prop.get("market"),
            "line": prop.get("line"),
            "odds": prop.get("odds")
        })

# === Save the flat, clean output ===
flat_df = pd.DataFrame(rows)
flat_df.to_csv("data/clean_all_props_flat.csv", index=False)

print(f"✅ All team, pitcher, and batter props saved to: data/clean_all_props_flat.csv")
