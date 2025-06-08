import pandas as pd
import joblib
import numpy as np
import os
from datetime import datetime

# === Load models and data ===
regressor = joblib.load("models/final_team_model.joblib")
schedule_df = pd.read_csv("data/scheduled_games_and_starters_with_id.csv")
pitcher_df = pd.read_csv("data/Stathead_2025_Pitcher_Master.csv")
historical_df = pd.read_csv("data/team_run_prediction_dataset.csv")

# Clean and parse dates
schedule_df["date"] = pd.to_datetime(schedule_df["date"])
pitcher_df["Date"] = pitcher_df["Date"].astype(str).str.extract(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})")[0]
pitcher_df["Date"] = pd.to_datetime(pitcher_df["Date"])
historical_df["Date"] = pd.to_datetime(historical_df["Date"])

# Convert innings pitched to float
ip_parts = pitcher_df["IP"].astype(str).str.extract(r"(?P<whole>\d+)(?:\.(?P<frac>\d))?")
pitcher_df["IP_float"] = ip_parts["whole"].astype(float) + ip_parts["frac"].fillna(0).astype(float) / 3.0

# === Rolling SP stats function ===
def get_sp_rolling_stats(pitcher_name, game_date):
    df = pitcher_df[pitcher_df["Player"] == pitcher_name]
    df = df[df["Date"] < game_date].sort_values("Date").tail(3)
    if df.empty:
        return None
    ip_total = df["IP_float"].sum()
    er_total = pd.to_numeric(df["ER"], errors="coerce").fillna(0).sum()
    h_total = pd.to_numeric(df["H"], errors="coerce").fillna(0).sum()
    bb_total = pd.to_numeric(df["BB"], errors="coerce").fillna(0).sum()
    if ip_total == 0:
        return None
    return {
        "SP_ERA_3g": (er_total * 9) / ip_total,
        "SP_WHIP_3g": (h_total + bb_total) / ip_total,
        "SP_IP": ip_total
    }

# === Thresholds and classifiers ===
thresholds = [3.5, 4.5, 5.5, 6.5]
classifiers = {
    t: joblib.load(f"models/classifier_over_{str(t).replace('.', '_')}.joblib")
    for t in thresholds
}

# === Prediction loop ===
prediction_rows = []

for _, game in schedule_df.iterrows():
    game_date = game["date"]

    for is_home in [True, False]:
        team = game["home_team"] if is_home else game["away_team"]
        opp = game["away_team"] if is_home else game["home_team"]
        sp_name = game["home_pitcher"] if is_home else game["away_pitcher"]
        opp_sp_name = game["away_pitcher"] if is_home else game["home_pitcher"]

        # Pull rolling team stats
        team_row = historical_df[
            (historical_df["Team"] == team) & (historical_df["Date"] < game_date)
        ].sort_values("Date").tail(1)

        opp_row = historical_df[
            (historical_df["Team"] == opp) & (historical_df["Date"] < game_date)
        ].sort_values("Date").tail(1)

        sp_stats = get_sp_rolling_stats(sp_name, game_date)
        opp_sp_stats = get_sp_rolling_stats(opp_sp_name, game_date)

        if team_row.empty or opp_row.empty or sp_stats is None or opp_sp_stats is None:
            continue

        features = {
            "Runs_avg3": team_row["Runs_avg3"].values[0],
            "OBP_avg3": team_row["OBP_avg3"].values[0],
            "Team_ER_avg3": opp_row["Team_ER_avg3"].values[0],
            "Team_WHIP_avg3": opp_row["Team_WHIP_avg3"].values[0],
            "SP_ERA_3g": sp_stats["SP_ERA_3g"],
            "SP_WHIP_3g": sp_stats["SP_WHIP_3g"],
            "SP_IP": sp_stats["SP_IP"],
            "Opp_SP_ERA_3g": opp_sp_stats["SP_ERA_3g"],
            "Opp_SP_WHIP_3g": opp_sp_stats["SP_WHIP_3g"],
            "Opp_SP_IP": opp_sp_stats["SP_IP"],
            "Home": 1 if is_home else 0
        }

        X_pred = pd.DataFrame([features])
        predicted_runs = regressor.predict(X_pred)[0]

        row = {
            "date": game_date.date(),
            "team": team,
            "opponent": opp,
            "home": features["Home"],
            "starting_pitcher": sp_name,
            "opponent_pitcher": opp_sp_name,
            "predicted_runs": round(predicted_runs, 2)
        }

        # Add classifier predictions for each threshold
        for t in thresholds:
            clf = classifiers[t]
            prob = clf.predict_proba(X_pred)[0][1]  # Probability of Over
            label = clf.predict(X_pred)[0]
            t_str = str(t).replace(".", "_")
            row[f"Over_{t_str}"] = int(label)
            row[f"Over_{t_str}_Prob"] = round(prob, 3)
            row[f"Under_{t_str}_Prob"] = round(1 - prob, 3)

        prediction_rows.append(row)

# === Output predictions
os.makedirs("outputs", exist_ok=True)
pred_df = pd.DataFrame(prediction_rows)
pred_df.to_csv("outputs/team_predictions.csv", index=False)
print("✅ Saved full team predictions to outputs/team_predictions.csv")
