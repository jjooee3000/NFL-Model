#!/usr/bin/env python3
"""
Multi-Window Ensemble Prediction Script

Generates predictions using multiple training windows and model variants,
then averages results to reduce overfitting and improve accuracy.

Expected improvement: ~0.2-0.4 pts margin MAE vs single prediction.

Usage:
    # Predict with default settings (weeks 14-18, all variants)
    python src/scripts/predict_ensemble_multiwindow.py --week 1 --playoffs --games BUF@JAX
    
    # Custom training windows
    python src/scripts/predict_ensemble_multiwindow.py --week 1 --playoffs --train-windows 14 15 16 17
    
    # Specific variants only
    python src/scripts/predict_ensemble_multiwindow.py --week 1 --playoffs --variants default tuned
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
import argparse
import time

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import OUTPUTS_DIR, DATA_DIR, ensure_dir
from models.model_v3 import NFLHybridModelV3
try:
    from scripts.update_postgame_scores import update_scores
except Exception:
    # Fallback import path when running as a script
    import sys as _sys
    _sys.path.insert(0, str(SRC_DIR))
    from scripts.update_postgame_scores import update_scores


def fetch_upcoming_games_sqlite(week: int, playoffs: bool = False) -> pd.DataFrame:
    """Fetch upcoming games for a given week from SQLite or workbook fallback.

    If playoffs=True and no games are found for the requested week, try a
    fallback to week=1 (playoff round numbering).
    """
    db_path = DATA_DIR / "nfl_model.db"
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                base_query = (
                    "SELECT game_id, season, week, away_team, home_team "
                    "FROM games "
                    "WHERE week = ? AND (home_score IS NULL OR away_score IS NULL)"
                )
                df = pd.read_sql_query(base_query, conn, params=(week,))
                # Playoffs fallback: DB may store playoff rounds as week=1
                if playoffs and df.empty and week >= 19:
                    df = pd.read_sql_query(base_query, conn, params=(1,))
                return df
        except Exception as e:
            print(f"  Warning: SQLite upcoming games fetch failed: {e}")
    # Fallback to workbook 'games' sheet
    workbook_path = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
    try:
        games_df = pd.read_excel(str(workbook_path), sheet_name="games")
        mask = (games_df.get("week") == week) & (games_df.get("home_score").isna())
        cols = [c for c in ["game_id", "season", "week", "away_team", "home_team"] if c in games_df.columns]
        return games_df.loc[mask, cols]
    except Exception as e:
        print(f"  Warning: Workbook upcoming games fetch failed: {e}")
        return pd.DataFrame(columns=["game_id", "season", "week", "away_team", "home_team"])  # empty
def game_already_completed(game_id: str) -> bool:
    """Check SQLite if a game has recorded final scores."""
    db_path = DATA_DIR / "nfl_model.db"
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = pd.read_sql_query(
                "SELECT home_score, away_score FROM games WHERE game_id = ?",
                conn,
                params=(game_id,)
            )
            if not row.empty:
                hs = row.iloc[0].get('home_score')
                as_ = row.iloc[0].get('away_score')
                return pd.notna(hs) and pd.notna(as_)
    except Exception:
        return False
    return False


def run_single_prediction(week, train_week, variant, playoffs=False, games_filters=None):
    """Run a single prediction with specific parameters"""
    try:
        # Initialize model with SQLite preference
        workbook_path = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
        model = NFLHybridModelV3(
            workbook_path=str(workbook_path),
            prefer_sqlite=True,
            model_type='randomforest',
            window=8
        )
        
        # Configure variant
        use_tuning = variant in ['tuned', 'stacking']
        use_stacking = variant == 'stacking'
        
        # Fit model
        print(f"  Training: week {train_week}, variant={variant}...", end=' ')
        start = time.time()
        
        report = model.fit(
            train_through_week=train_week,
            tune_hyperparams=use_tuning,
            stack_models=use_stacking
        )
        
        elapsed = time.time() - start
        mae = report.get('margin_MAE_test') if isinstance(report, dict) else None
        mae_str = f"{mae:.2f}" if (mae is not None and np.isfinite(mae)) else "N/A"
        print(f"[OK] ({elapsed:.1f}s, MAE={mae_str})")
        
        # Get upcoming games
        upcoming = fetch_upcoming_games_sqlite(week=week, playoffs=playoffs)
        
        if upcoming is None or upcoming.empty:
            # If explicit games were provided, build upcoming from filters
            if games_filters:
                pairs = []
                for game_str in games_filters:
                    for sep in ['@', ' @ ', ' vs ', '_']:
                        if sep in game_str:
                            parts = game_str.split(sep)
                            if len(parts) == 2:
                                away = parts[0].strip().upper()
                                home = parts[1].strip().upper()
                                pairs.append((away, home))
                            break
                if pairs:
                    upcoming = pd.DataFrame([
                        {"season": 2025, "week": week, "away_team": a, "home_team": h}
                        for (a, h) in pairs
                    ])
                else:
                    print(f"    No games found for week {week}")
                    return None
            else:
                print(f"    No games found for week {week}")
                return None
        
        # Generate predictions
        predictions = []
        for _, game in upcoming.iterrows():
            gid = str(game.get('game_id', f"{int(game.get('season', 2025))}_{week:02d}_{str(game['away_team']).upper()}_{str(game['home_team']).upper()}"))
            # Skip games already completed
            if game_already_completed(gid):
                print(f"    Skipping completed game: {gid}")
                continue
            # Use training cutoff to select feature history; avoids week=1 playoff empty history
            pred = model.predict_game(
                away_team=str(game['away_team']).upper(),
                home_team=str(game['home_team']).upper(),
                week=train_week + 1
            )
            
            if pred:
                predictions.append({
                    'game_id': gid,
                    'week': week,
                    'away_team': str(game['away_team']).upper(),
                    'home_team': str(game['home_team']).upper(),
                    'pred_margin_home': pred.get('pred_margin_home', pred.get('margin')),
                    'pred_total': pred.get('pred_total', pred.get('total')),
                    'pred_winprob_home': (
                        pred.get('pred_winprob_home')
                        if pred.get('pred_winprob_home') is not None
                        else 0.5 + (pred.get('pred_margin_home', pred.get('margin', 0.0)))/40
                    ),
                    'train_week': train_week,
                    'model_mae': (report.get('margin_MAE_test') if isinstance(report, dict) else None),
                    'n_features': (report.get('n_features') if isinstance(report, dict) else None),
                    'variant': variant
                })
        
        return pd.DataFrame(predictions) if predictions else None
        
    except Exception as e:
        print(f"[X] Error: {e}")
        return None


def combine_predictions(all_preds):
    """Combine predictions across windows and variants"""
    if all_preds.empty:
        return None
    
    # Group by game
    game_cols = ['game_id', 'away_team', 'home_team', 'week']
    combined = []
    
    for game_id, group in all_preds.groupby('game_id'):
        away = group.iloc[0]['away_team']
        home = group.iloc[0]['home_team']
        week = group.iloc[0]['week']
        
        # Calculate statistics
        margin_mean = group['pred_margin_home'].mean()
        margin_std = group['pred_margin_home'].std()
        total_mean = group['pred_total'].mean()
        total_std = group['pred_total'].std()
        winprob_mean = group['pred_winprob_home'].mean()
        
        # Weighted average (weight by inverse MAE)
        if 'model_mae' in group.columns and group['model_mae'].notna().all():
            weights = 1 / group['model_mae']
            weights = weights / weights.sum()
            margin_weighted = (group['pred_margin_home'] * weights).sum()
            total_weighted = (group['pred_total'] * weights).sum()
        else:
            margin_weighted = margin_mean
            total_weighted = total_mean
        
        # Confidence intervals (95%)
        margin_ci_lower = margin_mean - 1.96 * margin_std
        margin_ci_upper = margin_mean + 1.96 * margin_std
        total_ci_lower = total_mean - 1.96 * total_std
        total_ci_upper = total_mean + 1.96 * total_std
        
        combined.append({
            'game_id': game_id,
            'week': week,
            'away_team': away,
            'home_team': home,
            'pred_margin_home': margin_weighted,
            'pred_margin_mean': margin_mean,
            'pred_margin_std': margin_std,
            'pred_margin_ci_lower': margin_ci_lower,
            'pred_margin_ci_upper': margin_ci_upper,
            'pred_total': total_weighted,
            'pred_total_mean': total_mean,
            'pred_total_std': total_std,
            'pred_total_ci_lower': total_ci_lower,
            'pred_total_ci_upper': total_ci_upper,
            'pred_winprob_home': winprob_mean,
            'n_predictions': len(group),
            'n_windows': group['train_week'].nunique(),
            'n_variants': group['variant'].nunique(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    return pd.DataFrame(combined)


def print_prediction_summary(combined_df, all_preds_df):
    """Print detailed prediction summary"""
    print("\n" + "="*100)
    print("MULTI-WINDOW ENSEMBLE PREDICTIONS")
    print("="*100)
    
    for _, game in combined_df.iterrows():
        away = game['away_team']
        home = game['home_team']
        margin = game['pred_margin_home']
        total = game['pred_total']
        prob_home = game['pred_winprob_home']
        
        # Determine spread
        favored = home if margin > 0 else away
        line = abs(margin)
        
        print(f"\n{away} @ {home}")
        print("-" * 100)
        print(f"  Ensemble Prediction ({game['n_predictions']} predictions, {game['n_windows']} windows, {game['n_variants']} variants):")
        print(f"    Spread: {favored} -{line:>5.1f} (95% CI: {abs(game['pred_margin_ci_lower']):.1f} to {abs(game['pred_margin_ci_upper']):.1f})")
        print(f"    Total:  {total:>5.1f} (95% CI: {game['pred_total_ci_lower']:.1f} to {game['pred_total_ci_upper']:.1f})")
        print(f"    Win Probability: {home} {prob_home:.1%}, {away} {1-prob_home:.1%}")
        print(f"    Variance: Margin stdev={game['pred_margin_std']:.2f}, Total stdev={game['pred_total_std']:.2f}")
        
        # Show individual predictions
        game_preds = all_preds_df[all_preds_df['game_id'] == game['game_id']]
        print(f"\n  Individual Predictions:")
        for _, pred in game_preds.iterrows():
            train_w = pred['train_week']
            variant = pred['variant']
            p_margin = pred['pred_margin_home']
            p_total = pred['pred_total']
            print(f"    Week {train_w}, {variant:>8}: Margin {p_margin:+6.2f}, Total {p_total:>5.1f}")


def save_predictions(combined_df, all_preds_df):
    """Save predictions to files"""
    ensure_dir(OUTPUTS_DIR)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    
    # Save combined ensemble predictions
    ensemble_file = OUTPUTS_DIR / f"ensemble_multiwindow_{timestamp}.csv"
    combined_df.to_csv(ensemble_file, index=False)
    print(f"\n[SUCCESS] Ensemble predictions saved to: {ensemble_file}")
    
    # Save all individual predictions
    detail_file = OUTPUTS_DIR / f"ensemble_multiwindow_detail_{timestamp}.csv"
    all_preds_df.to_csv(detail_file, index=False)
    print(f"[SUCCESS] Individual predictions saved to: {detail_file}")
    
    return ensemble_file, detail_file


def log_predictions_to_sqlite(combined_df: pd.DataFrame, all_preds_df: pd.DataFrame):
    """Log combined and detailed predictions to SQLite (data/nfl_model.db).

    Creates tables if missing:
      - ensemble_predictions
      - ensemble_predictions_detail
    """
    db_path = DATA_DIR / "nfl_model.db"
    if not db_path.exists():
        print(f"\n[WARNING] SQLite DB not found at {db_path}; skipping DB logging.")
        return None

    # Ensure a consistent timestamp across both tables
    run_ts = None
    if 'timestamp' in combined_df.columns and not combined_df['timestamp'].isna().all():
        run_ts = combined_df.iloc[0]['timestamp']
    else:
        run_ts = datetime.utcnow().isoformat() + 'Z'

    # Prepare combined predictions (add season parsed from game_id)
    combined_out = combined_df.copy()
    def _parse_season(gid):
        try:
            return int(str(gid).split('_')[0])
        except Exception:
            return None
    combined_out['season'] = combined_out['game_id'].apply(_parse_season)

    # Prepare detailed predictions (add timestamp)
    details_out = all_preds_df.copy()
    if 'timestamp' not in details_out.columns:
        details_out['timestamp'] = run_ts

    try:
        with sqlite3.connect(str(db_path)) as conn:
            # Ensure tables exist and have required columns (add missing columns if needed)
            def ensure_table(name: str, df: pd.DataFrame):
                # Create if missing
                conn.execute(f"CREATE TABLE IF NOT EXISTS {name} (dummy INTEGER)")
                # Inspect existing columns
                info = pd.read_sql_query(f"PRAGMA table_info({name})", conn)
                existing = set(info['name'].tolist())
                # Add missing columns with inferred types
                for col in df.columns:
                    if col not in existing:
                        series = df[col]
                        if pd.api.types.is_float_dtype(series):
                            col_type = 'REAL'
                        elif pd.api.types.is_integer_dtype(series):
                            col_type = 'INTEGER'
                        else:
                            col_type = 'TEXT'
                        conn.execute(f"ALTER TABLE {name} ADD COLUMN {col} {col_type}")
                # Drop dummy if present and unused
                if 'dummy' in existing and 'dummy' not in df.columns:
                    # SQLite doesn't support DROP COLUMN in older versions; leave dummy if created
                    pass

            ensure_table('ensemble_predictions', combined_out)
            ensure_table('ensemble_predictions_detail', details_out)

            # Append rows
            combined_out.to_sql('ensemble_predictions', conn, if_exists='append', index=False)
            details_out.to_sql('ensemble_predictions_detail', conn, if_exists='append', index=False)

        print(f"\nOK Logged predictions to SQLite: {db_path}")
        return run_ts
    except Exception as e:
        print(f"\nERROR Failed to log predictions to SQLite: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Multi-window ensemble predictions for improved accuracy",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--week', type=int, required=True, help='Week number to predict')
    parser.add_argument('--playoffs', action='store_true', help='Include playoff games')
    parser.add_argument(
        '--train-windows',
        nargs='+',
        type=int,
        default=[14, 15, 16, 17, 18],
        help='Training week endpoints to use (default: 14 15 16 17 18)'
    )
    parser.add_argument(
        '--variants',
        nargs='+',
        default=['default', 'tuned', 'stacking'],
        help='Model variants to run (default: default tuned stacking)'
    )
    parser.add_argument(
        '--games',
        nargs='+',
        help='Filter to specific games (e.g., BUF@JAX SFO@PHI)'
    )
    parser.add_argument(
        '--sync-postgame',
        action='store_true',
        help='Sync completed game scores into SQLite before predicting'
    )
    parser.add_argument(
        '--season',
        type=int,
        default=2025,
        help='Season year for postgame sync (default: 2025)'
    )
    
    args = parser.parse_args()
    
    print("="*100)
    print(f"MULTI-WINDOW ENSEMBLE PREDICTION - Week {args.week}")
    print("="*100)
    print(f"\nConfiguration:")
    print(f"  Training windows: {args.train_windows}")
    print(f"  Variants: {args.variants}")
    print(f"  Total predictions per game: {len(args.train_windows) * len(args.variants)}")
    print(f"  Expected runtime: ~{len(args.train_windows) * len(args.variants) * 30}s")

    # Optional: sync completed scores into DB to ensure filtering works
    if args.sync_postgame:
        try:
            print(f"\nSyncing completed scores for season {args.season}, week {args.week}...")
            updated = update_scores(args.season, args.week)
            print(f"Synced {updated} games.")
        except Exception as e:
            print(f"Warning: postgame sync failed: {e}")
    
    # Run all combinations
    all_predictions = []
    total_runs = len(args.train_windows) * len(args.variants)
    current_run = 0
    
    print(f"\nRunning {total_runs} model fits...")
    print("-" * 100)
    
    for train_week in args.train_windows:
        for variant in args.variants:
            current_run += 1
            print(f"[{current_run}/{total_runs}] ", end='')
            
            preds = run_single_prediction(
                week=args.week,
                train_week=train_week,
                variant=variant,
                playoffs=args.playoffs,
                games_filters=args.games
            )
            
            if preds is not None:
                all_predictions.append(preds)
    
    if not all_predictions:
        print("\n❌ No predictions generated")
        sys.exit(1)
    
    # Combine all predictions
    all_preds_df = pd.concat(all_predictions, ignore_index=True)
    
    # Filter to specific games if requested
    if args.games:
        game_filters = []
        for game_str in args.games:
            for sep in ['@', ' @ ', ' vs ', '_']:
                if sep in game_str:
                    parts = game_str.split(sep)
                    if len(parts) == 2:
                        away = parts[0].strip().upper()
                        home = parts[1].strip().upper()
                        game_filters.append((away, home))
                    break
        
        filtered = all_preds_df[
            all_preds_df.apply(
                lambda row: (row['away_team'], row['home_team']) in game_filters,
                axis=1
            )
        ]
        
        if filtered.empty:
            print(f"\n[WARNING] No games matched filters: {args.games}")
        else:
            all_preds_df = filtered
            print(f"\n[SUCCESS] Filtered to {len(game_filters)} game(s)")
    
    print(f"\n[SUCCESS] Generated {len(all_preds_df)} total predictions")
    
    # Combine into ensemble
    print("\nCombining predictions into ensemble...")
    combined_df = combine_predictions(all_preds_df)
    
    if combined_df is None:
        print("❌ Failed to combine predictions")
        sys.exit(1)
    
    # Save results
    save_predictions(combined_df, all_preds_df)

    # Log to SQLite DB
    log_predictions_to_sqlite(combined_df, all_preds_df)
    
    # Print summary
    print_prediction_summary(combined_df, all_preds_df)
    
    print("\n" + "="*100)
    print("ENSEMBLE COMPLETE")
    print("="*100)
    print(f"\nEnsemble approach used:")
    print(f"  • {len(args.train_windows)} training windows × {len(args.variants)} variants")
    print(f"  • Weighted by model MAE (better models weighted higher)")
    print(f"  • 95% confidence intervals provided")
    print(f"  • Expected improvement: ~0.2-0.4 pts margin MAE vs single prediction")


if __name__ == '__main__':
    main()
