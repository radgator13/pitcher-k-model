import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
import time
import os

def get_game_ids(date_obj):
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"
    print(f"🔍 Requesting game IDs for {date_str}...")
    r = requests.get(url)
    events = r.json().get("events", [])
    return [{"gameId": e["id"], "date": date_obj.strftime("%Y-%m-%d")} for e in events if "id" in e]

def extract_boxscore(game_id, game_date):
    url = f"https://www.espn.com/mlb/boxscore/_/gameId/{game_id}"
    print(f"🌐 Scraping HTML: {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.content, "html.parser")

    team_names = soup.select("h2.ScoreCell__TeamName")
    if len(team_names) < 2:
        print("❌ Could not find team names")
        return None

    away_team = team_names[0].text.strip()
    home_team = team_names[1].text.strip()

    records = soup.select("div.Gamestrip__Record")
    away_record = records[0].text.strip().split(',')[0] if records else ""
    home_record = records[1].text.strip().split(',')[0] if len(records) > 1 else ""

    scores = soup.select("div.Gamestrip__Score")
    away_runs = scores[0].get_text(strip=True) if scores else ""
    home_runs = scores[1].get_text(strip=True) if len(scores) > 1 else ""

    game_row = {
        "Game Date": game_date,
        "Away Team": away_team,
        "Home Team": home_team,
        "Away Record": away_record,
        "Home Record": home_record,
        "Away Score": re.sub(r"\D", "", away_runs),
        "Home Score": re.sub(r"\D", "", home_runs)
    }

    print(f"✅ Game context parsed: {away_team} @ {home_team} | Score: {away_runs}-{home_runs}")

    try:
        containers = soup.select("div.Athletes__Container")
        print(f"🔍 Found {len(containers)} pitcher containers")

        for container in containers:
            labels = container.find_all("span", class_="Athlete__Header")
            names = container.find_all("span", class_="Athlete__PlayerName")
            stats = container.find_all("div", class_="Athlete__Stats")

            count = min(len(labels), len(names), len(stats))
            print(f"➡️ Found {count} pitcher label blocks in this container")

            for i in range(count):
                role = labels[i].text.strip().lower()
                if role not in ["win", "loss"]:
                    print(f"   ⛔ Skipping label: {role}")
                    continue

                prefix = "Winning" if role == "win" else "Losing"
                name = names[i].text.strip()
                stats_text = stats[i].text.strip()

                print(f"   🏷️ {prefix} Pitcher: {name} | Stats: {stats_text}")

                ip = re.search(r"(\d+\.?\d*) IP", stats_text)
                h = re.search(r"(\d+) H", stats_text)
                er = re.search(r"(\d+) ER", stats_text)
                k = re.search(r"(\d+) K", stats_text)
                bb = re.search(r"(\d+) BB", stats_text)

                game_row[f"{prefix} Pitcher"] = name
                game_row[f"{prefix} IP"] = float(ip.group(1)) if ip else None
                game_row[f"{prefix} H"] = int(h.group(1)) if h else None
                game_row[f"{prefix} ER"] = int(er.group(1)) if er else None
                game_row[f"{prefix} K"] = int(k.group(1)) if k else None
                game_row[f"{prefix} BB"] = int(bb.group(1)) if bb else None

    except Exception as e:
        print(f"⚠️ Error parsing pitchers for game {game_id}: {e}")

    return game_row

def scrape_and_append_pitchers_only():
    today = datetime.today()
    start_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    new_rows = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.expanduser("~/Downloads/archive")
    os.makedirs(archive_dir, exist_ok=True)

    master_file = "data/boxscores_pitcher_full-MASTER.csv"
    archive_file = f"data/archive/boxscores_pitcher_append_{timestamp}.csv"


    if os.path.exists(master_file):
        existing_df = pd.read_csv(master_file)
        existing_keys = set(existing_df[["Game Date", "Away Team", "Home Team"]].apply(tuple, axis=1))
    else:
        existing_df = pd.DataFrame()
        existing_keys = set()

    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        print(f"\n📅 Checking games on {current.strftime('%Y-%m-%d')}")
        games = get_game_ids(current)
        print(f"Found {len(games)} games.")

        for game in games:
            try:
                row = extract_boxscore(game["gameId"], game["date"])
                if row:
                    row_id = (row.get("Game Date"), row.get("Away Team"), row.get("Home Team"))
                    if row_id in existing_keys:
                        print(f"⏭️ Already exists: {row_id}")
                        continue

                    if "Winning Pitcher" in row and "Losing Pitcher" in row:
                        new_rows.append(row)
                    else:
                        print(f"⚠️ Incomplete data: {row_id}")
            except Exception as e:
                print(f"❌ Error scraping game {game['gameId']}: {e}")
            time.sleep(0.5)

        current += timedelta(days=1)

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        print(f"\n✅ Appending {len(new_df)} new games to MASTER and ARCHIVE.")

        new_df.to_csv(master_file, mode='a', index=False, header=not os.path.exists(master_file))
        new_df.to_csv(archive_file, index=False)

        print(f"📌 Appended to {master_file}")
        print(f"📁 Archived to {archive_file}")
    else:
        print("\n⚠️ No new games to append.")

if __name__ == "__main__":
    print("🚀 Appending pitcher data from today -2 through today +1")
    scrape_and_append_pitchers_only()
