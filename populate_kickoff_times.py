"""
Populate kickoff_time_local from ESPN API timestamps
"""
import sqlite3
from pathlib import Path
import requests
from datetime import datetime
import pytz

db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Populating kickoff_time_local from ESPN ===\n')

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url, timeout=10)

if response.status_code == 200:
    data = response.json()
    eastern = pytz.timezone('America/New_York')
    
    for event in data.get('events', []):
        try:
            comps = event['competitions'][0]['competitors']
            away = next(c for c in comps if c['homeAway'] == 'away')
            home = next(c for c in comps if c['homeAway'] == 'home')
            
            away_abbr = away['team']['abbreviation']
            home_abbr = home['team']['abbreviation']
            
            # Parse date from ISO timestamp
            game_date = event.get('date', '')
            if game_date:
                # Parse UTC timestamp
                dt_utc = datetime.strptime(game_date, '%Y-%m-%dT%H:%M%SZ')
                dt_utc = pytz.utc.localize(dt_utc)
                
                # Convert to Eastern Time
                dt_eastern = dt_utc.astimezone(eastern)
                
                # Format as "8:15 PM ET"
                time_str = dt_eastern.strftime('%I:%M %p ET').lstrip('0')
                
                # Update database
                season_year = event.get('season', {}).get('year', 0)
                result = conn.execute("""
                    UPDATE games 
                    SET kickoff_time_local = ?
                    WHERE away_team = ? AND home_team = ? AND season = ?
                """, (time_str, away_abbr, home_abbr, season_year))
                
                if result.rowcount > 0:
                    print(f'  ✅ {away_abbr}@{home_abbr} → {time_str}')
        except Exception as e:
            print(f'  ❌ Error parsing {event.get("shortName", "unknown")}: {e}')
            continue
    
    conn.commit()
    print('\n✅ Kickoff times populated from ESPN')
else:
    print(f'❌ ESPN API error: {response.status_code}')

# Verify
print('\n=== Verification ===')
rows = conn.execute("""
    SELECT game_id, away_team, home_team, kickoff_time_local
    FROM games
    WHERE kickoff_time_local IS NOT NULL
    ORDER BY game_id DESC
    LIMIT 10
""").fetchall()

print('Recent games with kickoff times:')
for row in rows:
    print(f'  {row[0]}: {row[1]}@{row[2]} - {row[3]}')

conn.close()
print('\n✅ Done!')
