import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import warnings
warnings.filterwarnings("ignore")

# === Load Data ===
df = pd.read_csv("data/team_run_prediction_dataset.csv")
print(f" Loaded dataset with {len(df)} rows")

# === Features & Target ===
target = "Target_Runs"
features = [
    "Runs_avg3", "OBP_avg3", "Team_ER_avg3", "Team_WHIP_avg3",
    "SP_ERA_3g", "SP_WHIP_3g", "SP_IP",
    "Opp_SP_ERA_3g", "Opp_SP_WHIP_3g", "Opp_SP_IP",
    "Home"
]
X = df[features]
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# === Random Forest Tuning ===
print("\n Tuning Random Forest...")
rf_params = {
    "n_estimators": [100, 200],
    "max_depth": [5, 10, None],
    "min_samples_split": [2, 5]
}
rf_grid = GridSearchCV(
    RandomForestRegressor(random_state=42),
    rf_params,
    cv=3,
    scoring="neg_root_mean_squared_error",
    n_jobs=-1
)
rf_grid.fit(X_train, y_train)

# Best RF
best_rf = rf_grid.best_estimator_
rf_preds = best_rf.predict(X_test)
rf_rmse = np.sqrt(mean_squared_error(y_test, rf_preds))

print(f" Best Random Forest RMSE: {rf_rmse:.3f}")
print(f"  Best Params: {rf_grid.best_params_}")

# === XGBoost Tuning ===
print("\n Tuning XGBoost...")
xgb_params = {
    "n_estimators": [100, 200],
    "max_depth": [3, 6, 10],
    "learning_rate": [0.05, 0.1]
}
xgb_grid = GridSearchCV(
    xgb.XGBRegressor(random_state=42, verbosity=0),
    xgb_params,
    cv=3,
    scoring="neg_root_mean_squared_error",
    n_jobs=-1
)
xgb_grid.fit(X_train, y_train)

# Best XGB
best_xgb = xgb_grid.best_estimator_
xgb_preds = best_xgb.predict(X_test)
xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_preds))

print(f" Best XGBoost RMSE: {xgb_rmse:.3f}")
print(f"  Best Params: {xgb_grid.best_params_}")

# === Compare
print("\n Final Results:")
print(f"Random Forest RMSE: {rf_rmse:.3f}")
print(f"XGBoost       RMSE: {xgb_rmse:.3f}")

# === Retrain Final Model on All Data
final_model = RandomForestRegressor(
    n_estimators=100,
    max_depth=None,
    min_samples_split=2,
    random_state=42
)
final_model.fit(X, y)
print(" Trained final Random Forest model on all data")

# === Save the model
import joblib, os
os.makedirs("models", exist_ok=True)
joblib.dump(final_model, "models/final_rf_model.joblib")
print(" Model saved to: models/final_rf_model.joblib")
