import os
import time
import datetime
import pandas as pd
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path

# === Load credentials
load_dotenv(dotenv_path=Path("utilities/.env"))
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")
if not USERNAME or not PASSWORD:
    raise ValueError("❌ STATHEAD_USERNAME or STATHEAD_PASSWORD is not set.")

# === Setup headless browser
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# === Paths
today = datetime.date.today()
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
date_dir = f"data/archive/{today.isoformat()}"
os.makedirs(date_dir, exist_ok=True)

output_csv = f"{date_dir}/stathead_pitching_scrape_{timestamp}.csv"
master_csv = "data/Stathead_2025_Pitcher_Master.csv"

# === Scrape recent 5 days
all_rows = []
page_num = 0

try:
    print("🚀 Logging in and starting scrape...")
    driver.get("https://stathead.com/users/login.cgi")
    time.sleep(2)
    driver.find_element(By.NAME, "username").send_keys(USERNAME)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(3)

    driver.get(
        "https://stathead.com/baseball/player-pitching-game-finder.cgi"
        "?request=1&match=player_game&order_by_asc=0&order_by=date"
        "&timeframe=last_n_days&previous_days=5"
        "&comp_type=reg&team_game_min=1&team_game_max=165"
        "&player_game_min=1&player_game_max=9999"
        "&is_pitcher=1&role=anyGS"
    )
    time.sleep(5)

    while True:
        page_num += 1
        print(f"📄 Scraping page {page_num}...")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.select_one("table.stats_table")
        if not table:
            print("❌ Table not found.")
            break

        df = pd.read_html(str(table))[0]

        # ✅ Remove repeated headers mid-table
        df = df[df["Rk"].astype(str).str.lower() != "rk"].reset_index(drop=True)

        all_rows.append(df)
        print(f"✅ Page {page_num}: {len(df)} clean rows")

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "div.prevnext a.button2.next")
            href = next_btn.get_attribute("href")
            if not href:
                break
            driver.get(href)
            time.sleep(5)
        except:
            break

finally:
    print("🧹 Closing browser...")
    driver.quit()

# === Process scraped rows
if all_rows:
    scraped_df = pd.concat(all_rows, ignore_index=True)
    scraped_df.to_csv(output_csv, index=False)
    print(f"💾 Scraped {len(scraped_df)} rows to {output_csv}")

    if os.path.exists(master_csv):
        master_df = pd.read_csv(master_csv)
        before = len(master_df)
        combined = pd.concat([master_df, scraped_df], ignore_index=True)
        combined.drop_duplicates(subset=["Player", "Date", "Team", "IP", "Result"], inplace=True)
        after = len(combined)
        new_rows = after - before

        combined.to_csv(master_csv, index=False)
        print(f"📌 Master file updated: {after} total rows")
        print(f"➕ Appended {new_rows} new row(s)")
    else:
        scraped_df.to_csv(master_csv, index=False)
        print("🆕 Master file created.")
else:
    print("❌ No data collected.")
