import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
import xgboost as xgb
import joblib

# === Load dataset
df = pd.read_csv("data/team_run_prediction_dataset.csv")

# === Define features and target
features = [
    "Runs_avg3", "OBP_avg3", "Team_ER_avg3", "Team_WHIP_avg3",
    "SP_ERA_3g", "SP_WHIP_3g", "SP_IP",
    "Opp_SP_ERA_3g", "Opp_SP_WHIP_3g", "Opp_SP_IP", "Home"
]
target = "Target_Runs"

X = df[features]
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# === Models to compare
models = {
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "XGBoost": xgb.XGBRegressor(n_estimators=100, random_state=42),
    "Linear Regression": LinearRegression()
}

# === Tune Random Forest with GridSearchCV
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [None, 5, 10],
    'min_samples_split': [2, 5],
}
grid_rf = GridSearchCV(RandomForestRegressor(random_state=42), param_grid, cv=3, scoring='neg_root_mean_squared_error', n_jobs=-1)
grid_rf.fit(X_train, y_train)

best_rf = grid_rf.best_estimator_
rf_rmse = np.sqrt(mean_squared_error(y_test, best_rf.predict(X_test)))
models["Random Forest (Tuned)"] = best_rf

results = []
best_model = None
best_rmse = float("inf")

for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    results.append((name, rmse))
    print(f"✅ {name}: RMSE = {rmse:.3f}")

    if rmse < best_rmse:
        best_model = model
        best_rmse = rmse

# === Save best model
joblib.dump(best_model, "models/final_team_model.joblib")
print(f"\n🏆 Saved best model ({best_model.__class__.__name__}) to models/final_team_model.joblib")
