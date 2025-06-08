# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import joblib
import os

# === Load files ===
pitching = pd.read_csv("data/Stathead_2025_Pitcher_Master.csv")
model = joblib.load("models/pitcher_k_model.joblib")

# === Clean data ===
pitching["Date"] = pd.to_datetime(pitching["Date"].astype(str).str.extract(r"^(\d{4}-\d{2}-\d{2})")[0])
pitching["SO"] = pd.to_numeric(pitching["SO"], errors="coerce")
pitching["IP"] = pd.to_numeric(pitching["IP"], errors="coerce")
pitching["ER"] = pd.to_numeric(pitching["ER"], errors="coerce")
pitching["BB"] = pd.to_numeric(pitching["BB"], errors="coerce")
pitching["BF"] = pd.to_numeric(pitching["BF"], errors="coerce")
pitching["Home"] = pitching["Unnamed: 5"].apply(lambda x: 0 if x == "@" else 1)

# === Convert IP to float
def convert_ip(ip):
    try:
        whole, frac = str(ip).split('.') if '.' in str(ip) else (str(ip), '0')
        return float(whole) + float(frac) / 3
    except:
        return 0.0

pitching["IP_float"] = pitching["IP"].apply(convert_ip)
pitching = pitching.sort_values(["Player", "Date"])

# === Get rolling 3-game averages (min 2 games to avoid early cutoff)
rolling = pitching.groupby("Player").rolling(
    window=3, min_periods=2, on="Date"
)[["SO", "IP", "ER", "BB", "BF"]].mean().reset_index()

rolling = rolling.rename(columns={
    "SO": "K_last3", "IP": "IP_last3", "ER": "ER_last3",
    "BB": "BB_last3", "BF": "BF_last3"
})

# === Merge back to identify usable starts
pitching = pitching.merge(rolling, on=["Player", "Date"], how="left")

# === Filter to starting pitchers (IP ≥ 3.5)
pitching["Is_SP"] = pitching["IP_float"] >= 3.5
pitching_starts = pitching[pitching["Is_SP"]]

# === Debug: Check date coverage
print("📆 Max Date (raw):", pitching["Date"].max())
print("📆 Max Date (starts only):", pitching_starts["Date"].max())

# === Drop rows missing rolling features
pitching_starts = pitching_starts.dropna(subset=["K_last3", "IP_last3", "ER_last3", "BB_last3", "BF_last3"])

# === Final date after filtering
print("📆 Max Date (usable for modeling):", pitching_starts["Date"].max())

# === Build feature matrix
features = ["K_last3", "IP_last3", "ER_last3", "BB_last3", "BF_last3", "Home"]

X = pitching_starts[features]
y = pitching_starts["SO"]
dates = pitching_starts["Date"]
pitchers = pitching_starts["Player"]
teams = pitching_starts["Team"]
opponents = pitching_starts["Opp"]

# === Add logic for Model Pick, Confidence, and Result
VEGAS_LINE = 4.5

def compute_result(pred_k, actual_k):
    if pd.isna(actual_k):
        return "NO DATA"
    pick = "Over" if pred_k > VEGAS_LINE else "Under"
    if pick == "Over" and actual_k > VEGAS_LINE:
        return "HIT"
    elif pick == "Under" and actual_k < VEGAS_LINE:
        return "HIT"
    return "MISS"

# === Predict K’s
predicted_ks = model.predict(X)

# === Build output
records = []
for i in range(len(X)):
    pred_k = round(predicted_ks[i], 2)
    actual_k = y.iloc[i]
    row = {
        "Date": dates.iloc[i],
        "Team": teams.iloc[i],
        "Opponent": opponents.iloc[i],
        "Pitcher": pitchers.iloc[i],
        "Predicted K": pred_k,
        "Confidence": round(abs(pred_k - VEGAS_LINE), 2),
        "Model Pick": "Over" if pred_k > VEGAS_LINE else "Under",
        "Actual K": actual_k,
        "Result": compute_result(pred_k, actual_k)
    }
    records.append(row)

# === Save to correct file
OUTPUT_PATH = "data/model_backfill_pitcher_ks.csv"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

out_df = pd.DataFrame(records)
out_df = out_df.drop_duplicates(subset=["Date", "Pitcher"])
out_df.to_csv(OUTPUT_PATH, index=False)

print(f"✅ Backfilled pitcher K predictions saved to {OUTPUT_PATH}")
