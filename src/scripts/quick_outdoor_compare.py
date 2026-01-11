"""Quick outdoor-only comparison for weather impact in v3."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.model_v2 import NFLHybridModelV2 as V2Model
from models.model_v3 import NFLHybridModelV3 as V3Model
import pandas as pd

workbook_path = Path(__file__).parent.parent.parent / "data" / "nfl_2025_model_data_with_moneylines.xlsx"
train_week = 14

print("Outdoor-only comparison starting...")

# Patch load_workbook for outdoor-only
orig_v2_load = V2Model.load_workbook
orig_v3_load = V3Model.load_workbook

def load_outdoor_v2(self):
    games, team_games, odds = orig_v2_load(self)
    if "is_indoor" in games.columns:
        games = games[games["is_indoor"] == 0].copy()
        team_games = team_games[team_games["game_id"].isin(games["game_id"])].copy()
        if "game_id" in odds.columns:
            odds = odds[odds["game_id"].isin(games["game_id"])].copy()
    return games, team_games, odds


def load_outdoor_v3(self):
    games, team_games, odds = orig_v3_load(self)
    if "is_indoor" in games.columns:
        games = games[games["is_indoor"] == 0].copy()
        team_games = team_games[team_games["game_id"].isin(games["game_id"])].copy()
        if "game_id" in odds.columns:
            odds = odds[odds["game_id"].isin(games["game_id"])].copy()
    return games, team_games, odds

V2Model.load_workbook = load_outdoor_v2
V3Model.load_workbook = load_outdoor_v3

# v2 baseline
v2 = V2Model(workbook_path=str(workbook_path), window=8, model_type="randomforest")
v2_report = v2.fit(train_through_week=train_week)
print(f"v2 baseline (outdoor): margin {v2_report['margin_MAE_test']:.3f}, total {v2_report['total_MAE_test']:.3f}")

# v3 without weather
original_candidate = V3Model._candidate_features

def _candidate_features_no_weather(team_games: pd.DataFrame):
    candidates = [
        "points_for", "points_against",
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
    ]
    return [c for c in candidates if c in team_games.columns]

V3Model._candidate_features = staticmethod(_candidate_features_no_weather)

v3_no = V3Model(workbook_path=str(workbook_path), window=8, model_type="randomforest")
v3_no_report = v3_no.fit(train_through_week=train_week, rf_params_margin={"n_estimators":100, "n_jobs":-1, "random_state":42}, rf_params_total={"n_estimators":100, "n_jobs":-1, "random_state":42})
print(f"v3 no weather (outdoor): margin {v3_no_report['margin_MAE_test']:.3f}, total {v3_no_report['total_MAE_test']:.3f}")

# restore candidate (wrap back as staticmethod)
V3Model._candidate_features = staticmethod(original_candidate)

# v3 with weather
v3_w = V3Model(workbook_path=str(workbook_path), window=8, model_type="randomforest")
v3_w_report = v3_w.fit(train_through_week=train_week, rf_params_margin={"n_estimators":100, "n_jobs":-1, "random_state":42}, rf_params_total={"n_estimators":100, "n_jobs":-1, "random_state":42})
print(f"v3 with weather (outdoor): margin {v3_w_report['margin_MAE_test']:.3f}, total {v3_w_report['total_MAE_test']:.3f}")

# restore load_workbook
V2Model.load_workbook = orig_v2_load
V3Model.load_workbook = orig_v3_load

# summarize improvements
imp = lambda base, new: (base - new) / base * 100.0
print("\nSUMMARY (outdoor-only):")
print(f"  v3 momentum fix vs v2: margin {imp(v2_report['margin_MAE_test'], v3_no_report['margin_MAE_test']):+.2f}%")
print(f"  v3 momentum fix vs v2: total  {imp(v2_report['total_MAE_test'], v3_no_report['total_MAE_test']):+.2f}%")
print(f"  weather vs v3 no weather: margin {imp(v3_no_report['margin_MAE_test'], v3_w_report['margin_MAE_test']):+.2f}%")
print(f"  weather vs v3 no weather: total  {imp(v3_no_report['total_MAE_test'], v3_w_report['total_MAE_test']):+.2f}%")
