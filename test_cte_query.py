"""Test the CTE query directly"""
import sqlite3
from datetime import datetime
import traceback

try:
    conn = sqlite3.connect('data/nfl_model.db')
    conn.row_factory = sqlite3.Row
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"Today: {today}\n")
    
    query = """
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
    """
    
    print("Executing query...")
    rows = conn.execute(query, (today,)).fetchall()
    print(f"\nSuccess! Found {len(rows)} rows\n")
    
    for i, r in enumerate(rows, 1):
        print(f"{i}. {r['game_id']}: {r['away_team']}@{r['home_team']}")
        print(f"   Date: {r['game_date_yyyy-mm-dd']}, Pred: {r['pred_margin_home']:.1f}")
    
    conn.close()
    print("\nQuery executed successfully!")
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
