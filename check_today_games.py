import sqlite3
from pathlib import Path
import datetime

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Sample Week 19 Games with kickoff_time_local ===')
rows = conn.execute("""
    SELECT game_id, "game_date_yyyy-mm-dd" as date, kickoff_time_local, away_team, home_team 
    FROM games 
    WHERE season=2025 AND week=19 
    LIMIT 5
""").fetchall()
for row in rows:
    print(row)

print('\n=== Today\'s Games Check ===')
today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
print(f'Today (UTC): {today}')

rows_today = conn.execute("""
    SELECT game_id, "game_date_yyyy-mm-dd" as date, kickoff_time_local, away_team, home_team, away_score, home_score
    FROM games 
    WHERE "game_date_yyyy-mm-dd" = ?
""", (today,)).fetchall()

if rows_today:
    for row in rows_today:
        print(row)
else:
    print('No games found for today')

# Check for games on 2025-01-12 (typical playoff date)
print('\n=== Games on 2025-01-12 ===')
rows_jan12 = conn.execute("""
    SELECT game_id, "game_date_yyyy-mm-dd" as date, kickoff_time_local, away_team, home_team, away_score, home_score
    FROM games 
    WHERE "game_date_yyyy-mm-dd" = '2025-01-12'
""").fetchall()
for row in rows_jan12:
    print(row)

conn.close()
