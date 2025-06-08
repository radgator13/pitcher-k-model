# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import datetime
import unidecode
import re
from rapidfuzz import process, fuzz

st.set_page_config(page_title="Strikeout Predictions", layout="wide")
if st.button("🔄 Clear cache and reload"):
    st.cache_data.clear()


# === Utility Functions ===
def normalize(text):
    return unidecode.unidecode(str(text)).lower().strip()

def normalize_col(col):
    return normalize(col).replace("’", "'").replace("‘", "'").replace("`", "'")

def to_initial_last(full_name):
    parts = full_name.split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) >= 2 else full_name

def clean_pitcher_name(name):
    return re.sub(r"\(.*?\)", "", str(name)).strip()

def get_mode_line(x):
    return x.mode().iloc[0] if not x.mode().empty else None

def get_confidence(pred, line):
    return round(abs(pred - line), 2) if not pd.isna(line) else None

def render_confidence(value):
    if pd.isna(value): return ""
    if value >= 2.0: return "🔥🔥🔥🔥🔥"
    elif value >= 1.6: return "🔥🔥🔥🔥"
    elif value >= 1.1: return "🔥🔥🔥"
    elif value >= 0.6: return "🔥🔥"
    elif value > 0.0: return "🔥"
    else: return ""

tab1, tab2, tab3 = st.tabs([
    "📈 Today's Predictions",
    "📊 Model Results vs Actual Ks",
    "🗓️ Backfill Results"
])


with tab1:
    try:
        st.markdown("### 📈 Strikeout Predictions for Today")

        selected_date = st.date_input("📅 Select date", value=datetime.date.today())
        date_str = selected_date.strftime("%Y-%m-%d")

        prediction_path = f"predictions/{date_str}/strikeouts_master.csv"
        odds_path = "data/betonline_pitcher_props.csv"

        if not os.path.exists(prediction_path) or not os.path.exists(odds_path):
            st.warning("Required files not found.")
            st.stop()

        pred_df = pd.read_csv(prediction_path)
        odds_df = pd.read_csv(odds_path)

        pitcher_col = next((c for c in pred_df.columns if normalize(c) in ["pitcher", "starting_pitcher"]), None)
        if pitcher_col is None:
            st.error("No pitcher column found.")
            st.stop()

        pred_df["pitcher_key"] = pred_df[pitcher_col].apply(lambda x: normalize(clean_pitcher_name(x)).strip())

        odds_df = odds_df[odds_df["market"].str.lower() == "pitcher_strikeouts"].copy()
        odds_df["description"] = odds_df["description"].astype(str)
        odds_df["pitcher_key"] = odds_df["description"].apply(lambda x: normalize(clean_pitcher_name(x)).strip())
        odds_df["line"] = pd.to_numeric(odds_df["line"], errors="coerce")

        line_df = odds_df.groupby("pitcher_key", as_index=False)["line"].agg(get_mode_line)
        line_df = line_df.rename(columns={"line": "vegas_line"})

        merged = pred_df.merge(line_df, on="pitcher_key", how="left")
        merged["🔥 Confidence"] = merged.apply(
            lambda row: render_confidence(get_confidence(row.get("Predicted K"), row.get("vegas_line"))),
            axis=1
        )
        merged["date"] = selected_date

        col_map = {c.lower(): c for c in merged.columns}
        output_df = merged[[
            col_map["date"],
            col_map.get("team", "Team"),
            col_map.get("opponent", "Opponent"),
            pitcher_col,
            col_map.get("predicted k", "Predicted K"),
            "vegas_line",
            "🔥 Confidence"
        ]].rename(columns={
            pitcher_col: "Pitcher",
            "vegas_line": "Vegas Line",
            col_map.get("team", "Team"): "Team",
            col_map.get("opponent", "Opponent"): "Opponent"
        })

        output_df = output_df.sort_values("Vegas Line", ascending=False)

        st.markdown("### 📊 Final Output Table")
        st.dataframe(output_df, use_container_width=True)

        if len(output_df) > 0:
            if st.button("📥 Generate & Save CSV"):
                try:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    folder = f"predictions/{date_str}"
                    os.makedirs(folder, exist_ok=True)

                    full_path = f"{folder}/strikeouts_{timestamp}.csv"
                    output_df.to_csv(full_path, index=False)

                    master_path = f"{folder}/strikeouts_master.csv"
                    current_complete = output_df["Vegas Line"].notna().sum()

                    if os.path.exists(master_path):
                        existing_df = pd.read_csv(master_path)
                        existing_complete = existing_df["Vegas Line"].notna().sum()
                    else:
                        existing_complete = -1

                    if current_complete > existing_complete:
                        output_df.to_csv(master_path, index=False)
                        st.success(f"📊 Master updated: {current_complete} props matched (was {existing_complete})")
                    else:
                        st.info(f"✅ Master kept: {existing_complete} props matched is still best")

                    with open(full_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download This CSV",
                            data=f,
                            file_name=os.path.basename(full_path),
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"CSV save failed: {e}")
        else:
            st.info("No data to export.")

    except Exception as e:
        st.error(f"❌ Tab 1 failed: {e}")




























with tab2:
    try:
        st.markdown("### 🧾 Model Predictions vs Actual Strikeouts")
        date_dirs = sorted(d for d in os.listdir("predictions") if os.path.isdir(os.path.join("predictions", d)))
        selected_date = st.selectbox("📅 Select date to compare", date_dirs)

        pred_path = f"predictions/{selected_date}/strikeouts_master.csv"
        boxscore_path = "data/pitching_through_yesterday.csv"

        pred_df = pd.read_csv(pred_path)
        boxscore_df = pd.read_csv(boxscore_path)

        boxscore_df["GameDate"] = pd.to_datetime(boxscore_df["GameDate"]).dt.date
        boxscore_df["pitcher_key"] = boxscore_df["Pitcher"].apply(lambda x: normalize(clean_pitcher_name(x)))

        pred_df["date"] = pd.to_datetime(pred_df["date"]).dt.date
        pred_df["pitcher_key"] = pred_df["Pitcher"].apply(lambda x: normalize(to_initial_last(x)))

        col_map = {normalize_col(c): c for c in pred_df.columns}
        pred_k_col = next((c for k, c in col_map.items() if "predicted" in k and "k" in k), None)
        vegas_line_col = next((c for k, c in col_map.items() if "vegas" in k and "line" in k), None)

        if not pred_k_col or not vegas_line_col:
            st.error("❌ Required columns not found.")
            st.stop()

        compare_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
        actuals = boxscore_df[boxscore_df["GameDate"] == compare_date]
        actuals_grouped = actuals[["pitcher_key", "K"]].groupby("pitcher_key", as_index=False).agg({"K": "max"})

        merged = pred_df.merge(actuals_grouped, on="pitcher_key", how="left")
        merged["Predicted K"] = merged[pred_k_col]
        merged["Vegas Line"] = merged[vegas_line_col]
        merged["Actual K"] = merged["K"]

        merged["Confidence"] = (merged["Predicted K"] - merged["Vegas Line"]).abs().round(2)

        def fireball_rating(conf):
            if conf >= 2.0: return 5
            elif conf >= 1.6: return 4
            elif conf >= 1.1: return 3
            elif conf >= 0.6: return 2
            elif conf > 0.0: return 1
            return 0

        def render_confidence(conf):
            return "🔥" * fireball_rating(conf)

        merged["🔥 Confidence"] = merged["Confidence"].apply(render_confidence)
        merged["Fireball Level"] = merged["Confidence"].apply(fireball_rating)

        # ✅ Add confidence level slider
        min_fireballs = st.slider("🔥 Minimum Confidence Level (Fireballs)", 1, 5, 1)
        merged = merged[merged["Fireball Level"] >= min_fireballs]

        def model_pick(row):
            if pd.isna(row["Predicted K"]) or pd.isna(row["Vegas Line"]):
                return "N/A"
            return "Over" if row["Predicted K"] > row["Vegas Line"] else "Under" if row["Predicted K"] < row["Vegas Line"] else "Push"

        def result_eval(row):
            if pd.isna(row["Actual K"]) or pd.isna(row["Vegas Line"]):
                return "NO DATA"
            if row["Model Pick"] == "Over":
                return "HIT" if row["Actual K"] > row["Vegas Line"] else "MISS"
            elif row["Model Pick"] == "Under":
                return "HIT" if row["Actual K"] < row["Vegas Line"] else "MISS"
            return "NO DATA"

        merged["Model Pick"] = merged.apply(model_pick, axis=1)
        merged["Result"] = merged.apply(result_eval, axis=1)

        final = merged[[ 
            "date", "Pitcher", "Model Pick", "🔥 Confidence",
            "Vegas Line", "Predicted K", "Actual K", "Result"
        ]]

        st.dataframe(final, use_container_width=True)

        hits = (final["Result"] == "HIT").sum()
        misses = (final["Result"] == "MISS").sum()
        total = hits + misses
        hit_rate = f"{(hits / total * 100):.1f}%" if total > 0 else "N/A"

        st.markdown(f"**✅ HITs:** {hits} ❌ MISSes: {misses} 🎯 Hit Rate: {hit_rate}")

    except Exception as e:
        st.error("❌ Failed to compare predictions.")




        # === Tab 3: Backfill Results Explorer ===
with tab3:
    try:
        st.markdown("### 🗓️ Model Backfill Results by Date")

        # === Load backfill data (cache disabled for fresh load)
        def load_backfill_data():
            df = pd.read_csv("data/model_backfill_results.csv")
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            return df

        backfill_df = load_backfill_data()

        if backfill_df.empty:
            st.warning("No backfill results found.")
        else:
            # === Select date
            st.write("📆 Max date in backfill:", backfill_df["Date"].max())
            available_dates = sorted(backfill_df["Date"].unique(), reverse=True)
            default_date = datetime.date.today() - datetime.timedelta(days=1)
            default_date = max([d for d in available_dates if d <= default_date], default=available_dates[0])

            selected_date = st.date_input(
                "📅 Select a date",
                value=default_date,
                min_value=min(available_dates),
                max_value=max(available_dates)
)


            # === Vegas Line slider
            vegas_line = st.slider("🎯 Adjust comparison line (Vegas Line)", 0.0, 15.0, 4.5, 0.5)

            # === Filter rows
            filtered = backfill_df[backfill_df["Date"] == selected_date].copy()
            if filtered.empty:
                st.warning(f"No results for {selected_date}")
            else:
                # === Compute Confidence and Model Pick based on slider
                filtered["Vegas Line"] = vegas_line
                filtered["Confidence"] = (filtered["Predicted K"] - vegas_line).abs().round(2)
                filtered["Model Pick"] = filtered.apply(
                    lambda row: "Over" if row["Predicted K"] > vegas_line else "Under", axis=1
                )

                # === Evaluate Result if Actual K exists
                def result_eval(row):
                    if pd.isna(row["Actual K"]):
                        return "NO DATA"
                    if row["Model Pick"] == "Over" and row["Actual K"] > vegas_line:
                        return "HIT"
                    if row["Model Pick"] == "Under" and row["Actual K"] < vegas_line:
                        return "HIT"
                    return "MISS"

                filtered["Result"] = filtered.apply(result_eval, axis=1)

                # === Add fireball rendering for confidence
                def render_confidence(conf):
                    if pd.isna(conf): return ""
                    if conf >= 2.0: return "🔥🔥🔥🔥🔥"
                    elif conf >= 1.6: return "🔥🔥🔥🔥"
                    elif conf >= 1.1: return "🔥🔥🔥"
                    elif conf >= 0.6: return "🔥🔥"
                    elif conf > 0.0: return "🔥"
                    else: return ""

                filtered["🔥"] = filtered["Confidence"].apply(render_confidence)

                # === Final columns for display
                display_df = filtered[[
                    "Date", "Team", "Opponent", "Pitcher",
                    "Predicted K", "Vegas Line", "Confidence", "🔥",
                    "Model Pick", "Actual K", "Result"
                ]]

                st.markdown(f"### Results for {selected_date} ({len(display_df)} rows)")
                st.dataframe(display_df, use_container_width=True)

                # === Summary
                hits = (display_df["Result"] == "HIT").sum()
                misses = (display_df["Result"] == "MISS").sum()
                total = hits + misses
                if total > 0:
                    hit_rate = f"{(hits / total * 100):.1f}%"
                    st.markdown(f"**✅ HITs:** {hits} ❌ MISSes: {misses} 🎯 Hit Rate: {hit_rate}")

    except Exception as e:
        st.error(f"❌ Failed to load backfill data: {e}")



