"""
Check current playoff games in database without seasontype
"""
import sqlite3
from pathlib import Path

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

# Check the specific playoff matchups that ESPN says happened
matchups = [
    ('LAC', 'NE', '2026-01-12'),      # ESPN says this date
    ('BUF', 'JAX', '2026-01-11'),     # ESPN says this date  
    ('SF', 'PHI', '2026-01-11'),      # ESPN says this date
    ('LAR', 'CAR', '2026-01-10'),     # ESPN says this date
    ('GB', 'CHI', '2026-01-11'),      # ESPN says this date
    ('HOU', 'PIT', '2026-01-13')      # ESPN says this date
]

print('=== Database entries for current playoff matchups ===\n')
print('ESPN says these games are Season 2025, Postseason Week 1')
print('Dates: January 10-13, 2026\n')

for away, home, espn_date in matchups:
    print(f'{away} @ {home} (ESPN date: {espn_date}):')
    rows = conn.execute("""
        SELECT game_id, season, week, "game_date_yyyy-mm-dd", away_score, home_score
        FROM games
        WHERE away_team = ? AND home_team = ?
        ORDER BY "game_date_yyyy-mm-dd" DESC
        LIMIT 5
    """, (away, home)).fetchall()
    
    if rows:
        for row in rows:
            score_str = f'{row[4]} - {row[5]}' if row[4] is not None else 'NULL - NULL'
            date_match = '✅' if row[3] == espn_date or row[3] == espn_date.replace('2026', '2025') else '❌'
            print(f'  {date_match} {row[0]} - S{row[1]} W{row[2]} - {row[3]} - Score: {score_str}')
    else:
        print(f'  ❌ NO ENTRIES FOUND')
    print()

# Find the bad BUF@JAX entry
print('\n=== BUF@JAX entries detail ===')
rows = conn.execute("""
    SELECT game_id, season, week, "game_date_yyyy-mm-dd", away_score, home_score
    FROM games
    WHERE away_team = 'BUF' AND home_team = 'JAX'
    ORDER BY season DESC, week DESC
""").fetchall()

for row in rows:
    score_str = f'{row[4]} - {row[5]}' if row[4] is not None else 'NULL - NULL'
    print(f'  {row[0]} - S{row[1]} W{row[2]} - {row[3]} - Score: {score_str}')

# The problem: 2025_W01_BUF_JAX has date 2025-09-07 which is regular season Week 1
# But the actual Week 1 regular season BUF@JAX game hasn't happened yet!
# This is actually the PLAYOFF game with the wrong date

conn.close()
