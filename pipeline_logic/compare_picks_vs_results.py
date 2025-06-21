# -*- coding: utf-8 -*-
import pandas as pd
import datetime
import unidecode
import re
from rapidfuzz import process, fuzz

# --- Setup ---
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
date_str = yesterday.strftime("%Y-%m-%d")
print(f"\n Evaluating predictions for {date_str}\n")

# --- Normalize Utilities ---
def normalize(text):
    return unidecode.unidecode(str(text)).lower().strip()

def normalize_col(col):
    return normalize(col).replace("’", "'").replace("‘", "'").replace("`", "'")

def to_initial_last(full_name):
    parts = full_name.split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) >= 2 else full_name

def clean_pitcher_name(name):
    return re.sub(r"\(.*?\)", "", str(name)).strip()

# --- Load Predictions ---
pred_path = f"predictions/{date_str}/strikeouts_master.csv"
pred_df = pd.read_csv(pred_path)
pred_df["date"] = pd.to_datetime(pred_df["date"]).dt.date

# Detect predicted strikeouts column
normalized_cols = {normalize_col(c): c for c in pred_df.columns}
match_key = next((k for k in normalized_cols if "predicted" in k and "k" in k), None)
pred_k_col = normalized_cols.get(match_key)

if not pred_k_col:
    print(" Could not find predicted strikeouts column.")
    exit()

# Normalize prediction names
pred_df["pitcher_key"] = pred_df["Pitcher"].apply(lambda x: normalize(to_initial_last(x)))
predicted_keys = set(pred_df["pitcher_key"])

# --- Load Boxscore File ---
boxscore_path = "data/pitching_through_yesterday.csv"
boxscore_df = pd.read_csv(boxscore_path)
boxscore_df["GameDate"] = pd.to_datetime(boxscore_df["GameDate"]).dt.date
boxscore_df["pitcher_key"] = boxscore_df["Pitcher"].apply(lambda x: normalize(clean_pitcher_name(x)))

# Filter to prediction date & predicted pitchers
actuals = boxscore_df[
    (boxscore_df["GameDate"] == yesterday) &
    (boxscore_df["pitcher_key"].isin(predicted_keys))
].copy()

# Get max K if multiple rows per pitcher
actuals_grouped = (
    actuals[["pitcher_key", "K"]]
    .groupby("pitcher_key", as_index=False)
    .agg({"K": "max"})
)

# --- Match to predictions ---
merged = pred_df.merge(
    actuals_grouped,
    on="pitcher_key",
    how="left"
)

merged["Actual K"] = merged["K"]
merged["Predicted K"] = merged[pred_k_col]

# --- Calculate Model Pick (Over/Under) ---
def model_pick_direction(row):
    if pd.isna(row["Predicted K"]) or pd.isna(row["Vegas Line"]):
        return "N/A"
    if row["Predicted K"] > row["Vegas Line"]:
        return "Over"
    elif row["Predicted K"] < row["Vegas Line"]:
        return "Under"
    else:
        return "Push"

merged["Model Pick"] = merged.apply(model_pick_direction, axis=1)

# --- Evaluate HIT or MISS vs Vegas Line ---
def evaluate_result(row):
    if pd.isna(row["Actual K"]) or pd.isna(row["Vegas Line"]):
        return "NO DATA"
    if row["Model Pick"] == "Over":
        return "HIT" if row["Actual K"] > row["Vegas Line"] else "MISS"
    elif row["Model Pick"] == "Under":
        return "HIT" if row["Actual K"] < row["Vegas Line"] else "MISS"
    return "NO DATA"

merged["Result"] = merged.apply(evaluate_result, axis=1)

# --- Final Output ---
final = merged[[
    "date", "Pitcher", "Model Pick", " Confidence", "Vegas Line", "Predicted K", "Actual K", "Result"
]]

print("\n Final Results:")
print(final.to_string(index=False))

# --- Summary Totals ---
hit_count = (final["Result"] == "HIT").sum()
miss_count = (final["Result"] == "MISS").sum()
total = hit_count + miss_count
hit_rate = (hit_count / total * 100) if total > 0 else 0.0

print("\n Summary:")
print(f"Total HITs  : {hit_count}")
print(f"Total MISSes: {miss_count}")
print(f"Hit Rate    : {hit_rate:.1f}%")

# Optional: Save CSV
# final.to_csv(f"predictions/{date_str}/k_hit_miss_results.csv", index=False)
