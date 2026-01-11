"""
Compare v3 with weather features vs v3 without weather and v2.
Measures the specific impact of weather data on prediction accuracy.

Usage:
    python src/scripts/compare_weather_impact.py [--train-week 14] [--outdoor-only]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys
import warnings

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, REPORTS_DIR, ensure_dir  # noqa: E402
from models.archive.model_v2 import NFLHybridModelV2 as V2Model  # noqa: E402
from models.model_v3 import NFLHybridModelV3 as V3Model  # noqa: E402


def fmt_improve(base: float, new: float) -> float:
    """Calculate improvement percentage."""
    return (base - new) / base * 100.0 if base and base == base else float("nan")


def train_v3_without_weather(workbook_path: str, train_through_week: int, outdoor_only: bool = False) -> dict:
    """
    Train v3 model with weather features excluded.
    
    This is done by temporarily modifying the candidate features.
    """
    import pandas as pd
    
    # Temporarily patch the _candidate_features method to exclude weather
    original_method = V3Model._candidate_features
    original_load_v3 = V3Model.load_workbook
    
    # Apply outdoor-only filtering if requested
    if outdoor_only:
        def load_workbook_outdoor_v3(self):
            games, team_games, odds = original_load_v3(self)
            if "is_indoor" in games.columns:
                games = games[games["is_indoor"] == 0].copy()
                team_games = team_games[team_games["game_id"].isin(games["game_id"])].copy()
                if "game_id" in odds.columns:
                    odds = odds[odds["game_id"].isin(games["game_id"])].copy()
            return games, team_games, odds
        V3Model.load_workbook = load_workbook_outdoor_v3
    
    def _candidate_features_no_weather(team_games: pd.DataFrame) -> list:
        candidates = [
            # Score-based metrics
            "points_for", "points_against",
            # Play-level metrics
            "plays", "seconds_per_play", "yards_per_play", "yards_per_play_allowed",
            # Rushing
            "rush_att", "rush_yds", "rush_ypa", "rush_td",
            # Turnovers
            "turnovers_give", "turnovers_take",
            "ints_thrown", "ints_got", "fumbles_lost", "fumbles_recovered",
            # Pass rush
            "sacks_allowed", "sacks_made",
            "pressures_made", "pressures_allowed",
            "hurries_made", "hurries_allowed",
            # Blitzes
            "blitzes_sent", "blitzes_faced",
            # Penalties
            "penalties", "penalty_yards",
            # Opponent efficiency
            "opp_first_downs", "opp_first_downs_rush", "opp_first_downs_pass", "opp_first_downs_pen",
            "opp_3d_att", "opp_3d_conv", "opp_3d_pct",
            "opp_4d_att", "opp_4d_conv", "opp_4d_pct",
            # Special teams
            "punts", "punt_yards", "punt_yards_per_punt", "punts_blocked",
            # NO WEATHER FEATURES
        ]
        return [c for c in candidates if c in team_games.columns]
    
    # Monkey-patch temporarily (remove @staticmethod wrapper)
    V3Model._candidate_features = staticmethod(_candidate_features_no_weather)

    try:
        model = V3Model(workbook_path=workbook_path, window=8, model_type="randomforest")
        report = model.fit(train_through_week=train_through_week)
    finally:
        # Restore original methods (ensure staticmethod wrapper)
        try:
            V3Model._candidate_features = staticmethod(original_method)
        except Exception:
            V3Model._candidate_features = original_method
        if outdoor_only:
            V3Model.load_workbook = original_load_v3
    
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare weather impact on v3 model accuracy")
    parser.add_argument("--train-week", type=int, default=14, help="Train through week N (default: 14)")
    parser.add_argument("--outdoor-only", action="store_true", help="Restrict to outdoor games only")
    args = parser.parse_args()

    workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
    ensure_dir(REPORTS_DIR)

    print("\n" + "="*80)
    print("WEATHER IMPACT ANALYSIS")
    print("="*80)
    print(f"Workbook: {workbook}")
    print(f"Train through week: {args.train_week}\n")
    print(f"Outdoor only: {'YES' if args.outdoor_only else 'NO'}\n")

    variants = []

    def fmt_mae(v) -> str:
        try:
            v = float(v)
            return f"{v:.3f}" if v == v else "N/A"
        except Exception:
            return "N/A"

    # v2 baseline (no weather, momentum bug)
    print("Training v2 (baseline - no weather, momentum bug)...")
    # Apply outdoor-only filtering for v2 if requested
    original_load_v2 = V2Model.load_workbook
    if args.outdoor_only:
        def load_workbook_outdoor_v2(self):
            games, team_games, odds = original_load_v2(self)
            if "is_indoor" in games.columns:
                games = games[games["is_indoor"] == 0].copy()
                team_games = team_games[team_games["game_id"].isin(games["game_id"])].copy()
                if "game_id" in odds.columns:
                    odds = odds[odds["game_id"].isin(games["game_id"])].copy()
            return games, team_games, odds
        V2Model.load_workbook = load_workbook_outdoor_v2
    v2 = V2Model(workbook_path=str(workbook), window=8, model_type="randomforest")
    start = time.perf_counter()
    v2_report = v2.fit(train_through_week=args.train_week)
    v2_time = time.perf_counter() - start
    if args.outdoor_only:
        V2Model.load_workbook = original_load_v2
    variants.append(("v2_baseline", v2_report, v2_time, v2_report.get("n_features", 0), False))
    print(f"  Margin MAE: {fmt_mae(v2_report['margin_MAE_test'])}, Total MAE: {fmt_mae(v2_report['total_MAE_test'])}\n")

    # v3 without weather (fixed momentum, no weather)
    print("Training v3 WITHOUT weather (fixed momentum, no weather)...")
    start = time.perf_counter()
    v3_no_weather_report = train_v3_without_weather(str(workbook), args.train_week, outdoor_only=args.outdoor_only)
    v3_no_weather_time = time.perf_counter() - start
    variants.append(("v3_no_weather", v3_no_weather_report, v3_no_weather_time, 
                    v3_no_weather_report.get("n_features", 0), False))
    print(f"  Margin MAE: {fmt_mae(v3_no_weather_report['margin_MAE_test'])}, "
          f"Total MAE: {fmt_mae(v3_no_weather_report['total_MAE_test'])}\n")

    # v3 with weather (full feature set)
    print("Training v3 WITH weather (fixed momentum + weather)...")
    # Apply outdoor-only filtering by patching load_workbook if requested
    original_load_v3 = V3Model.load_workbook
    if args.outdoor_only:
        def load_workbook_outdoor_v3(self):
            games, team_games, odds = original_load_v3(self)
            if "is_indoor" in games.columns:
                games = games[games["is_indoor"] == 0].copy()
                team_games = team_games[team_games["game_id"].isin(games["game_id"])].copy()
                if "game_id" in odds.columns:
                    odds = odds[odds["game_id"].isin(games["game_id"])].copy()
            return games, team_games, odds
        V3Model.load_workbook = load_workbook_outdoor_v3
    v3 = V3Model(workbook_path=str(workbook), window=8, model_type="randomforest")
    start = time.perf_counter()
    v3_report = v3.fit(train_through_week=args.train_week)
    v3_time = time.perf_counter() - start
    # Restore patch if applied
    if args.outdoor_only:
        V3Model.load_workbook = original_load_v3
    variants.append(("v3_with_weather", v3_report, v3_time, v3_report.get("n_features", 0), True))
    print(f"  Margin MAE: {fmt_mae(v3_report['margin_MAE_test'])}, Total MAE: {fmt_mae(v3_report['total_MAE_test'])}\n")

    # Calculate improvements
    v2_margin = v2_report["margin_MAE_test"]
    v2_total = v2_report["total_MAE_test"]
    v3_no_wx_margin = v3_no_weather_report["margin_MAE_test"]
    v3_no_wx_total = v3_no_weather_report["total_MAE_test"]
    v3_wx_margin = v3_report["margin_MAE_test"]
    v3_wx_total = v3_report["total_MAE_test"]

    print("="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    print("\n📊 Margin (Spread) Prediction MAE:")
    print(f"  v2 baseline:          {fmt_mae(v2_margin)}")
    print(f"  v3 no weather:        {fmt_mae(v3_no_wx_margin)} ({fmt_improve(v2_margin, v3_no_wx_margin):+.1f}% vs v2)")
    print(f"  v3 with weather:      {fmt_mae(v3_wx_margin)} ({fmt_improve(v2_margin, v3_wx_margin):+.1f}% vs v2)")
    print(f"  Weather impact:       {fmt_improve(v3_no_wx_margin, v3_wx_margin):+.1f}%")

    print("\n📊 Total Points Prediction MAE:")
    print(f"  v2 baseline:          {fmt_mae(v2_total)}")
    print(f"  v3 no weather:        {fmt_mae(v3_no_wx_total)} ({fmt_improve(v2_total, v3_no_wx_total):+.1f}% vs v2)")
    print(f"  v3 with weather:      {fmt_mae(v3_wx_total)} ({fmt_improve(v2_total, v3_wx_total):+.1f}% vs v2)")
    print(f"  Weather impact:       {fmt_improve(v3_no_wx_total, v3_wx_total):+.1f}%")

    print("\n⚙️ Model Complexity:")
    for name, rep, tsec, nfeat, has_wx in variants:
        print(f"  {name:20s}: {nfeat:4d} features, {tsec:5.2f}s train time")

    # Write detailed report
    report_path = REPORTS_DIR / "WEATHER_IMPACT_ANALYSIS.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Weather Impact Analysis\n\n")
        f.write(f"Training data: through week {args.train_week}\n")
        f.write(f"Test data: weeks {args.train_week + 1}+\n\n")
        
        f.write("## Executive Summary\n\n")
        weather_margin_impact = fmt_improve(v3_no_wx_margin, v3_wx_margin)
        weather_total_impact = fmt_improve(v3_no_wx_total, v3_wx_total)
        
        if weather_margin_impact > 0 or weather_total_impact > 0:
            f.write("✅ **Weather features improved model accuracy.**\n\n")
        else:
            f.write("⚠️ **Weather features did not improve accuracy in this test.**\n\n")
        
        f.write(f"- **Margin prediction**: {weather_margin_impact:+.1f}% improvement\n")
        f.write(f"- **Total prediction**: {weather_total_impact:+.1f}% improvement\n")
        f.write(f"- **Feature count increase**: {v3_report['n_features']} (with weather) vs "
                f"{v3_no_weather_report['n_features']} (without)\n\n")
        
        f.write("## Detailed Results\n\n")
        f.write("### Margin (Spread) Prediction\n\n")
        f.write("| Model | MAE | vs v2 | vs v3 no-weather |\n")
        f.write("|-------|-----|-------|------------------|\n")
        f.write(f"| v2 baseline | {fmt_mae(v2_margin)} | - | - |\n")
        f.write(f"| v3 no weather | {fmt_mae(v3_no_wx_margin)} | {fmt_improve(v2_margin, v3_no_wx_margin):+.1f}% | - |\n")
        f.write(f"| v3 with weather | {fmt_mae(v3_wx_margin)} | {fmt_improve(v2_margin, v3_wx_margin):+.1f}% | "
            f"{fmt_improve(v3_no_wx_margin, v3_wx_margin):+.1f}% |\n\n")
        
        f.write("### Total Points Prediction\n\n")
        f.write("| Model | MAE | vs v2 | vs v3 no-weather |\n")
        f.write("|-------|-----|-------|------------------|\n")
        f.write(f"| v2 baseline | {fmt_mae(v2_total)} | - | - |\n")
        f.write(f"| v3 no weather | {fmt_mae(v3_no_wx_total)} | {fmt_improve(v2_total, v3_no_wx_total):+.1f}% | - |\n")
        f.write(f"| v3 with weather | {fmt_mae(v3_wx_total)} | {fmt_improve(v2_total, v3_wx_total):+.1f}% | "
            f"{fmt_improve(v3_no_wx_total, v3_wx_total):+.1f}% |\n\n")
        
        f.write("## Interpretation\n\n")
        f.write("**MAE (Mean Absolute Error)** measures average prediction error in points:\n")
        f.write("- Lower is better\n")
        f.write("- Margin MAE ~10 means spread predictions are off by 10 points on average\n")
        f.write("- For betting value, need MAE well below typical line movement (~2-3 points)\n\n")
        
        f.write("**Weather features** include:\n")
        f.write("- Temperature, wind speed/gusts, precipitation, humidity, pressure\n")
        f.write("- Each generates 6 momentum features (rolling, EMA, trend, volatility, season avg, ratio)\n")
        f.write("- Plus home/away deltas for each momentum type\n")
        f.write("- Indoor stadium flag to discount weather impact for dome games\n\n")
        
        f.write("## Next Steps\n\n")
        if weather_margin_impact > 0 or weather_total_impact > 0:
            f.write("1. ✓ Weather integration successful\n")
            f.write("2. Consider weather interaction terms (wind × pass rate, temp × dome flag)\n")
            f.write("3. Separate outdoor-only models may show stronger weather signal\n")
            f.write("4. Hyperparameter tuning with weather features enabled\n")
        else:
            f.write("1. Weather features not yet providing value—possible reasons:\n")
            f.write("   - Insufficient training data for weather signal to emerge\n")
            f.write("   - Weather effect size smaller than other noise sources\n")
            f.write("   - Need interaction terms (weather × team style)\n")
            f.write("   - RF may need more trees/depth to capture weather patterns\n")
            f.write("2. Try outdoor games only (exclude dome teams)\n")
            f.write("3. Add feature engineering (extreme weather flags, wind bins)\n")
            f.write("4. Test on larger datasets or specific weather-sensitive matchups\n")

    print(f"\n📄 Detailed report saved: {report_path}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
