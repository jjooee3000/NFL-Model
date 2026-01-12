"""Check LAC@NE games and predictions"""
import sqlite3

conn = sqlite3.connect('data/nfl_model.db')
conn.row_factory = sqlite3.Row

print("="*60)
print("LAC@NE GAMES IN DATABASE")
print("="*60)
rows = conn.execute("""
    SELECT game_id, away_team, home_team, away_score, home_score, "game_date_yyyy-mm-dd"
    FROM games
    WHERE (game_id LIKE '%LAC%NE%' OR game_id LIKE '%NWE%LAC%')
    ORDER BY "game_date_yyyy-mm-dd" DESC
""").fetchall()

for r in rows:
    print(f"{r['game_id']}: {r['away_team']}@{r['home_team']} {r['away_score']}-{r['home_score']} on {r['game_date_yyyy-mm-dd']}")

print("\n" + "="*60)
print("PREDICTIONS FOR LAC@NE FROM ensemble_predictions")
print("="*60)
pred_rows = conn.execute("""
    SELECT game_id, COUNT(*) as count, MIN(timestamp) as first, MAX(timestamp) as last
    FROM ensemble_predictions
    WHERE game_id LIKE '%LAC%NE%' OR game_id LIKE '%NWE%LAC%'
    GROUP BY game_id
""").fetchall()

for r in pred_rows:
    print(f"{r['game_id']}: {r['count']} predictions from {r['first']} to {r['last']}")

print("\n" + "="*60)
print("CURRENT QUERY RESULTS (what shows on page)")
print("="*60)
recent_rows = conn.execute("""
    SELECT 
        ep.game_id, ep.away_team, ep.home_team, ep.pred_margin_home, 
        g.away_score, g.home_score, g."game_date_yyyy-mm-dd"
    FROM ensemble_predictions ep
    JOIN games g ON ep.game_id = g.game_id
    WHERE g.away_score IS NOT NULL AND g.home_score IS NOT NULL
    ORDER BY g."game_date_yyyy-mm-dd" DESC, ep.timestamp DESC
    LIMIT 10
""").fetchall()

for i, r in enumerate(recent_rows, 1):
    print(f"{i}. {r['game_id']}: {r['away_team']}@{r['home_team']} pred:{r['pred_margin_home']:.1f} actual:{r['home_score']}-{r['away_score']}")

conn.close()
