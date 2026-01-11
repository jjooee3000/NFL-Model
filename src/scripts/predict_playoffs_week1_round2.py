#!/usr/bin/env python3
"""
Generate predictions for Week 1 Playoff games on 2026-01-12 and 2026-01-13
Games:
  - BUF @ JAX (Sunday 1/12 1:00 PM)
  - SFO @ PHI (Sunday 1/12 4:30 PM)
  - LAC @ NWE (Sunday 1/12 8:15 PM)
  - HOU @ PIT (Monday 1/13 8:15 PM)
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.model_v3 import ModelV3Runner
from utils.pfr_scraper import PFRScraper

OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)

# Games to predict
GAMES = [
    {"away_team": "BUF", "home_team": "JAX", "date": "2026-01-12", "time": "1:00 PM"},
    {"away_team": "SFO", "home_team": "PHI", "date": "2026-01-12", "time": "4:30 PM"},
    {"away_team": "LAC", "home_team": "NWE", "date": "2026-01-12", "time": "8:15 PM"},
    {"away_team": "HOU", "home_team": "PIT", "date": "2026-01-13", "time": "8:15 PM"},
]

def get_team_data(scraper, team_code):
    """Get season stats for a team"""
    try:
        # Get 2025 season stats
        stats = scraper.get_team_stats(2025, team_code)
        return stats
    except Exception as e:
        print(f"Warning: Could not fetch stats for {team_code}: {e}")
        return None

def run_predictions():
    """Generate predictions for all games"""
    print("="*70)
    print("PLAYOFF WEEK 1 PREDICTIONS (2026-01-12 and 2026-01-13)")
    print("="*70)
    
    scraper = PFRScraper()
    model = ModelV3Runner()
    
    predictions = []
    
    for i, game in enumerate(GAMES, 1):
        away = game["away_team"]
        home = game["home_team"]
        date = game["date"]
        time = game["time"]
        
        print(f"\n[Game {i}] {away} @ {home} ({date} {time})")
        print("-" * 70)
        
        try:
            # Get team data
            away_stats = get_team_data(scraper, away)
            home_stats = get_team_data(scraper, home)
            
            if away_stats is None or home_stats is None:
                print(f"⚠️  Skipping {away}@{home}: insufficient data")
                continue
            
            # Generate prediction using v3 model
            prediction = model.predict_game(
                away_team=away,
                home_team=home,
                away_stats=away_stats,
                home_stats=home_stats
            )
            
            if prediction is None:
                print(f"⚠️  Model could not generate prediction for {away}@{home}")
                continue
            
            # Format prediction
            pred_margin_home = prediction.get('pred_margin_home', np.nan)
            pred_total = prediction.get('pred_total', np.nan)
            pred_winprob_home = prediction.get('pred_winprob_home', np.nan)
            pred_winprob_away = prediction.get('pred_winprob_away', np.nan)
            
            # Display results
            print(f"  Model: v3 (using previous week 18 training data)")
            print(f"  Predicted margin (home): {pred_margin_home:+.2f} pts")
            print(f"  Predicted total: {pred_total:.1f} pts")
            print(f"  Win probability - {away}: {pred_winprob_away:.1%}")
            print(f"  Win probability - {home}: {pred_winprob_home:.1%}")
            
            # Add to predictions list
            predictions.append({
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'game_id': f"2025_01_{away}_{home}",
                'week': 1,
                'away_team': away,
                'home_team': home,
                'date': date,
                'time': time,
                'pred_margin_home': pred_margin_home,
                'pred_total': pred_total,
                'pred_winprob_home': pred_winprob_home,
                'pred_winprob_away': pred_winprob_away,
                'model_version': 'v3',
                'variant': 'playoff_default',
                'notes': 'Week 1 Playoff predictions using v3 model trained on week 18 data. Total underestimation noted in Week 1 evaluation (+12.5 MAE) - monitor actual results.'
            })
            
        except Exception as e:
            print(f"❌ Error predicting {away}@{home}: {e}")
            import traceback
            traceback.print_exc()
    
    if not predictions:
        print("\n⚠️  No predictions generated")
        return None
    
    # Save predictions
    pred_df = pd.DataFrame(predictions)
    output_file = OUT_DIR / "predictions_playoffs_week1_2026-01-12_13.csv"
    pred_df.to_csv(output_file, index=False)
    print(f"\n\n✅ Saved {len(pred_df)} predictions to {output_file}")
    
    return pred_df

def print_summary(pred_df):
    """Print prediction summary"""
    if pred_df is None or pred_df.empty:
        return
    
    print("\n" + "="*70)
    print("PREDICTION SUMMARY")
    print("="*70)
    print(f"\nTotal predictions: {len(pred_df)}")
    print("\nPredictions by game:")
    print("-" * 70)
    
    for _, row in pred_df.iterrows():
        away = row['away_team']
        home = row['home_team']
        margin = row['pred_margin_home']
        total = row['pred_total']
        prob_home = row['pred_winprob_home']
        
        # Determine favored team
        favored = home if margin > 0 else away
        favored_by = abs(margin)
        
        print(f"\n{away} @ {home}")
        print(f"  Spread: {favored} -{favored_by:.1f} (margin: {margin:+.1f})")
        print(f"  Total: {total:.1f} pts")
        print(f"  Win prob: {home} {prob_home:.1%}, {away} {1-prob_home:.1%}")

if __name__ == '__main__':
    pred_df = run_predictions()
    if pred_df is not None:
        print_summary(pred_df)
