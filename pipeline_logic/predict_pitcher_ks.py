import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime

# === Load model
model = joblib.load("models/pitcher_k_model.joblib")

# === Load input data
games_df = pd.read_csv("data/predicted_runs.csv", parse_dates=["date"])
pitching_df = pd.read_csv("data/Stathead_2025_Pitcher_Master.csv")
pitching_df["Date"] = pd.to_datetime(pitching_df["Date"], errors="coerce")

# === Clean pitching data
pitching_df["SO"] = pd.to_numeric(pitching_df["SO"], errors="coerce")
pitching_df["IP"] = pd.to_numeric(pitching_df["IP"], errors="coerce")
pitching_df["ER"] = pd.to_numeric(pitching_df["ER"], errors="coerce")
pitching_df["BB"] = pd.to_numeric(pitching_df["BB"], errors="coerce")
pitching_df["BF"] = pd.to_numeric(pitching_df["BF"], errors="coerce")
pitching_df["Home"] = pitching_df["Unnamed: 5"].apply(lambda x: 0 if x == "@" else 1)

# === Predict for each starting pitcher in predicted_runs.csv
pred_rows = []

for _, row in games_df.iterrows():
    pitcher_name = row["starting_pitcher"]
    game_date = row["date"]
    team = row["team"]
    opponent = row["opponent"]

    # Get most recent 3 appearances
    history = pitching_df[(pitching_df["Player"] == pitcher_name) & (pitching_df["Date"] < game_date)]
    history = history.sort_values("Date").tail(3)

    if len(history) < 3:
        continue  # not enough data to predict

    # Compute rolling averages
    features = {
        "K_last3": history["SO"].mean(),
        "IP_last3": history["IP"].mean(),
        "ER_last3": history["ER"].mean(),
        "BB_last3": history["BB"].mean(),
        "BF_last3": history["BF"].mean(),
        "Home": 1 if row.get("home") in [1, "1", True] else 0
    }

    X = pd.DataFrame([features])
    predicted_ks = model.predict(X)[0]

    pred_rows.append({
        "date": game_date,
        "team": team,
        "opponent": opponent,
        "starting_pitcher": pitcher_name,
        "predicted_ks": round(predicted_ks, 2)
    })

# === Create DataFrame
output_df = pd.DataFrame(pred_rows)

# === Save to general output folder
os.makedirs("outputs", exist_ok=True)
output_df.to_csv("outputs/pitcher_k_predictions.csv", index=False)
print("✅ Saved to outputs/pitcher_k_predictions.csv")

# === Save to dated predictions folder (for Streamlit)
today_str = datetime.today().strftime("%Y-%m-%d")
output_folder = f"predictions/{today_str}"
os.makedirs(output_folder, exist_ok=True)

# ✅ Filter only today's predictions before saving
output_df_today = output_df[output_df["date"] == pd.to_datetime(today_str)]

# === Log dates included
print("📅 Dates in prediction output:", output_df["date"].dt.strftime("%Y-%m-%d").unique())

output_path = f"{output_folder}/strikeouts_master.csv"
output_df_today.to_csv(output_path, index=False)
print(f"✅ Saved to {output_path}")
