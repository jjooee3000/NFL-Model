"""
Apply ESPN synchronization fixes automatically
"""
import sqlite3
from pathlib import Path

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Applying ESPN-based fixes ===\n')

fixes = [
    # Fix dates
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-12' WHERE game_id = '2025_W19_LAC_NE'", "LAC@NE date"),
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-11' WHERE game_id = '2025_W01_BUF_JAX'", "BUF@JAX date (was Sept, should be Jan)"),
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-11' WHERE game_id = '2025_W19_SF_PHI'", "SF@PHI date"),
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-13' WHERE game_id = '2025_W19_HOU_PIT'", "HOU@PIT date"),
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-11' WHERE game_id = '2025_W01_GB_CHI'", "GB@CHI date (was Sept, should be Jan)"),
    
    # Fix scores for live/completed games
    ("UPDATE games SET away_score = 3, home_score = 9 WHERE game_id = '2025_W19_LAC_NE'", "LAC@NE score"),
    
    # Delete duplicate/wrong entries
    ("DELETE FROM games WHERE game_id = '2025_W13_LAR_CAR'", "Delete duplicate LAR@CAR (regular season game)"),
    ("DELETE FROM games WHERE game_id = '2025_W16_GB_CHI'", "Delete duplicate GB@CHI (Week 16 regular season)"),
]

for sql, description in fixes:
    try:
        cursor = conn.execute(sql)
        affected = cursor.rowcount
        print(f'✅ {description} - {affected} row(s) affected')
    except Exception as e:
        print(f'❌ {description} - ERROR: {e}')

conn.commit()

# Verify the fixes
print('\n=== Verification ===\n')

# Check playoff games
playoff_games = [
    ('2025_W19_LAC_NE', 'LAC', 'NE'),
    ('2025_W01_BUF_JAX', 'BUF', 'JAX'),
    ('2025_W19_SF_PHI', 'SF', 'PHI'),
    ('2025_W19_LAR_CAR', 'LAR', 'CAR'),
    ('2025_W01_GB_CHI', 'GB', 'CHI'),
    ('2025_W19_HOU_PIT', 'HOU', 'PIT'),
]

for game_id, away, home in playoff_games:
    row = conn.execute("""
        SELECT game_id, "game_date_yyyy-mm-dd", away_score, home_score
        FROM games
        WHERE game_id = ?
    """, (game_id,)).fetchone()
    
    if row:
        print(f'{game_id}: {row[1]} - {away} {row[2]} @ {home} {row[3]}')
    else:
        print(f'{game_id}: NOT FOUND (may have been deleted)')

# Check for remaining duplicates
print('\n=== Remaining duplicates check ===')
for away, home in [('LAR', 'CAR'), ('GB', 'CHI')]:
    rows = conn.execute("""
        SELECT game_id, week, "game_date_yyyy-mm-dd"
        FROM games
        WHERE away_team = ? AND home_team = ? AND season = 2025
    """, (away, home)).fetchall()
    
    print(f'{away}@{home}: {len(rows)} entries')
    for row in rows:
        print(f'  • {row[0]} - W{row[1]} - {row[2]}')

conn.close()
print('\n✅ Done!')
