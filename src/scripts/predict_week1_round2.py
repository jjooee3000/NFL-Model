#!/usr/bin/env python3
"""
Generate predictions for remaining Week 1 playoff games (2026-01-12 and 2026-01-13).

Games:
  - BUF @ JAX (Sunday 1/12 1:00 PM)
  - SFO @ PHI (Sunday 1/12 4:30 PM) 
  - LAC @ NWE (Sunday 1/12 8:15 PM)
  - HOU @ PIT (Monday 1/13 8:15 PM)

This uses the v3 model predictions already generated on 2026-01-10,
since those games haven't been completed yet.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime

# The games we want to predict
GAMES_TO_PREDICT = {
    "BUF @ JAX": {"away_team": "BUF", "home_team": "JAX", "game_id": "2025_01_BUF_JAX"},
    "SFO @ PHI": {"away_team": "SFO", "home_team": "PHI", "game_id": "2025_01_SFO_PHI"},
    "LAC @ NWE": {"away_team": "LAC", "home_team": "NWE", "game_id": "2025_01_LAC_NWE"},
    "HOU @ PIT": {"away_team": "HOU", "home_team": "PIT", "game_id": "2025_01_HOU_PIT"},
}

def load_prior_predictions():
    """Load predictions from 2026-01-10 run"""
    pred_file = Path("outputs/predictions_playoffs_week1_2026-01-10.csv")
    
    if not pred_file.exists():
        print(f"Error: {pred_file} not found")
        return None
    
    return pd.read_csv(pred_file)

def extract_and_reformat_predictions():
    """Extract relevant game predictions from prior run"""
    
    prior_preds = load_prior_predictions()
    if prior_preds is None:
        return None
    
    # Extract relevant games
    games_list = []
    for game_name, game_info in GAMES_TO_PREDICT.items():
        game_id = game_info["game_id"]
        
        # Find matching rows
        matches = prior_preds[prior_preds["game_id"] == game_id]
        
        if matches.empty:
            print(f"Warning: No predictions found for {game_name}")
            continue
        
        for _, row in matches.iterrows():
            games_list.append({
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'game_id': game_id,
                'week': 1,
                'away_team': game_info['away_team'],
                'home_team': game_info['home_team'],
                'pred_margin_home': row['pred_margin_home'],
                'pred_spread_away': row['pred_spread_away'],
                'pred_total': row['pred_total'],
                'pred_winprob_home': row['pred_winprob_home'],
                'pred_winprob_away': row['pred_winprob_away'],
                'train_week': row['train_week'],
                'window': row['window'],
                'variant': row['variant'],
                'model_version': row['model_version'],
                'stacking': row['stacking'],
                'tuned_params': row['tuned_params'],
                'notes': 'Week 1 Playoff predictions from 2026-01-10 run. Monitor against postgame actuals.'
            })
    
    return pd.DataFrame(games_list) if games_list else None

def save_predictions(pred_df):
    """Save predictions to file"""
    
    output_file = Path("outputs/predictions_playoffs_week1_2026-01-12_13.csv")
    pred_df.to_csv(output_file, index=False)
    
    print(f"\n✅ Saved {len(pred_df)} predictions to {output_file}")
    return output_file

def print_summary(pred_df):
    """Print prediction summary in readable format"""
    
    print("\n" + "="*80)
    print("WEEK 1 PLAYOFF PREDICTIONS - REMAINING GAMES (2026-01-12 and 2026-01-13)")
    print("="*80)
    
    # Group by game
    for game_id in pred_df['game_id'].unique():
        game_preds = pred_df[pred_df['game_id'] == game_id]
        away = game_preds.iloc[0]['away_team']
        home = game_preds.iloc[0]['home_team']
        
        print(f"\n{away} @ {home}")
        print("-" * 80)
        
        for _, row in game_preds.iterrows():
            margin = row['pred_margin_home']
            total = row['pred_total']
            variant = row['variant']
            stacking = row['stacking']
            
            # Determine spread format
            spread_away = row['pred_spread_away']
            spread_line = f"{home} {-spread_away:+.1f}" if spread_away else "N/A"
            
            variant_label = f"({variant}"
            if stacking:
                variant_label += ", stacking"
            variant_label += ")"
            
            print(f"  {variant_label}")
            print(f"    Margin (home): {margin:+.2f} pts")
            print(f"    Spread: {spread_line}")
            print(f"    Total: {total:.1f} pts")
            print(f"    Win prob: {home} {row['pred_winprob_home']:.1%}, {away} {row['pred_winprob_away']:.1%}")

def print_combined_summary(pred_df):
    """Print combined/average predictions per game"""
    
    print("\n" + "="*80)
    print("SUMMARY - COMBINED PREDICTIONS (Averaged Across Variants)")
    print("="*80)
    print("\nNote: Models show consistent underestimation of total points in Week 1 (+12.5 MAE)")
    print("      Consider adding ~10-15 pt buffer to total predictions\n")
    
    for game_id in pred_df['game_id'].unique():
        game_preds = pred_df[pred_df['game_id'] == game_id]
        away = game_preds.iloc[0]['away_team']
        home = game_preds.iloc[0]['home_team']
        
        # Average predictions
        avg_margin = game_preds['pred_margin_home'].mean()
        avg_total = game_preds['pred_total'].mean()
        avg_prob_home = game_preds['pred_winprob_home'].mean()
        
        # Determine line
        favored = home if avg_margin > 0 else away
        line = abs(avg_margin)
        
        print(f"{away:>4} @ {home:<4} | Spread: {favored:>4} -{line:>5.1f} | Total: {avg_total:>5.1f} | {home} Win: {avg_prob_home:>5.1%}")

if __name__ == '__main__':
    print("Loading prior predictions from 2026-01-10 run...")
    pred_df = extract_and_reformat_predictions()
    
    if pred_df is None or pred_df.empty:
        print("❌ No predictions could be extracted")
        sys.exit(1)
    
    print(f"✅ Extracted {len(pred_df)} predictions")
    
    output_file = save_predictions(pred_df)
    print_summary(pred_df)
    print_combined_summary(pred_df)
    
    print("\n" + "="*80)
    print(f"Predictions saved to: {output_file}")
    print("="*80)
