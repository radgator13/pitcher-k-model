import pandas as pd

# Update this path if your file is somewhere else
FILE = "data/model_backfill_results.csv"  # Replace with the actual file if named differently

print(f"🔍 Loading backfill file: {FILE}")
df = pd.read_csv(FILE)

# Ensure correct parsing of dates
if 'Date' not in df.columns:
    if 'date' in df.columns:
        df.rename(columns={'date': 'Date'}, inplace=True)
    else:
        raise Exception("❌ No 'Date' or 'date' column found in file")

df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

print(f"✅ Total rows loaded: {len(df)}")
print(f"📅 Min date: {df['Date'].min()}")
print(f"📅 Max date: {df['Date'].max()}")

# Optional: Show most recent few rows
print("\n🧾 Latest few entries:")
print(df.sort_values("Date", ascending=False).head(5))
