"""
Run predictions on upcoming games marked as prediction targets.

This script:
1. Loads games marked with is_prediction_target=1
2. Trains v3 model through specified week
3. Generates predictions for upcoming games
4. Logs predictions to prediction_log.csv

Usage:
    python src/scripts/predict_upcoming.py --week 19 --train-through 18
    python src/scripts/predict_upcoming.py --week 19 --train-through 18 --variants tuned stacking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import re
import sqlite3
import pandas as pd
from datetime import datetime
from models.model_v3 import NFLHybridModelV3
from utils.paths import DATA_DIR


def main():
    parser = argparse.ArgumentParser(description="Predict upcoming games")
    parser.add_argument("--week", type=int, required=True, help="Week of games to predict")
    parser.add_argument("--train-through", type=int, required=True, help="Train through this week")
    parser.add_argument("--workbook", type=str,
                       default="data/nfl_2025_model_data_with_moneylines.xlsx",
                       help="Path to workbook")
    parser.add_argument("--variants", nargs="+", 
                       choices=["default", "tuned", "stacking"],
                       default=["default"],
                       help="Model variants to run")
    parser.add_argument("--output", type=str,
                       default="outputs/prediction_log.csv",
                       help="Path to prediction log")
    parser.add_argument("--playoffs", action="store_true",
                        help="Predict only playoff games among targets (game_id like 'YYYY_RR_AAA_BBB')")
    args = parser.parse_args()
    
    workbook_path = Path(args.workbook)

    # Prefer SQLite for upcoming games if available; fallback to workbook targets
    target_games = pd.DataFrame()
    db_path = DATA_DIR / "nfl_model.db"
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                query = (
                    "SELECT game_id, season, week, away_team, home_team "
                    "FROM games "
                    "WHERE week = ? AND (home_score IS NULL OR away_score IS NULL)"
                )
                target_games = pd.read_sql_query(query, conn, params=(args.week,))
                source = "SQLite"
        except Exception as e:
            print(f"Warning: SQLite fetch failed ({e}); falling back to workbook targets.")
            target_games = pd.DataFrame()

    if target_games.empty:
        if not workbook_path.exists():
            print(f"Error: Neither SQLite nor workbook provided upcoming games (missing {workbook_path}).")
            sys.exit(1)
        print(f"Loading workbook: {workbook_path}")
        games_df = pd.read_excel(workbook_path, sheet_name="games")
        if "is_prediction_target" not in games_df.columns:
            print("Error: No is_prediction_target column found. Run fetch_upcoming_games.py first.")
            sys.exit(1)
        target_games = games_df[
            (games_df["is_prediction_target"] == 1) & 
            (games_df["week"] == args.week)
        ][[c for c in ["game_id","season","week","away_team","home_team"] if c in games_df.columns]]
        source = "Workbook"

    # If playoffs flag is set, filter to playoff-format game_ids (e.g., 2025_01_GNB_CHI)
    if args.playoffs and "game_id" in target_games.columns:
        playoff_mask = target_games["game_id"].astype(str).str.match(r"^\d{4}_\d{2}_.+")
        target_games = target_games[playoff_mask]

    if target_games.empty:
        print(f"No upcoming games found for week {args.week} from {source}.")
        print(f"Run: python src/scripts/fetch_upcoming_games.py --week {args.week}")
        sys.exit(1)
    
    print(f"\nFound {len(target_games)} game(s) to predict for week {args.week} from {source}{' (playoffs only)' if args.playoffs else ''}:")
    for _, game in target_games.iterrows():
        print(f"  {game['away_team']} @ {game['home_team']}")
    
    # Initialize prediction log
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if output_path.exists():
        pred_log = pd.read_csv(output_path)
    else:
        pred_log = pd.DataFrame()
    run_entries = []
    
    # Run predictions for each variant
    for variant in args.variants:
        print(f"\n{'='*70}")
        print(f"Training {variant} variant (train through week {args.train_through})...")
        print(f"{'='*70}")
        
        # Configure model based on variant
        if variant == "tuned":
            rf_params = {
                "n_estimators": 200,
                "max_depth": 12,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "random_state": 42,
                "n_jobs": -1
            }
            stack = False
        elif variant == "stacking":
            rf_params = None
            stack = True
        else:  # default
            rf_params = None
            stack = False
        
        # Train model with full data (SQLite preferred for 2020-2025 + weather)
        model = NFLHybridModelV3(workbook_path=str(workbook_path), window=8, model_type="randomforest", prefer_sqlite=True)
        fit_result = model.fit(
            train_through_week=args.train_through,
            rf_params_margin=rf_params,
            rf_params_total=rf_params,
            stack_models=stack
        )
        
        if fit_result['margin_MAE_test'] is not None:
            print(f"  Test MAE: Margin {fit_result['margin_MAE_test']:.3f}, Total {fit_result['total_MAE_test']:.3f}")
        else:
            print(f"  No test data (training through all completed games)")
        
        # Generate predictions for each target game
        for idx, game in target_games.iterrows():
            game_id = game["game_id"]
            away_team = game["away_team"]
            home_team = game["home_team"]
            week = game["week"]
            
            print(f"\n  Predicting: {away_team} @ {home_team} (Week {week})")
            
            try:
                # Use predict_game for individual game prediction
                # For playoff games (week resets to 1), use week after train_through
                # For regular season games, use the actual week
                as_of_week = args.train_through + 1 if week <= args.train_through else week
                
                prediction = model.predict_game(
                    away_team=away_team,
                    home_team=home_team,
                    week=as_of_week
                )
                
                # Log prediction
                log_entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "game_id": game_id,
                    "week": week,
                    "away_team": away_team,
                    "home_team": home_team,
                    "pred_margin_home": prediction["pred_margin_home"],
                    "pred_spread_away": prediction["pred_spread_away"],
                    "pred_total": prediction["pred_total"],
                    "pred_winprob_home": prediction.get("pred_winprob_home", None),
                    "pred_winprob_away": prediction.get("pred_winprob_away", None),
                    "train_week": args.train_through,
                    "window": 8,
                    "variant": variant,
                    "model_version": "v3",
                    "stacking": 1 if stack else 0,
                    "tuned_params": 1 if rf_params else 0,
                }
                
                entry_df = pd.DataFrame([log_entry])
                pred_log = pd.concat([pred_log, entry_df], ignore_index=True)
                run_entries.append(log_entry)
                
                print(f"    Margin (home): {prediction['pred_margin_home']:+.1f}")
                print(f"    Spread (away): {prediction['pred_spread_away']:+.1f}")
                print(f"    Total: {prediction['pred_total']:.1f}")
                if "pred_winprob_home" in prediction:
                    print(f"    Win Prob (home): {prediction['pred_winprob_home']:.1%}")
            
            except Exception as e:
                print(f"    ❌ Error predicting game: {e}")
                continue
    
    # Save predictions to SQLite DB instead of CSV log
    print(f"\n{'='*70}")
    db_path = DATA_DIR / "nfl_model.db"
    try:
        import sqlite3
        with sqlite3.connect(str(db_path)) as conn:
            # Write cumulative log to 'predictions' table
            pred_log.to_sql('predictions', conn, if_exists='append', index=False)
        print(f"✅ {len(pred_log)} total predictions logged to DB: {db_path}")
    except Exception as e:
        print(f"⚠️  Failed to write predictions to DB ({db_path}): {e}")
        print(f"Fallback: saving to {output_path}")
        pred_log.to_csv(output_path, index=False)
    
    # If playoffs-only, also save a separate file with just this run's entries
    if args.playoffs:
        ts = datetime.now().strftime("%Y-%m-%d")
        try:
            # Also store this run's entries separately in DB for traceability
            with sqlite3.connect(str(db_path)) as conn:
                pd.DataFrame(run_entries).to_sql('predictions_runs', conn, if_exists='append', index=False)
            print(f"\n🗂 Saved playoffs-only run entries to DB: {db_path} (table: predictions_runs)")
        except Exception:
            playoffs_out = Path(f"outputs/predictions_playoffs_week{args.week}_{ts}.csv")
            pd.DataFrame(run_entries).to_csv(playoffs_out, index=False)
            print(f"\n🗂 Saved playoffs-only predictions to {playoffs_out}")

    print(f"\n📊 Latest predictions:")
    latest = pred_log.tail(len(target_games) * len(args.variants))
    print(latest[["game_id", "variant", "pred_spread_away", "pred_total"]].to_string(index=False))


if __name__ == "__main__":
    main()
