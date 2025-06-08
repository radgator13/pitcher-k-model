import subprocess
import sys
import os
import shutil
from datetime import datetime
import builtins
import sys

original_print = builtins.print

def safe_print(*args, **kwargs):
    try:
        original_print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback = [str(arg).encode('ascii', errors='ignore').decode() for arg in args]
        original_print(*fallback, **kwargs)

builtins.print = safe_print

# === Ordered scripts to run ===
scripts = [
    "bet_logic/Step_1_get_BETONLINE_odds.py",
    "bet_logic/Step_3_check_event_id_and_merge.py",
    "bet_logic/Step_2_flatten_odds_api_events.py",    
    "bet_logic/Step_4_final_merged_readable_odds_api.py"
]

print("[INFO] Starting Odds API prop data pipeline...\n")

for script in scripts:
    if not os.path.exists(script):
        print(f"[ERR] Script not found: {script}")
        sys.exit(1)

    print(f"[RUN] Running: {script}")
    try:
        result = subprocess.run(
            ["python", script],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        print(f"[OK] Finished: {script}")
        output = result.stdout if result.stdout else "[WARN] No stdout captured."
        print(output)

        if "No pitcher props found." in output or "No batter props found." in output:
            print("[WARN] Pitcher and/or batter props were not available in the Odds API response.")
            print("[INFO] Try running again closer to game time (3–5 hours before first pitch).")

    except subprocess.CalledProcessError as e:
        print(f"[ERR] Error running {script}:\n")
        print(e.stderr if e.stderr else "[ERR] No error details returned.")
        sys.exit(1)

# === Archive handling ===
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
today_folder = datetime.now().strftime("%Y-%m-%d")
data_dir = "data"
archive_dir = os.path.join("archive", today_folder)

os.makedirs(data_dir, exist_ok=True)
os.makedirs(archive_dir, exist_ok=True)

base_filename = "clean_all_props_flat.csv"
original_path = os.path.join(data_dir, base_filename)

timestamped_filename = f"clean_all_props_flat_{timestamp}.csv"
timestamped_path = os.path.join(data_dir, timestamped_filename)
archived_path = os.path.join(archive_dir, timestamped_filename)

if os.path.exists(original_path):
    prev_stamp = datetime.fromtimestamp(os.path.getmtime(original_path)).strftime("%Y%m%d_%H%M%S")
    prev_archived_name = f"clean_all_props_flat_{prev_stamp}.csv"
    prev_archive_path = os.path.join(archive_dir, prev_archived_name)
    shutil.copy(original_path, prev_archive_path)
    print(f"[INFO] Archived previous flat file: {prev_archive_path}")

if os.path.exists(original_path):
    shutil.copy(original_path, timestamped_path)
    shutil.copy(original_path, archived_path)
    print(f"[OK] Saved: {timestamped_path}")
    print(f"[OK] Archived to: {archived_path}")
else:
    print("[WARN] clean_all_props_flat.csv not found — skipping archive copy.")

# # === Git automation ===
# print("\n[GIT] Checking repository...")

# # Step 1: Git init if not already
# if not os.path.exists(".git"):
#     print("[GIT] Initializing Git repository...")
#     subprocess.run(["git", "init"], check=True)

# # Step 2: Add remote if not already set
# remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout
# if "origin" not in remotes:
#     print("[GIT] Adding remote origin...")
#     subprocess.run([
#         "git", "remote", "add", "origin",
#         "https://github.com/radgator13/odds-api-analyze.git"
#     ], check=True)
# else:
#     print("[GIT] Remote 'origin' already exists.")

# # Step 3: Commit and push
# try:
#     print("[GIT] Adding all changes...")
#     subprocess.run(["git", "add", "."], check=True)

#     commit_msg = f"Auto push from run_odds_api at {timestamp}"
#     print(f"[GIT] Committing: {commit_msg}")
#     subprocess.run(["git", "commit", "-m", commit_msg], check=True)

#     print("[GIT] Pushing to GitHub...")
#     subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
#     print("[GIT] ✅ Push successful.")
# except subprocess.CalledProcessError as e:
#     print("[GIT] ❌ Git push failed.")
#     print(e)

print("\n[DONE] All steps completed successfully.")

