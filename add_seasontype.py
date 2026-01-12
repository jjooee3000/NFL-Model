"""
Add seasontype column to database and populate from ESPN API
"""
import sqlite3
from pathlib import Path
import requests

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Adding seasontype column ===\n')

# Check if column exists
cursor = conn.execute("PRAGMA table_info(games)")
columns = [row[1] for row in cursor.fetchall()]

if 'seasontype' not in columns:
    print('Adding seasontype column...')
    conn.execute('ALTER TABLE games ADD COLUMN seasontype INTEGER')
    print('✅ Column added')
else:
    print('✅ Column already exists')

# Populate seasontype from ESPN for recent games
print('\n=== Fetching ESPN data to populate seasontype ===')
url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url, timeout=10)

if response.status_code == 200:
    data = response.json()
    
    for event in data.get('events', []):
        try:
            comps = event['competitions'][0]['competitors']
            away = next(c for c in comps if c['homeAway'] == 'away')
            home = next(c for c in comps if c['homeAway'] == 'home')
            
            away_abbr = away['team']['abbreviation']
            home_abbr = home['team']['abbreviation']
            
            season = event.get('season', {})
            season_year = season.get('year', 0)
            season_type = season.get('type', 0)  # 1=pre, 2=reg, 3=post
            
            # Update database
            result = conn.execute("""
                UPDATE games 
                SET seasontype = ?
                WHERE away_team = ? AND home_team = ? AND season = ?
            """, (season_type, away_abbr, home_abbr, season_year))
            
            if result.rowcount > 0:
                type_label = {1: 'Preseason', 2: 'Regular', 3: 'Postseason'}.get(season_type, 'Unknown')
                print(f'  ✅ {away_abbr}@{home_abbr} → seasontype={season_type} ({type_label})')
        except Exception as e:
            continue
    
    conn.commit()
    print('\n✅ Seasontype populated from ESPN')
else:
    print(f'❌ ESPN API error: {response.status_code}')

# Set default seasontype for older games based on week number
print('\n=== Setting default seasontype for older games ===')
conn.execute("""
    UPDATE games 
    SET seasontype = 2 
    WHERE seasontype IS NULL AND week >= 1 AND week <= 18
""")
conn.execute("""
    UPDATE games 
    SET seasontype = 3 
    WHERE seasontype IS NULL AND week > 18
""")
conn.commit()
print('✅ Default seasontype set (weeks 1-18=Regular, >18=Postseason)')

# Verify
print('\n=== Verification ===')
rows = conn.execute("""
    SELECT seasontype, COUNT(*) as cnt
    FROM games
    GROUP BY seasontype
    ORDER BY seasontype
""").fetchall()

for row in rows:
    st = row[0] if row[0] is not None else 'NULL'
    label = {1: 'Preseason', 2: 'Regular', 3: 'Postseason', 'NULL': 'NULL'}.get(st, st)
    print(f'  seasontype {st} ({label}): {row[1]} games')

conn.close()
print('\n✅ Done!')
