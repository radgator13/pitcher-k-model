# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import unidecode
import re
import os

INPUT = "data/stathead_2025_pitcher_master.csv"
OUTPUT = "data/engineered_features_2025.csv"

def normalize(name):
    return unidecode.unidecode(str(name)).lower().strip()

def ip_to_float(ip):
    if pd.isna(ip):
        return np.nan
    try:
        parts = str(ip).split('.')
        return int(parts[0]) + (1/3 if parts[1] == '1' else 2/3 if parts[1] == '2' else 0)
    except:
        return np.nan

# === Load Data ===
df = pd.read_csv(INPUT)

# --- Fix Date column ---
df["Date"] = (
    df["Date"]
    .astype(str)
    .str.extract(r"^(\d{4}-\d{2}-\d{2})")[0]
    .pipe(pd.to_datetime)
)

# === Standardize Inputs ===
df["pitcher_key"] = df["Player"].apply(normalize)
df["IP_float"] = df["IP"].apply(ip_to_float)
df["Home"] = df["Opp"].apply(lambda x: 0 if str(x).strip() == '@' else 1)
df["BF"] = pd.to_numeric(df["BF"], errors="coerce")
df["ER"] = pd.to_numeric(df["ER"], errors="coerce")
df["BB"] = pd.to_numeric(df["BB"], errors="coerce")
df["SO"] = pd.to_numeric(df["SO"], errors="coerce")

# === Sort for rolling computation ===
df = df.sort_values(by=["pitcher_key", "Date"]).reset_index(drop=True)

# === Compute Rolling Features (exclude current game) ===
rolled = (
    df.groupby("pitcher_key")
    .apply(lambda g: g.assign(
        K_last3=g["SO"].shift(1).rolling(3).sum(),
        IP_last3=g["IP_float"].shift(1).rolling(3).sum(),
        ER_last3=g["ER"].shift(1).rolling(3).sum(),
        BB_last3=g["BB"].shift(1).rolling(3).sum(),
        BF_last3=g["BF"].shift(1).rolling(3).sum()
    ))
    .reset_index(drop=True)
)

# Keep the full dataset with rolling features included
df = rolled

# === Final Output Columns ===
output = df[[
    "Date", "Player", "pitcher_key", "Team", "Opp", "Home",
    "K_last3", "IP_last3", "ER_last3", "BB_last3", "BF_last3"
]].copy()

output.rename(columns={
    "Date": "date",
    "Player": "pitcher_name",
    "Team": "team",
    "Opp": "opponent"
}, inplace=True)

# === Save ===
os.makedirs("data", exist_ok=True)
output.to_csv(OUTPUT, index=False)

print(f" Feature file saved to: {OUTPUT}")
