"""
Final cleanup based on ESPN authoritative data
"""
import sqlite3
from pathlib import Path

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Final ESPN-based cleanup ===\n')

# The issue: We have duplicates for GB@CHI
# 2025_W01_GB_CHI with date 2026-01-11 and NULL scores - this is the PLAYOFF game with wrong week number
# 2025_W19_GB_CHI with date 2025-01-10 and scores 27-31 - this has the right scores but wrong date

# ESPN says: GB@CHI playoff game is 2026-01-11 with score 27-31

# Solution: Keep 2025_W19_GB_CHI, fix its date, delete 2025_W01_GB_CHI

fixes = [
    # Fix LAR@CAR date (2025 -> 2026)
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-10' WHERE game_id = '2025_W19_LAR_CAR'", "Fix LAR@CAR date to 2026"),
    
    # Fix GB@CHI W19 date (2025 -> 2026) and keep it
    ("UPDATE games SET \"game_date_yyyy-mm-dd\" = '2026-01-11' WHERE game_id = '2025_W19_GB_CHI'", "Fix GB@CHI W19 date to 2026"),
    
    # Delete the misplaced W01 GB@CHI entry
    ("DELETE FROM games WHERE game_id = '2025_W01_GB_CHI'", "Delete misplaced GB@CHI W01 entry"),
    
    # Update GB@CHI scores if needed
    ("UPDATE games SET away_score = 27, home_score = 31 WHERE game_id = '2025_W19_GB_CHI'", "Ensure GB@CHI has correct scores"),
]

for sql, description in fixes:
    try:
        cursor = conn.execute(sql)
        affected = cursor.rowcount
        print(f'✅ {description} - {affected} row(s) affected')
    except Exception as e:
        print(f'❌ {description} - ERROR: {e}')

conn.commit()

# Final verification against ESPN data
print('\n=== Final Verification Against ESPN ===\n')

espn_playoff_games = [
    ('LAC', 'NE', '2026-01-12', 3, 9, '2025_W19_LAC_NE'),
    ('BUF', 'JAX', '2026-01-11', 27, 24, '2025_W01_BUF_JAX'),  # Note: Still W01 ID but correct date
    ('SF', 'PHI', '2026-01-11', 23, 19, '2025_W19_SF_PHI'),
    ('LAR', 'CAR', '2026-01-10', 34, 31, '2025_W19_LAR_CAR'),
    ('GB', 'CHI', '2026-01-11', 27, 31, '2025_W19_GB_CHI'),
    ('HOU', 'PIT', '2026-01-13', None, None, '2025_W19_HOU_PIT'),  # Not played yet
]

for away, home, espn_date, espn_away, espn_home, expected_id in espn_playoff_games:
    row = conn.execute("""
        SELECT game_id, "game_date_yyyy-mm-dd", away_score, home_score
        FROM games
        WHERE game_id = ?
    """, (expected_id,)).fetchone()
    
    if row:
        date_ok = '✅' if row[1] == espn_date else f'❌ {row[1]}'
        if espn_away is not None:
            score_ok = '✅' if (row[2] == espn_away and row[3] == espn_home) else f'❌ {row[2]}-{row[3]}'
            print(f'{away}@{home}: Date {date_ok}, Score {score_ok}')
        else:
            print(f'{away}@{home}: Date {date_ok}, Score not played yet')
    else:
        print(f'{away}@{home}: ❌ NOT FOUND in database')

# Check for any remaining same-season duplicates
print('\n=== Duplicate check ===')
dups = conn.execute("""
    SELECT away_team, home_team, season, COUNT(*) as cnt
    FROM games
    WHERE season = 2025
    GROUP BY away_team, home_team, season
    HAVING COUNT(*) > 1
""").fetchall()

if dups:
    print(f'Found {len(dups)} duplicate matchups in 2025 season:')
    for row in dups:
        print(f'  {row[0]}@{row[1]}: {row[3]} entries')
        # Show details
        details = conn.execute("""
            SELECT game_id, week, "game_date_yyyy-mm-dd"
            FROM games
            WHERE away_team = ? AND home_team = ? AND season = 2025
        """, (row[0], row[1])).fetchall()
        for d in details:
            print(f'    • {d[0]} - W{d[1]} - {d[2]}')
else:
    print('✅ No duplicates found in 2025 season')

conn.close()
print('\n✅ All ESPN-based fixes complete!')
