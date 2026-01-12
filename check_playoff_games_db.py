"""
Check current playoff games in database - find the wrong entries
"""
import sqlite3
from pathlib import Path

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

# Check the specific playoff matchups
matchups = [
    ('LAC', 'NE'),
    ('BUF', 'JAX'),
    ('SF', 'PHI'),
    ('LAR', 'CAR'),
    ('GB', 'CHI'),
    ('HOU', 'PIT')
]

print('=== Database entries for current playoff matchups ===\n')

for away, home in matchups:
    print(f'{away} @ {home}:')
    rows = conn.execute("""
        SELECT game_id, season, week, seasontype, "game_date_yyyy-mm-dd", away_score, home_score
        FROM games
        WHERE away_team = ? AND home_team = ?
        ORDER BY season DESC, week DESC
    """, (away, home)).fetchall()
    
    if rows:
        for row in rows:
            seasontype = row[3] if row[3] else 'NULL'
            print(f'  • {row[0]} - S{row[1]} W{row[2]} ({seasontype}) - {row[4]} - {row[5]} vs {row[6]}')
    else:
        print(f'  NO ENTRIES FOUND')
    print()

# Check for Week 19 entries
print('\n=== All Week 19 entries (should be playoff week 1) ===')
rows = conn.execute("""
    SELECT game_id, season, week, seasontype, "game_date_yyyy-mm-dd", away_team, home_team
    FROM games
    WHERE week = 19
    ORDER BY "game_date_yyyy-mm-dd"
""").fetchall()

if rows:
    for row in rows:
        seasontype = row[3] if row[3] else 'NULL'
        print(f'  {row[0]} - {row[5]}@{row[6]} - {row[4]} - seasontype:{seasontype}')
else:
    print('  NO WEEK 19 ENTRIES')

# Check database schema for seasontype column
print('\n=== Checking seasontype values ===')
rows = conn.execute("""
    SELECT DISTINCT seasontype, COUNT(*) as cnt
    FROM games
    GROUP BY seasontype
    ORDER BY seasontype
""").fetchall()

for row in rows:
    st = row[0] if row[0] else 'NULL'
    print(f'  seasontype = {st}: {row[1]} games')

conn.close()
