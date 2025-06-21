import pandas as pd
import datetime
import re
import unidecode
from rapidfuzz import process, fuzz
from joblib import load

# === CONFIG ===
FEATURE_PATH = "data/engineered_features_2025.csv"
BOX_PATH = "data/pitching_through_yesterday.csv"
MODEL_PATH = "models/pitcher_k_model.joblib"
START_DATE = datetime.date(2025, 6, 1)
END_DATE = datetime.date(2025, 6, 7)

def normalize(name):
    return unidecode.unidecode(str(name)).lower().strip()

def clean_pitcher_name(name):
    return re.sub(r"\(.*?\)", "", str(name)).strip()

# === Load model
model = load(MODEL_PATH)
expected_features = model.feature_names_in_

# === Load data
feat_df = pd.read_csv(FEATURE_PATH)
feat_df["date"] = pd.to_datetime(feat_df["date"]).dt.date
feat_df["pitcher_key"] = feat_df["pitcher_name"].apply(normalize)

box_df = pd.read_csv(BOX_PATH)
box_df["GameDate"] = pd.to_datetime(box_df["GameDate"]).dt.date
box_df["pitcher_key"] = box_df["Pitcher"].apply(lambda x: normalize(clean_pitcher_name(x)))

# === Analyze date range
print(f" Checking feature completeness from {START_DATE} to {END_DATE}\n")
for date in pd.date_range(START_DATE, END_DATE).date:
    stats = feat_df[feat_df["date"] == date]
    box = box_df[box_df["GameDate"] == date]

    if stats.empty or box.empty:
        print(f"⏭ {date}: Skipped (missing {'features' if stats.empty else 'boxscores'})")
        continue

    feature_map = stats.set_index("pitcher_key")
    keys = stats["pitcher_key"].tolist()
    matched = 0
    total_missing = 0

    for _, row in box.iterrows():
        key = row["pitcher_key"]

        # Try exact or fuzzy match
        if key not in keys:
            match_result = process.extractOne(key, keys, scorer=fuzz.token_sort_ratio)
            if not match_result or match_result[1] < 80:
                continue
            key = match_result[0]

        if key in feature_map.index:
            #  Force exact Series row
            feat_row = feature_map.loc[[key]].iloc[0]
            missing = [col for col in expected_features if pd.isna(feat_row.get(col))]
            if missing:
                print(f" {date} - {row['Pitcher']} missing: {missing}")
                total_missing += 1
            else:
                matched += 1

    print(f" {date}: {matched} pitchers had complete features, {total_missing} had missing values\n")
