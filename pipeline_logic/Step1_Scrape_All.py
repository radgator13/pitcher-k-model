import subprocess
import time
from datetime import datetime

scripts = [
    "utilities/scrape_schedule_and_starters.py",
    "scrape_logic/ScrapePitcherGameData.py",
    "scrape_logic/ScrapeTeamBatting.py",
    "scrape_logic/ScrapeTeamPitching.py"

]

print(f" Starting scrape pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
start_time = time.time()

for script in scripts:
    print(f"\n Running {script}...")
    try:
        result = subprocess.run(["python", script], check=True)
        print(f" {script} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f" Error running {script}: {e}")
        break

end_time = time.time()
elapsed = round(end_time - start_time, 2)
print(f"\n Scrape pipeline finished in {elapsed} seconds.")
