import subprocess

steps = [
    ("📥 Step 1: Scrape latest odds", "bet_logic/run_odds_api.py"),
    ("📥 Step 2: Scrape latest data", "pipeline_logic/Step1_Scrape_All.py"),
    ("🧱 Step 3: Build training dataset", "pipeline_logic/build_team_runs_dataset.py"),
    ("🧠 Step 4: Predict upcoming games", "pipeline_logic/predict_runs.py"),
    ("📊 Step 5: Backfill historical predictions", "pipeline_logic/backfill_predictions.py"),
    ("🔥 Step 6: Backfill pitcher K predictions", "pipeline_logic/backfill_pitcher_ks.py"),
    ("🎯 Step 7: Predict pitcher strikeouts (future)", "pipeline_logic/predict_pitcher_ks.py"),
    ("📈 Step 9: Predict team over/under picks", "pipeline_logic/predict_team_overs_and_unders.py"),
    ("📈 Step 10: Get Pitching Results", "pipeline_logic/get_pitching_results.py"),
    ("📈 Step 11: Compare Picks vs Results", "pipeline_logic/compare_picks_vs_results.py"),
    ("📈 Step 12: Backfill Model Picks", "pipeline_logic/backfill_model_picks.py"),
    ("✅ DONE! Now run: streamlit run app.py", None),
]

# Run pipeline steps
for label, script in steps:
    print(f"\n=== {label} ===")
    if script:
        result = subprocess.run(["python", script])
        if result.returncode != 0:
            print(f"❌ Error in {script}. Halting pipeline.")
            break
else:
    # All steps completed successfully
    print("\n🚀 All steps completed successfully.")

    