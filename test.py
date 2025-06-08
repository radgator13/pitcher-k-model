import pandas as pd
from unidecode import unidecode
import re

# === Utility functions
def normalize(text):
    return unidecode(str(text)).lower().strip()

def clean_pitcher_name(name):
    return re.sub(r"\(.*?\)", "", str(name)).strip()

# === File paths (change if needed)
PRED_PATH = "predictions/2025-06-08/strikeouts_master.csv"
ODDS_PATH = "data/betonline_pitcher_props.csv"

# === Load data
pred_df = pd.read_csv(PRED_PATH)
odds_df = pd.read_csv(ODDS_PATH)

# === Identify pitcher column in predictions
pitcher_col = next((c for c in pred_df.columns if normalize(c) in ["pitcher", "starting_pitcher"]), None)
if pitcher_col is None:
    raise ValueError("❌ No 'Pitcher' column found in predictions file.")

# === Normalize prediction names
pred_df["pitcher_key"] = pred_df[pitcher_col].apply(lambda x: normalize(clean_pitcher_name(x)))
pred_pitchers = set(pred_df["pitcher_key"].dropna())

# === Process odds
odds_df = odds_df[odds_df["market"].str.lower() == "pitcher_strikeouts"].copy()
odds_df["description"] = odds_df["description"].astype(str)
odds_df["pitcher_key"] = odds_df["description"].apply(lambda x: normalize(clean_pitcher_name(x)))
odds_pitchers = set(odds_df["pitcher_key"].dropna())

# === Find intersections and differences
both = pred_pitchers & odds_pitchers
only_in_preds = pred_pitchers - odds_pitchers
only_in_odds = odds_pitchers - pred_pitchers

# === Print results
print("✅ Pitchers in both predictions and odds:", len(both))
print(sorted(list(both))[:10])

print("\n❌ Pitchers only in predictions:", len(only_in_preds))
print(sorted(list(only_in_preds))[:10])

print("\n❌ Pitchers only in odds:", len(only_in_odds))
print(sorted(list(only_in_odds))[:10])

# Optional: show merge coverage %
print(f"\n📊 Mergeable pitcher coverage: {len(both)} / {len(pred_pitchers)} ({100 * len(both) / max(len(pred_pitchers),1):.1f}%)")
