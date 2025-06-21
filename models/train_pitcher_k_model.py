import pandas as pd
import numpy as np
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor

# === Load Data ===
df = pd.read_csv("data/Stathead_2025_Pitcher_Master.csv")

# === Clean + Parse ===
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["SO"] = pd.to_numeric(df["SO"], errors="coerce")
df["IP"] = pd.to_numeric(df["IP"], errors="coerce")
df["ER"] = pd.to_numeric(df["ER"], errors="coerce")
df["BB"] = pd.to_numeric(df["BB"], errors="coerce")
df["BF"] = pd.to_numeric(df["BF"], errors="coerce")
df["Home"] = df["Unnamed: 5"].apply(lambda x: 0 if x == "@" else 1)
df = df.dropna(subset=["Player", "Date", "SO"])

# === Rolling Averages ===
df = df.sort_values(["Player", "Date"])
rolling = df.groupby("Player").rolling(3, on="Date")[["SO", "IP", "ER", "BB", "BF"]].mean().reset_index()
rolling = rolling.rename(columns={
    "SO": "K_last3", "IP": "IP_last3", "ER": "ER_last3",
    "BB": "BB_last3", "BF": "BF_last3"
})
df = df.merge(rolling, on=["Player", "Date"], how="left")
df = df.dropna(subset=["K_last3", "IP_last3", "ER_last3"])  # keep recent games only

# === Feature Matrix ===
features = [
    "K_last3", "IP_last3", "ER_last3", "BB_last3", "BF_last3", "Home"
]
X = df[features]
y = df["SO"]

# === Train/Test Split ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True, random_state=42)

# === Models to Evaluate ===
models = {
    "LinearRegression": LinearRegression(),
    "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42),
    "GradientBoosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "XGBoost": XGBRegressor(n_estimators=100, random_state=42, verbosity=0)
}

results = []

for name, model in models.items():
    try:
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        results.append((name, model, rmse))
        print(f"{name} RMSE: {rmse:.3f}")
    except Exception as e:
        print(f"{name} failed: {e}")

# === Pick Best ===
results.sort(key=lambda x: x[2])  # sort by RMSE
best_name, best_model, best_rmse = results[0]
print(f"\n Best Model: {best_name} (RMSE = {best_rmse:.3f})")

# === Save Best Model
os.makedirs("models", exist_ok=True)
joblib.dump(best_model, "models/pitcher_k_model.joblib")
print(" Model saved to models/pitcher_k_model.joblib")
