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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
driver.set_page_load_timeout(240)

# === Paths
today = datetime.date.today()
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
date_dir = f"data/archive/{today.isoformat()}"
os.makedirs(date_dir, exist_ok=True)

output_csv = f"{date_dir}/stathead_team_pitching_scrape_{timestamp}.csv"
master_csv = "data/Stathead_2025_TeamPitching_Master.csv"

# === Scrape recent team pitching logs
all_rows = []
page_num = 0

try:
    print("🚀 Starting browser and loading login page...")
    driver.get("https://stathead.com/users/login.cgi")
    time.sleep(2)

    print("🔐 Logging in...")
    driver.find_element(By.NAME, "username").send_keys(USERNAME)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(3)

    print("📅 Navigating to recent team pitching game logs...")
    driver.get(
        "https://stathead.com/baseball/team-pitching-game-finder.cgi"
        "?request=1&match=team_game&order_by_asc=0&order_by=date"
        "&timeframe=last_n_days&previous_days=5"
        "&comp_type=reg&game_type=all"
    )

    print("🕒 Waiting for results page to load (up to 3 mins)...")
    WebDriverWait(driver, 180).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.stats_table"))
    )

    while True:
        page_num += 1
        print(f"📄 Scraping page {page_num}...")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.select_one("table.stats_table")

        if not table:
            print("❌ Table not found on page.")
            break

        df = pd.read_html(str(table), header=0)[0]

        # ✅ This removes ONLY the repeated header row
        df = df[df["Rk"].astype(str).str.lower() != "rk"].reset_index(drop=True)

        all_rows.append(df)
        print(f"✅ Page {page_num}: {len(df)} clean rows scraped")


        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "div.prevnext a.button2.next")
            href = next_btn.get_attribute("href")
            if not href:
                print("⛔ No more pages to scrape.")
                break
            print("➡️ Moving to next page...")
            driver.get(href)

            print("⏳ Waiting for next table (up to 3 mins)...")
            WebDriverWait(driver, 180).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.stats_table"))
            )
        except:
            print("⛔ No next button found — ending scrape.")
            break

finally:
    print("🧹 Shutting down browser...")
    driver.quit()

# === Save results
if all_rows:
    scraped_df = pd.concat(all_rows, ignore_index=True)
    scraped_df.to_csv(output_csv, index=False)
    print(f"💾 Scraped {len(scraped_df)} rows to {output_csv}")

    if os.path.exists(master_csv):
        master_df = pd.read_csv(master_csv)
        before = len(master_df)
        combined = pd.concat([master_df, scraped_df], ignore_index=True)

        dedupe_cols = ["Team", "Date", "Result", "IP"]
        combined.drop_duplicates(subset=dedupe_cols, inplace=True)

        after = len(combined)
        new_rows = after - before if after >= before else 0

        combined.to_csv(master_csv, index=False)
        print(f"📌 Master file updated: {after} total rows")
        print(f"➕ Appended {new_rows} new row(s)")
    else:
        scraped_df.to_csv(master_csv, index=False)
        print("🆕 Master file created.")
else:
    print("❌ No data collected.")
