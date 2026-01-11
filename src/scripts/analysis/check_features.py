from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR

workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
tg = pd.read_excel(workbook, sheet_name='team_games')

# Current candidate features in model_v2
current = {
    "plays", "seconds_per_play", "yards_per_play", "yards_per_play_allowed",
    "rush_att", "rush_yds", "rush_ypa", "rush_td",
    "turnovers_give", "turnovers_take",
    "ints_thrown", "ints_got", "fumbles_lost", "fumbles_recovered",
    "sacks_allowed", "sacks_made",
    "pressures_made", "pressures_allowed",
    "hurries_made", "hurries_allowed",
    "blitzes_sent", "blitzes_faced",
    "penalties", "penalty_yards",
    "opp_first_downs", "opp_first_downs_rush", "opp_first_downs_pass", "opp_first_downs_pen",
    "opp_3d_att", "opp_3d_conv", "opp_3d_pct",
    "opp_4d_att", "opp_4d_conv", "opp_4d_pct",
    "punts", "punt_yards", "punt_yards_per_punt", "punts_blocked",
}

available = set(tg.columns) - {"game_id", "team", "opponent", "is_home (0/1)", "points_for", "points_against"}

missing = available - current

print(f"Currently using: {len(current)} features")
print(f"Available: {len(available)} features")
print(f"Missing (not using): {len(missing)} features\n")

print("=== MISSING HIGH-VALUE FEATURES (NOT USED) ===")
missing_list = sorted(list(missing))
for feat in missing_list:
    # Check for NaN values
    nan_pct = (tg[feat].isna().sum() / len(tg)) * 100
    if nan_pct < 50:  # Only show features that aren't mostly NaN
        print(f"  {feat:35s} (NaN: {nan_pct:5.1f}%)")

print("\n=== ALL TEAM_GAMES COLUMNS ===")
for col in sorted(tg.columns):
    nan_pct = (tg[col].isna().sum() / len(tg)) * 100
    status = "CURRENT" if col in current else "MISSING"
    print(f"  {col:35s} | {status:7s} | NaN: {nan_pct:5.1f}%")
