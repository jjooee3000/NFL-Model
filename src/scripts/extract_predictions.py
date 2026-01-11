#!/usr/bin/env python3
"""
Extract and reformat predictions from previously generated prediction runs.

This is a POST-PROCESSING tool - it works with predictions already generated.
For generating NEW predictions, use: src/scripts/predict_upcoming.py

Usage:
    # Extract predictions from a prior run
    python src/scripts/extract_predictions.py --input outputs/predictions_playoffs_week1_2026-01-10.csv
    
    # Extract specific games only
    python src/scripts/extract_predictions.py --input outputs/predictions_upcoming.json --games BUF@JAX SFO@PHI
    
    # Reformat and combine variant predictions
    python src/scripts/extract_predictions.py --input outputs/prediction_log.csv --combine-variants

Examples:
    - Extract Week 1 playoff games from a prior run
    - Reformat predictions from JSON to CSV format
    - Average predictions across multiple model variants
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import json
import argparse

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import OUTPUTS_DIR, ensure_dir


def load_predictions(input_file):
    """Load predictions from CSV or JSON file"""
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"❌ Error: {input_path} not found")
        return None
    
    try:
        if input_path.suffix.lower() == '.json':
            with open(input_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return pd.DataFrame(data)
                return pd.DataFrame([data])
        else:  # Assume CSV
            return pd.read_csv(input_path)
    except Exception as e:
        print(f"❌ Error loading {input_file}: {e}")
        return None


def filter_games(pred_df, games):
    """Filter predictions to specific games"""
    if not games or games is None:
        return pred_df
    
    # Normalize game strings (handle BUF@JAX, BUF vs JAX, BUF_JAX, etc.)
    normalized_games = set()
    for game in games:
        # Extract team codes
        for sep in ['@', ' @ ', ' vs ', '_', '-']:
            if sep in game:
                parts = game.split(sep)
                if len(parts) == 2:
                    team1 = parts[0].strip().upper()
                    team2 = parts[1].strip().upper()
                    normalized_games.add((team1, team2))
                break
    
    # Filter dataframe
    filtered = []
    for _, row in pred_df.iterrows():
        away = str(row.get('away_team', '')).upper()
        home = str(row.get('home_team', '')).upper()
        
        if (away, home) in normalized_games:
            filtered.append(row)
    
    if not filtered:
        print(f"⚠️  Warning: No games matched filters: {games}")
        return pd.DataFrame()
    
    return pd.DataFrame(filtered)


def combine_variants(pred_df):
    """Combine/average predictions across model variants"""
    if pred_df.empty:
        return pred_df
    
    # Group by game
    combined = []
    
    game_cols = ['away_team', 'home_team', 'game_id', 'week']
    if not all(col in pred_df.columns for col in game_cols if col in pred_df.columns):
        # Fallback grouping
        game_cols = ['away_team', 'home_team']
    
    grouped = pred_df.groupby(game_cols, as_index=False)
    
    for group_key, group_df in grouped:
        # Average numeric predictions
        avg_row = {}
        
        # Copy non-numeric columns from first row
        first = group_df.iloc[0]
        for col in group_df.columns:
            if col in ['away_team', 'home_team', 'game_id', 'week', 'train_week']:
                avg_row[col] = first[col]
            elif col in pred_df.select_dtypes(include=[np.number]).columns:
                avg_row[col] = group_df[col].mean()
            else:
                avg_row[col] = first[col] if pd.notna(first[col]) else ''
        
        avg_row['variant'] = 'combined_average'
        avg_row['n_variants'] = len(group_df)
        combined.append(avg_row)
    
    return pd.DataFrame(combined)


def save_predictions(pred_df, output_file=None):
    """Save predictions to file"""
    ensure_dir(OUTPUTS_DIR)
    
    if output_file is None:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = OUTPUTS_DIR / f"extracted_predictions_{timestamp}.csv"
    else:
        output_file = Path(output_file)
    
    pred_df.to_csv(output_file, index=False)
    print(f"✅ Saved {len(pred_df)} predictions to {output_file}")
    
    return output_file


def print_summary(pred_df, combine=False):
    """Print prediction summary in readable format"""
    if pred_df.empty:
        print("No predictions to display")
        return
    
    print("\n" + "="*90)
    title = "EXTRACTED PREDICTIONS - COMBINED VARIANTS" if combine else "EXTRACTED PREDICTIONS"
    print(title)
    print("="*90)
    
    # Determine grouping columns
    game_cols = ['away_team', 'home_team']
    if 'game_id' in pred_df.columns:
        game_cols = ['game_id', 'away_team', 'home_team']
    
    unique_games = pred_df.drop_duplicates(subset=game_cols)
    
    for _, game_row in unique_games.iterrows():
        away = game_row['away_team']
        home = game_row['home_team']
        
        # Get all predictions for this game
        if 'game_id' in pred_df.columns:
            game_preds = pred_df[pred_df['game_id'] == game_row['game_id']]
        else:
            game_preds = pred_df[(pred_df['away_team'] == away) & (pred_df['home_team'] == home)]
        
        print(f"\n{away} @ {home}")
        print("-" * 90)
        
        for idx, row in game_preds.iterrows():
            variant = row.get('variant', 'default')
            
            # Extract key predictions
            margin = row.get('pred_margin_home', row.get('margin_home', np.nan))
            total = row.get('pred_total', row.get('total', np.nan))
            prob_home = row.get('pred_winprob_home', row.get('winprob_home', np.nan))
            
            if pd.notna(margin) and pd.notna(total):
                # Determine spread
                favored = home if margin > 0 else away
                line = abs(margin)
                
                extra_info = []
                if 'n_variants' in row and pd.notna(row['n_variants']):
                    extra_info.append(f"avg of {int(row['n_variants'])} variants")
                if 'stacking' in row and row['stacking']:
                    extra_info.append("stacking")
                
                extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
                
                print(f"  {variant}{extra_str}:")
                print(f"    Spread: {favored} -{line:>5.1f}  |  Total: {total:>5.1f}  |  {home} Win: {prob_home:>5.1%}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and reformat predictions from prior runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from prior run (default output filename)
  python src/scripts/extract_predictions.py --input outputs/predictions_playoffs_week1_2026-01-10.csv
  
  # Extract specific games only
  python src/scripts/extract_predictions.py --input outputs/prediction_log.csv --games BUF@JAX SFO@PHI
  
  # Combine variants into single prediction per game
  python src/scripts/extract_predictions.py --input outputs/prediction_log.csv --combine-variants
  
  # Specify custom output file
  python src/scripts/extract_predictions.py --input outputs/predictions.csv --output outputs/selected_games.csv --games BUF@JAX
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Input CSV or JSON file with predictions'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output CSV file (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '--games',
        nargs='+',
        default=None,
        help='Filter to specific games (e.g., BUF@JAX SFO@PHI LAC@NWE)'
    )
    parser.add_argument(
        '--combine-variants',
        action='store_true',
        help='Average predictions across variants for same game'
    )
    
    args = parser.parse_args()
    
    # Load predictions
    print(f"Loading predictions from {args.input}...")
    pred_df = load_predictions(args.input)
    
    if pred_df is None or pred_df.empty:
        print("❌ No predictions loaded")
        sys.exit(1)
    
    print(f"✅ Loaded {len(pred_df)} predictions")
    
    # Filter games if requested
    if args.games:
        print(f"Filtering to games: {' '.join(args.games)}")
        pred_df = filter_games(pred_df, args.games)
        
        if pred_df.empty:
            print("❌ No games matched filters")
            sys.exit(1)
        
        print(f"✅ Filtered to {len(pred_df)} predictions")
    
    # Combine variants if requested
    if args.combine_variants:
        print("Combining predictions across variants...")
        pred_df = combine_variants(pred_df)
        print(f"✅ Combined to {len(pred_df)} predictions")
    
    # Save
    output_file = save_predictions(pred_df, args.output)
    
    # Display summary
    print_summary(pred_df, combine=args.combine_variants)
    
    print("\n" + "="*90)
    print(f"Done. Predictions saved to: {output_file}")
    print("="*90)


if __name__ == '__main__':
    main()
