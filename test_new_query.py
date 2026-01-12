"""Test the new query for recent predictions"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/nfl_model.db')
conn.row_factory = sqlite3.Row

today = datetime.utcnow().strftime("%Y-%m-%d")
print(f"Today's date: {today}")
print("="*80)

# Test the new query
recent_rows = conn.execute("""
    WITH LatestPredictions AS (
        SELECT 
            ep.game_id, 
            ep.away_team, 
            ep.home_team, 
            ep.pred_margin_home, 
            ep.pred_total,
            ep.timestamp,
            ROW_NUMBER() OVER (PARTITION BY ep.game_id ORDER BY ep.timestamp DESC) as rn
        FROM ensemble_predictions ep
    )
    SELECT 
        lp.game_id, lp.away_team, lp.home_team, lp.pred_margin_home, lp.pred_total, 
        lp.timestamp, g.away_score, g.home_score, g."game_date_yyyy-mm-dd"
    FROM LatestPredictions lp
    JOIN games g ON lp.game_id = g.game_id
    WHERE lp.rn = 1
        AND g.away_score IS NOT NULL 
        AND g.home_score IS NOT NULL
        AND g."game_date_yyyy-mm-dd" < ?
    ORDER BY g."game_date_yyyy-mm-dd" DESC
    LIMIT 10
""", (today,)).fetchall()

print(f"Found {len(recent_rows)} completed games with predictions")
print("="*80)

for i, r in enumerate(recent_rows, 1):
    actual_margin = r['home_score'] - r['away_score']
    pred_margin = r['pred_margin_home']
    error = abs(actual_margin - pred_margin)
    correct = (actual_margin > 0 and pred_margin > 0) or (actual_margin < 0 and pred_margin < 0)
    
    print(f"{i}. {r['game_date_yyyy-mm-dd']} - {r['game_id']}")
    print(f"   {r['away_team']}@{r['home_team']}: Pred margin: {pred_margin:.1f}, Actual: {r['away_score']}-{r['home_score']} (margin: {actual_margin:.1f})")
    print(f"   Error: {error:.1f} pts, {'✓ CORRECT' if correct else '✗ WRONG'}")
    print(f"   Prediction timestamp: {r['timestamp']}")
    print()

conn.close()
