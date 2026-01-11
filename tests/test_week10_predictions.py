"""Quick test to compare Week 10 predictions with actual results."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import sqlite3
import pandas as pd
from models.model_v3 import NFLHybridModelV3

# Connect to database
db_path = Path("data/nfl_model.db")
conn = sqlite3.connect(str(db_path))

# Get week 10 games
query = """
SELECT DISTINCT game_id, season, week, away_team, home_team, away_score, home_score
FROM games
WHERE season = 2024 AND week = 10
ORDER BY game_id
LIMIT 6
"""
week10_games = pd.read_sql(query, conn)
print(f"\nTesting on {len(week10_games)} Week 10 games:")
print(week10_games[['game_id', 'away_team', 'home_team', 'away_score', 'home_score']])

# Train model through week 9
print("\n\nTraining model through week 9...")
model = NFLHybridModelV3(workbook_path="data/nfl_2025_model_data_with_moneylines.xlsx")
report = model.fit(train_through_week=9)

print(f"\nModel trained with {report.get('n_features', 'N/A')} features")
mae = report.get('model_mae', 'N/A')
if isinstance(mae, (int, float)):
    print(f"Train MAE: {mae:.2f}")
else:
    print(f"Train MAE: {mae}")

# Predict each game
print("\n\n" + "="*80)
print("PREDICTIONS VS ACTUAL RESULTS (Week 10)")
print("="*80)

results = []
for _, game in week10_games.iterrows():
    try:
        pred = model.predict_game(
            away_team=game['away_team'],
            home_team=game['home_team'],
            week=int(game['week'])
        )
        
        # Calculate actual margin (home - away)
        actual_margin = game['home_score'] - game['away_score']
        pred_margin = pred['pred_margin_home']
        error = abs(pred_margin - actual_margin)
        
        # Determine winner
        actual_winner = game['home_team'] if actual_margin > 0 else game['away_team']
        pred_winner = game['home_team'] if pred_margin > 0 else game['away_team']
        correct = "✓" if actual_winner == pred_winner else "✗"
        
        print(f"\n{game['away_team']} @ {game['home_team']}")
        print(f"  Predicted: {game['home_team']} {pred_margin:+.1f} pts (Total: {pred['pred_total']:.1f})")
        print(f"  Actual:    {game['home_team']} {actual_margin:+.1f} pts (Total: {game['home_score'] + game['away_score']:.1f})")
        print(f"  Error: {error:.1f} pts  Winner: {correct}")
        
        results.append({
            'game_id': game['game_id'],
            'away_team': game['away_team'],
            'home_team': game['home_team'],
            'pred_margin': pred_margin,
            'actual_margin': actual_margin,
            'error': error,
            'pred_total': pred['pred_total'],
            'actual_total': game['home_score'] + game['away_score'],
            'winner_correct': actual_winner == pred_winner
        })
        
    except Exception as e:
        print(f"\n{game['away_team']} @ {game['home_team']}")
        print(f"  Error: {e}")

conn.close()

# Summary statistics
if results:
    df_results = pd.DataFrame(results)
    print("\n\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Games predicted: {len(df_results)}")
    print(f"Mean Absolute Error (Margin): {df_results['error'].mean():.2f} pts")
    print(f"Winner Accuracy: {df_results['winner_correct'].sum()}/{len(df_results)} ({100*df_results['winner_correct'].mean():.1f}%)")
    print(f"Total MAE: {(df_results['pred_total'] - df_results['actual_total']).abs().mean():.2f} pts")
