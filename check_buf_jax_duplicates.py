import sqlite3
from pathlib import Path

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== All BUF@JAX entries in database ===')
rows = conn.execute("""
    SELECT game_id, season, week, "game_date_yyyy-mm-dd", away_team, home_team, away_score, home_score
    FROM games 
    WHERE (away_team = 'BUF' AND home_team = 'JAX') OR (away_team = 'JAX' AND home_team = 'BUF')
    ORDER BY season, week, "game_date_yyyy-mm-dd"
""").fetchall()

print(f'Found {len(rows)} BUF@JAX entries:')
for row in rows:
    print(f'  {row}')

print('\n=== Checking for other duplicates (same matchup, same week) ===')
rows_dups = conn.execute("""
    SELECT away_team, home_team, season, week, COUNT(*) as cnt
    FROM games
    GROUP BY away_team, home_team, season, week
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
    LIMIT 10
""").fetchall()

if rows_dups:
    print(f'Found {len(rows_dups)} matchups with duplicates:')
    for row in rows_dups:
        print(f'  {row[0]}@{row[1]} - Season {row[2]} Week {row[3]}: {row[4]} entries')
else:
    print('No duplicates found')

conn.close()
