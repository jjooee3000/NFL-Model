"""
Compare ESPN API data with database to find conflicts and gaps.
Treat ESPN as authoritative source.
"""
import sqlite3
from pathlib import Path
import requests
from datetime import datetime

# Fetch ESPN data
print('=== Fetching ESPN API data ===')
url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url, timeout=10)

if response.status_code != 200:
    print(f'ESPN API error: {response.status_code}')
    exit(1)

data = response.json()
espn_games = []

for event in data.get('events', []):
    try:
        status_info = event['status']['type']
        state = status_info['state']
        
        comps = event['competitions'][0]['competitors']
        away = next(c for c in comps if c['homeAway'] == 'away')
        home = next(c for c in comps if c['homeAway'] == 'home')
        
        away_abbr = away['team']['abbreviation']
        home_abbr = home['team']['abbreviation']
        away_score = int(away.get('score', 0))
        home_score = int(home.get('score', 0))
        
        game_date = event.get('date', '')
        date_only = game_date.split('T')[0] if game_date else ''
        
        # Get week and season info
        season = event.get('season', {})
        week_info = event.get('week', {})
        week_num = week_info.get('number', 0)
        season_type = season.get('type', 0)  # 1=pre, 2=reg, 3=post
        season_year = season.get('year', 0)
        
        espn_games.append({
            'away': away_abbr,
            'home': home_abbr,
            'away_score': away_score,
            'home_score': home_score,
            'date': date_only,
            'week': week_num,
            'season': season_year,
            'season_type': season_type,
            'state': state,
            'short_name': event.get('shortName', '')
        })
    except Exception as e:
        continue

print(f'ESPN API returned {len(espn_games)} games')
print()

# Get database data
db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Comparing ESPN vs Database ===')
print()

# Check each ESPN game against database
for espn_game in espn_games:
    away = espn_game['away']
    home = espn_game['home']
    
    # Try to find matching game in DB
    db_rows = conn.execute("""
        SELECT game_id, season, week, "game_date_yyyy-mm-dd", away_team, home_team, away_score, home_score
        FROM games
        WHERE away_team = ? AND home_team = ?
        ORDER BY season DESC, week DESC
    """, (away, home)).fetchall()
    
    print(f'{espn_game["short_name"]} ({espn_game["state"]})')
    print(f'  ESPN: {away} {espn_game["away_score"]} @ {home} {espn_game["home_score"]} - {espn_game["date"]} - Week {espn_game["week"]}')
    
    if len(db_rows) == 0:
        print(f'  ⚠️  NOT FOUND IN DATABASE')
    elif len(db_rows) == 1:
        db_row = db_rows[0]
        db_date = db_row[3]
        db_away_score = db_row[6] if db_row[6] is not None else 'NULL'
        db_home_score = db_row[7] if db_row[7] is not None else 'NULL'
        
        issues = []
        if db_date != espn_game['date']:
            issues.append(f"DATE MISMATCH (DB: {db_date}, ESPN: {espn_game['date']})")
        if str(db_away_score) != str(espn_game['away_score']) and db_away_score != 'NULL':
            issues.append(f"AWAY SCORE MISMATCH (DB: {db_away_score}, ESPN: {espn_game['away_score']})")
        if str(db_home_score) != str(espn_game['home_score']) and db_home_score != 'NULL':
            issues.append(f"HOME SCORE MISMATCH (DB: {db_home_score}, ESPN: {espn_game['home_score']})")
        
        if issues:
            print(f'  ❌ DB: {db_row[0]} - {db_row[4]} {db_away_score} @ {db_row[5]} {db_home_score} - {db_date}')
            for issue in issues:
                print(f'     • {issue}')
        else:
            print(f'  ✅ DB: {db_row[0]} - Matches')
    else:
        print(f'  ⚠️  {len(db_rows)} DUPLICATE ENTRIES IN DATABASE:')
        for db_row in db_rows:
            db_date = db_row[3]
            db_away_score = db_row[6] if db_row[6] is not None else 'NULL'
            db_home_score = db_row[7] if db_row[7] is not None else 'NULL'
            print(f'     • {db_row[0]} - {db_row[4]} {db_away_score} @ {db_row[5]} {db_home_score} - {db_date} (S{db_row[1]} W{db_row[2]})')
    
    print()

conn.close()
