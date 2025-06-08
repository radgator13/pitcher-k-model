# -*- coding: utf-8 -*-
import pandas as pd
import datetime
from joblib import load
import unidecode
import os
import re
from rapidfuzz import process, fuzz

# === Config ===
MODEL_PATH = "models/pitcher_k_model.joblib"
BOX_SCORE_PATH = "data/pitching_through_yesterday.csv"
FEATURE_PATH = "data/engineered_features_2025.csv"
OUTPUT_PATH = "data/model_backfill_results.csv"
VEGAS_LINE = 4.5
START_DATE = datetime.date(2025, 3, 27)
END_DATE = datetime.date.today() - datetime.timedelta(days=1)

def normalize(name):
    return unidecode.unidecode(str(name)).lower().strip()

def clean_pitcher_name(name):
    return re.sub(r"\(.*?\)", "", str(name)).strip()

print(f"📦 Loading model from: {MODEL_PATH}")
model = load(MODEL_PATH)

print(f"📊 Loading pitching results from: {BOX_SCORE_PATH}")
box_df = pd.read_csv(BOX_SCORE_PATH)
box_df["GameDate"] = pd.to_datetime(box_df["GameDate"]).dt.date
box_df["pitcher_key"] = box_df["Pitcher"].apply(lambda x: normalize(clean_pitcher_name(x)))

print(f"🔍 Loading model features from: {FEATURE_PATH}")
feat_df = pd.read_csv(FEATURE_PATH)
feat_df["date"] = pd.to_datetime(feat_df["date"]).dt.date
feat_df["pitcher_key"] = feat_df["pitcher_name"].apply(normalize)

# === Confirm data coverage
print("📅 Max date in box_df:", box_df["GameDate"].max())
print("📅 Max date in feat_df:", feat_df["date"].max())

expected_features = model.feature_names_in_
records = []

# === Date range loop
date_range = pd.date_range(START_DATE, END_DATE).date
print(f"📅 Running backfill from {START_DATE} to {END_DATE} ({len(date_range)} days)\n")

for date in date_range:
    game_pitchers = box_df[box_df["GameDate"] == date]
    stats_for_date = feat_df[feat_df["date"] == date]

    if game_pitchers.empty or stats_for_date.empty:
        print(f"⏭️ Skipping {date}: missing {'boxscore' if game_pitchers.empty else 'features'}")
        continue

    feature_keys = stats_for_date["pitcher_key"].tolist()
    feature_map = stats_for_date.set_index("pitcher_key")
    matched_rows = []

    for _, row in game_pitchers.iterrows():
        gkey = row["pitcher_key"]

        if gkey in feature_keys:
            match = gkey
            score = 100
        else:
            match_result = process.extractOne(gkey, feature_keys, scorer=fuzz.token_sort_ratio)
            match, score = match_result[0], match_result[1] if match_result else (None, 0)

        if match and score >= 80:
            feat_row = feature_map.loc[match]
            print(f"🔗 Matched {row['Pitcher']} → {feat_row['pitcher_name']} (score={score})")
            full_row = {
                "pitcher_key": match,
                "pitcher_name": feat_row["pitcher_name"],
                "date": feat_row["date"],
                "Team": row["Team"],
                "Opponent": row["Opponent"],
                "K": row["K"]
            }
            for col in expected_features:
                full_row[col] = feat_row.get(col, None)
            matched_rows.append(full_row)

    if not matched_rows:
        print(f"⏭️ Skipping {date}: no matches after join")
        continue

    print(f"📋 {date}: matched {len(matched_rows)} / {len(game_pitchers)} pitchers")
    merged = pd.DataFrame(matched_rows)
    X = merged[expected_features].apply(pd.to_numeric, errors="coerce")

    # === Missing feature diagnostics
    if X.isna().any().any():
        for i, row in merged.iterrows():
            missing = X.iloc[i].isna()
            if missing.any():
                print(f"⚠️ {row['pitcher_name']} missing: {missing[missing].index.tolist()}")

    X = X.dropna()
    if X.empty:
        print(f"⏭️ Skipping {date}: all rows dropped due to NaNs")
        continue

    print(f"✅ {date}: {len(X)} valid rows ready for prediction")

    try:
        preds = model.predict(X)
    except Exception as e:
        print(f"❌ Error predicting on {date}: {e}")
        continue

    for i, idx in enumerate(X.index):
        row = merged.loc[idx]
        pred_k = round(preds[i], 2)
        actual_k = row["K"]
        confidence = round(abs(pred_k - VEGAS_LINE), 2)
        pick = "Over" if pred_k > VEGAS_LINE else "Under"

        if pd.isna(actual_k):
            result = "NO DATA"
        elif (pick == "Over" and actual_k > VEGAS_LINE) or (pick == "Under" and actual_k < VEGAS_LINE):
            result = "HIT"
        else:
            result = "MISS"

        records.append({
            "Date": date,
            "Pitcher": row["pitcher_name"],
            "Team": row["Team"],
            "Opponent": row["Opponent"],
            "Predicted K": pred_k,
            "Confidence": confidence,
            "Model Pick": pick,
            "Actual K": actual_k,
            "Result": result
        })

# === Save final output
out_df = pd.DataFrame(records)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
out_df.to_csv(OUTPUT_PATH, index=False)
print(f"\n✅ Backfill complete: {len(out_df)} predictions saved to {OUTPUT_PATH}")
