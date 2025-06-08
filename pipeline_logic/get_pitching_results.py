import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import pandas as pd
import os

def scrape_espn_boxscore(game_id, game_date):
    url = f"https://www.espn.com/mlb/boxscore/_/gameId/{game_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Could not retrieve game {game_id}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    print(f"✅ Game ID: {game_id} | Date: {game_date}")

    pitching_data = []

    teams = []
    for div in soup.find_all("div", class_="TeamTitle__Name"):
        text = div.get_text(strip=True)
        if text.endswith("Pitching"):
            teams.append(text.replace("Pitching", "").strip())
    if len(teams) != 2:
        print("⚠️ Could not determine both teams.")
        return []
    away_team, home_team = teams

    final_score = "Unknown"
    score_blocks = soup.find_all("div", class_="Boxscore__Meta")
    if score_blocks:
        score_text = score_blocks[0].get_text(separator=" ")
        match = re.search(r"([A-Za-z \-.]+)\s+(\d+)\s*[-–]\s*(\d+)\s+([A-Za-z \-.]+)", score_text)
        if match:
            t1, s1, s2, t2 = match.group(1).strip(), match.group(2), match.group(3), match.group(4).strip()
            if t1 in [away_team, home_team] and t2 in [away_team, home_team]:
                final_score = f"{t1} {s1} - {s2} {t2}" if t1 == away_team else f"{t2} {s2} - {s1} {t1}"

    for title_div in soup.find_all("div", class_="TeamTitle__Name"):
        if not title_div.text.strip().endswith("Pitching"):
            continue

        team_name = title_div.text.replace("Pitching", "").strip()
        opponent = home_team if team_name == away_team else away_team
        home_away = "Home" if team_name == home_team else "Away"

        try:
            wrapper = title_div.find_parent("div", class_="Boxscore__Team")
            tables = wrapper.find_all("table")
            if len(tables) < 2:
                print(f"⚠️ Not enough tables for {team_name}.")
                continue

            name_table = tables[0]
            stat_table = tables[1]
            headers = [th.text.strip() for th in stat_table.find("thead").find_all("th")]
            name_rows = name_table.find("tbody").find_all("tr")
            stat_rows = stat_table.find("tbody").find_all("tr")

            for name_row, stat_row in zip(name_rows, stat_rows):
                pitcher = name_row.get_text(strip=True)
                if pitcher.lower() == "team":
                    continue
                values = [td.text.strip() for td in stat_row.find_all("td")]
                if len(values) != len(headers):
                    continue
                record = dict(zip(headers, values))
                record.update({
                    "Pitcher": pitcher,
                    "Team": team_name,
                    "Opponent": opponent,
                    "HomeAway": home_away,
                    "FinalScore": final_score,
                    "GameID": game_id,
                    "GameDate": game_date
                })
                pitching_data.append(record)

        except Exception as e:
            print(f"🔥 Error in {team_name} section: {e}")

    return pitching_data

def get_game_ids_for_date(date):
    url = f"https://www.espn.com/mlb/scoreboard/_/date/{date.strftime('%Y%m%d')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Could not load scoreboard for {date}")
        return []
    game_ids = re.findall(r'gameId/(\d+)', resp.text)
    return sorted(set(game_ids))

# Load existing results
existing_path = "data/pitching_through_yesterday.csv"
if os.path.exists(existing_path):
    existing_df = pd.read_csv(existing_path)
    existing_df["GameID"] = existing_df["GameID"].astype(str)
    existing_df["Pitcher"] = existing_df["Pitcher"].astype(str)
    existing_keys = set(zip(existing_df["GameID"], existing_df["Pitcher"]))
    print(f"📄 Found {len(existing_df)} existing rows.")
else:
    existing_df = pd.DataFrame()
    existing_keys = set()
    print("🆕 Starting fresh.")

# Date range
#start_date = datetime(2025, 3, 27)
start_date = datetime.today() - timedelta(days=3)
end_date = datetime.today() - timedelta(days=1)
current_date = start_date

new_rows = []

while current_date <= end_date:
    print(f"\n📆 Processing {current_date.date()}")
    for game_id in get_game_ids_for_date(current_date):
        game_data = scrape_espn_boxscore(game_id, current_date.date())
        for row in game_data:
            if (str(row["GameID"]), str(row["Pitcher"])) not in existing_keys:
                new_rows.append(row)
    current_date += timedelta(days=1)

# Save merged result
if new_rows:
    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    cols = ['Pitcher', 'Team', 'Opponent', 'HomeAway', 'FinalScore', 'GameID', 'GameDate'] + [
        c for c in new_df.columns if c not in ['Pitcher', 'Team', 'Opponent', 'HomeAway', 'FinalScore', 'GameID', 'GameDate']
    ]
    combined = combined[cols]
    combined.to_csv(existing_path, index=False)
    print(f"\n✅ Appended {len(new_rows)} new rows.")
    print(f"✅ Updated: {existing_path}")
else:
    print("✅ No new pitching data needed.")
