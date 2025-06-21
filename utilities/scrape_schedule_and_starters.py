from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from dateutil import parser
import pandas as pd
import os
import time
import shutil

# === ChromeDriver path
chrome_path = r"C:\Users\a1d3r\.wdm\drivers\chromedriver\win64\136.0.7103.94\chromedriver-win32\chromedriver.exe"

# === Headless Chrome setup
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
service = Service(executable_path=chrome_path)

# === Get URLs for next 3 days
base_url = "https://www.espn.com/mlb/schedule/_/date/"
today = datetime.today()
dates = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(3)]

all_games = []

for date_str in dates:
    driver = webdriver.Chrome(service=service, options=options)
    url = f"{base_url}{date_str}"
    print(f" Loading → {url}")
    driver.get(url)
    time.sleep(5)

    try:
        section = driver.find_element(By.CLASS_NAME, "ScheduleTables")
        game_date = section.find_element(By.CLASS_NAME, "Table__Title").text.strip()
        print(f" Game Date Found: {game_date}")

        rows = section.find_elements(By.XPATH, ".//tbody/tr[contains(@class, 'Table__TR')]")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 5:
                continue
            try:
                away_team = cols[0].text.strip()
                home_team = cols[1].text.strip().replace("@", "").strip()
                pitching_matchup = cols[4].text.strip()

                if "vs" in pitching_matchup:
                    away_pitcher, home_pitcher = [p.strip() for p in pitching_matchup.split("vs", 1)]
                else:
                    away_pitcher, home_pitcher = "Undecided", "Undecided"

                all_games.append({
                    "GameDate": game_date,
                    "AwayTeam": away_team,
                    "HomeTeam": home_team,
                    "AwayPitcher": away_pitcher,
                    "HomePitcher": home_pitcher
                })
            except Exception as e:
                print(f" Error processing row: {e}")

    except Exception as e:
        print(f" Could not find schedule on page {url} → {e}")
    
    driver.quit()

# === Create DataFrame
df = pd.DataFrame(all_games)

# === Drop games with both pitchers undecided
df = df[~((df["AwayPitcher"] == "Undecided") & (df["HomePitcher"] == "Undecided"))]

# === Parse GameDate safely
def parse_date(text):
    try:
        return parser.parse(text).strftime("%Y-%m-%d")
    except Exception as e:
        print(f" Failed to parse date: '{text}' → {e}")
        return None

df["GameDate"] = df["GameDate"].apply(parse_date)
df["GameDate"] = pd.to_datetime(df["GameDate"], errors="coerce")

# === Rename columns
df.rename(columns={
    "GameDate": "date",
    "AwayTeam": "away_team",
    "HomeTeam": "home_team",
    "AwayPitcher": "away_pitcher",
    "HomePitcher": "home_pitcher"
}, inplace=True)

# === Match pitcher IDs
id_map_path = "data/pitcher_id_map.csv"
if os.path.exists(id_map_path):
    id_map = pd.read_csv(id_map_path)
    id_map["FullName"] = id_map["FullName"].astype(str).str.replace(" ", "").str.strip()
    full_name_to_id = dict(zip(id_map["FullName"], id_map["PlayerID"]))

    def match_id(name):
        key = name.replace(" ", "").strip()
        return full_name_to_id.get(key, "")

    df["away_pitcher_id"] = df["away_pitcher"].apply(match_id)
    df["home_pitcher_id"] = df["home_pitcher"].apply(match_id)

    print(" Successfully matched pitcher names to PlayerID.")
else:
    print(" pitcher_id_map.csv not found.")
    df["away_pitcher_id"] = ""
    df["home_pitcher_id"] = ""

# === Archive old file
os.makedirs("data", exist_ok=True)
os.makedirs("data/archive", exist_ok=True)

output_path = "data/scheduled_games_and_starters_with_id.csv"
if os.path.exists(output_path):
    archive_date = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.join("data", "archive", archive_date)
    os.makedirs(archive_dir, exist_ok=True)

    archive_filename = f"scheduled_games_and_starters_with_id_{timestamp}.csv"
    archive_path = os.path.join(archive_dir, archive_filename)

    shutil.move(output_path, archive_path)
    print(f" Archived old file to {archive_path}")

# === Save new schedule
df.to_csv(output_path, index=False)
print(f" Saved new schedule to → {output_path}")
