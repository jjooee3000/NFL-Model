"""
Fix game dates in database - change 2026 to 2025 for playoff games
"""
import sqlite3
from pathlib import Path

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Checking games with 2026 dates ===')
rows = conn.execute("""
    SELECT game_id, "game_date_yyyy-mm-dd", away_team, home_team 
    FROM games 
    WHERE season=2025 AND "game_date_yyyy-mm-dd" LIKE '2026-%'
""").fetchall()

print(f'Found {len(rows)} games with 2026 dates:')
for row in rows:
    print(f'  {row}')

if len(rows) > 0:
    print('\n=== Fixing dates (2026 → 2025) ===')
    conn.execute("""
        UPDATE games 
        SET "game_date_yyyy-mm-dd" = REPLACE("game_date_yyyy-mm-dd", '2026-', '2025-')
        WHERE season=2025 AND "game_date_yyyy-mm-dd" LIKE '2026-%'
    """)
    conn.commit()
    print(f'✓ Updated {len(rows)} games')
    
    # Verify
    print('\n=== Verification ===')
    rows_after = conn.execute("""
        SELECT game_id, "game_date_yyyy-mm-dd", away_team, home_team 
        FROM games 
        WHERE season=2025 AND week=19 
        LIMIT 5
    """).fetchall()
    for row in rows_after:
        print(f'  {row}')

conn.close()
print('\nDone!')
