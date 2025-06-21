import pandas as pd
import numpy as np
import joblib

# === Load Files ===
batting = pd.read_csv("data/Stathead_2025_TeamBatting_Master.csv")
pitching = pd.read_csv("data/Stathead_2025_Pitcher_Master.csv")
model = joblib.load("models/final_rf_model.joblib")

# === Clean Dates ===
batting["Date"] = batting["Date"].astype(str).str.extract(r"^(\d{4}-\d{2}-\d{2})")[0]
batting["Date"] = pd.to_datetime(batting["Date"])
pitching["Date"] = pitching["Date"].astype(str).str.extract(r"^(\d{4}-\d{2}-\d{2})")[0]
pitching["Date"] = pd.to_datetime(pitching["Date"])

# === Identify Home/Away ===
batting["Home"] = batting["Unnamed: 3"].ne("@").astype(int)
batting["R"] = pd.to_numeric(batting["R"], errors="coerce").fillna(0)

# === Build game-level rows (one row per game) ===
home_rows = batting[batting["Home"] == 1][["Date", "Team", "Opp", "R"]].rename(
    columns={"Team": "Home", "Opp": "Away", "R": "Home_R"}
)
away_rows = batting[batting["Home"] == 0][["Date", "Team", "R"]].rename(
    columns={"Team": "Away", "R": "Away_R"}
)

games = pd.merge(home_rows, away_rows, on=["Date", "Away"])
games["Actual_Total"] = games["Home_R"] + games["Away_R"]

#  Deduplicate real games
games["key"] = games["Date"].astype(str) + "_" + games["Home"] + "_" + games["Away"]
games = games.drop_duplicates(subset="key")
games = games.drop(columns="key")


# === Convert IP to float for pitcher logs ===
def convert_ip(ip):
    try:
        whole, frac = str(ip).split('.') if '.' in str(ip) else (str(ip), '0')
        return float(whole) + float(frac) / 3
    except:
        return 0.0

pitching["IP_float"] = pitching["IP"].apply(convert_ip)

# === Identify Starting Pitchers ===
pitching["Is_SP"] = pitching["IP_float"] >= 3.5
pitching = pitching.sort_values(["Date", "Team", "BF"], ascending=[True, True, False])
starters = pitching[pitching["Is_SP"]].groupby(["Date", "Team"]).head(1)[["Date", "Team", "Player"]]

# === Get rolling stats ===
pitching["ER"] = pd.to_numeric(pitching["ER"], errors="coerce").fillna(0)
pitching["H"] = pd.to_numeric(pitching["H"], errors="coerce").fillna(0)
pitching["BB"] = pd.to_numeric(pitching["BB"], errors="coerce").fillna(0)

sp_rolling = pitching.sort_values(["Player", "Date"]).groupby("Player").rolling(3, on="Date").agg({
    "ER": "sum",
    "H": "sum",
    "BB": "sum",
    "IP_float": "sum"
}).reset_index()

sp_rolling["SP_ERA_3g"] = (sp_rolling["ER"] * 9) / sp_rolling["IP_float"].replace(0, np.nan)
sp_rolling["SP_WHIP_3g"] = (sp_rolling["H"] + sp_rolling["BB"]) / sp_rolling["IP_float"].replace(0, np.nan)
sp_rolling = sp_rolling.rename(columns={"IP_float": "SP_IP"})
sp_rolling = sp_rolling[["Player", "Date", "SP_ERA_3g", "SP_WHIP_3g", "SP_IP"]]

# === Merge SPs with rolling stats
starters = starters.merge(sp_rolling, on=["Player", "Date"], how="left")

# === Attach to games
games = games.merge(starters.rename(columns={"Team": "Home", "Player": "Home_SP"}), on=["Date", "Home"], how="left")
games = games.merge(starters.rename(columns={"Team": "Away", "Player": "Away_SP"}), on=["Date", "Away"], how="left")

# === Get team rolling batting stats
batting = batting.sort_values(["Team", "Date"])
batting["OBP"] = pd.to_numeric(batting["OBP"], errors="coerce").fillna(0)
batting["Runs_avg3"] = batting.groupby("Team")["R"].rolling(3).mean().reset_index(0, drop=True)
batting["OBP_avg3"] = batting.groupby("Team")["OBP"].rolling(3).mean().reset_index(0, drop=True)

# === Get team pitching rolling stats
team_pitching = pitching.sort_values(["Team", "Date"])
team_rolling = team_pitching.groupby("Team").rolling(3, on="Date").agg({
    "ER": "sum", "H": "sum", "BB": "sum", "IP_float": "sum"
}).reset_index()

team_rolling["Team_ER_avg3"] = (team_rolling["ER"] * 9) / team_rolling["IP_float"].replace(0, np.nan)
team_rolling["Team_WHIP_avg3"] = (team_rolling["H"] + team_rolling["BB"]) / team_rolling["IP_float"].replace(0, np.nan)
team_rolling = team_rolling[["Team", "Date", "Team_ER_avg3", "Team_WHIP_avg3"]]

# === Attach features per team
def build_features(row, side):
    team = row[side]
    opp = row["Home"] if side == "Away" else row["Away"]
    date = row["Date"]

    team_row = batting[(batting["Team"] == team) & (batting["Date"] < date)].sort_values("Date").tail(1)
    opp_pitch_row = team_rolling[(team_rolling["Team"] == opp) & (team_rolling["Date"] < date)].sort_values("Date").tail(1)
    sp_row = starters[(starters["Player"] == row[f"{side}_SP"]) & (starters["Date"] < date)].sort_values("Date").tail(1)
    opp_sp_row = starters[(starters["Player"] == row[f"{'Away' if side == 'Home' else 'Home'}_SP"]) & (starters["Date"] < date)].sort_values("Date").tail(1)

    if team_row.empty or opp_pitch_row.empty or sp_row.empty or opp_sp_row.empty:
        return None

    return {
        "Runs_avg3": team_row["Runs_avg3"].values[0],
        "OBP_avg3": team_row["OBP_avg3"].values[0],
        "Team_ER_avg3": opp_pitch_row["Team_ER_avg3"].values[0],
        "Team_WHIP_avg3": opp_pitch_row["Team_WHIP_avg3"].values[0],
        "SP_ERA_3g": sp_row["SP_ERA_3g"].values[0],
        "SP_WHIP_3g": sp_row["SP_WHIP_3g"].values[0],
        "SP_IP": sp_row["SP_IP"].values[0],
        "Opp_SP_ERA_3g": opp_sp_row["SP_ERA_3g"].values[0],
        "Opp_SP_WHIP_3g": opp_sp_row["SP_WHIP_3g"].values[0],
        "Opp_SP_IP": opp_sp_row["SP_IP"].values[0],
        "Home": 1 if side == "Home" else 0
    }


# === Predict for both teams
rows = []
for _, row in games.iterrows():
    f_home = build_features(row, "Home")
    f_away = build_features(row, "Away")
    if f_home is None or f_away is None:
        continue

    pred_home = model.predict(pd.DataFrame([f_home]))[0]
    pred_away = model.predict(pd.DataFrame([f_away]))[0]

    rows.append({
        "Date": row["Date"],
        "Home_Team": row["Home"],
        "Away_Team": row["Away"],
        "Home_SP": row["Home_SP"],
        "Away_SP": row["Away_SP"],
        "Predicted_Home": round(pred_home, 2),
        "Predicted_Away": round(pred_away, 2),
        "Predicted_Total": round(pred_home + pred_away, 2),
        "Actual_Total": row["Actual_Total"],
        "Home_R": row["Home_R"],
        "Away_R": row["Away_R"]
})

# Convert rows to DataFrame and remove duplicates
final_df = pd.DataFrame(rows)
final_df = final_df.drop_duplicates(subset=["Date", "Home_Team", "Away_Team"])

# === Export
final_df.to_csv("data/backfilled_predictions.csv", index=False)
print(" Backfilled predictions saved to data/backfilled_predictions.csv")

