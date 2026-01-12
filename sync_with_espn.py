"""
Sync database with ESPN API data (treating ESPN as authoritative)
This will:
1. Fix incorrect dates
2. Update scores from ESPN 
3. Identify and mark misplaced games
4. Create proper playoff game entries
"""
import sqlite3
from pathlib import Path
import requests
from datetime import datetime

# Fetch authoritative ESPN data
print('=== Fetching ESPN API (authoritative source) ===')
url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url, timeout=10)

if response.status_code != 200:
    print(f'ESPN API error: {response.status_code}')
    exit(1)

data = response.json()
espn_games = []

for event in data.get('events', []):
    try:
        # Basic info
        status_info = event['status']['type']
        state = status_info['state']
        
        comps = event['competitions'][0]['competitors']
        away = next(c for c in comps if c['homeAway'] == 'away')
        home = next(c for c in comps if c['homeAway'] == 'home')
        
        away_abbr = away['team']['abbreviation']
        home_abbr = home['team']['abbreviation']
        away_score = int(away.get('score', 0)) if state != 'pre' else None
        home_score = int(home.get('score', 0)) if state != 'pre' else None
        
        # Date and time
        game_date = event.get('date', '')
        date_only = game_date.split('T')[0] if game_date else ''
        
        # Season/week info
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
        print(f'Error parsing event: {e}')
        continue

print(f'✅ ESPN returned {len(espn_games)} games')
print()

# Connect to database
db = Path('data/nfl_model.db')
conn = sqlite3.connect(db)

print('=== Analysis and Fixes ===\n')

issues_found = []
fixes_to_apply = []

for espn_game in espn_games:
    away = espn_game['away']
    home = espn_game['home']
    espn_date = espn_game['date']
    espn_week = espn_game['week']
    espn_season = espn_game['season']
    espn_season_type = espn_game['season_type']
    
    print(f"{espn_game['short_name']} - ESPN: {espn_season} S{espn_season_type} W{espn_week} - {espn_date}")
    
    # Find matching games in database
    db_rows = conn.execute("""
        SELECT game_id, season, week, "game_date_yyyy-mm-dd", away_score, home_score
        FROM games
        WHERE away_team = ? AND home_team = ? AND season = ?
        ORDER BY week DESC
    """, (away, home, espn_season)).fetchall()
    
    if len(db_rows) == 0:
        print(f'  ⚠️  NOT FOUND - Need to create entry')
        issues_found.append(f'MISSING: {away}@{home} S{espn_season} W{espn_week}')
    elif len(db_rows) == 1:
        db_row = db_rows[0]
        game_id = db_row[0]
        db_date = db_row[3]
        db_week = db_row[2]
        db_away_score = db_row[4]
        db_home_score = db_row[5]
        
        issues = []
        
        # Check date
        if db_date != espn_date:
            issues.append(f'DATE: {db_date} → {espn_date}')
            fixes_to_apply.append(('UPDATE games SET "game_date_yyyy-mm-dd" = ? WHERE game_id = ?', (espn_date, game_id)))
        
        # Check scores (if game is finished)
        if espn_game['away_score'] is not None and espn_game['home_score'] is not None:
            if db_away_score != espn_game['away_score'] or db_home_score != espn_game['home_score']:
                issues.append(f"SCORE: {db_away_score}-{db_home_score} → {espn_game['away_score']}-{espn_game['home_score']}")
                fixes_to_apply.append(('UPDATE games SET away_score = ?, home_score = ? WHERE game_id = ?', 
                                      (espn_game['away_score'], espn_game['home_score'], game_id)))
        
        # Check week number
        if db_week != espn_week:
            issues.append(f'WEEK: {db_week} → {espn_week}')
            # Don't auto-fix week number - this could be a different game
        
        if issues:
            print(f'  ❌ DB: {game_id} - Issues: {", ".join(issues)}')
            issues_found.append(f'{game_id}: {", ".join(issues)}')
        else:
            print(f'  ✅ DB: {game_id} - Match OK')
    
    else:
        print(f'  ⚠️  {len(db_rows)} entries - Need to identify correct one')
        for db_row in db_rows:
            print(f'     • {db_row[0]} - W{db_row[2]} - {db_row[3]}')
        issues_found.append(f'DUPLICATES: {away}@{home} S{espn_season} ({len(db_rows)} entries)')
    
    print()

# Check for the misplaced Week 1 games
print('\n=== Checking for misplaced Week 1 entries ===')
misplaced = conn.execute("""
    SELECT game_id, away_team, home_team, "game_date_yyyy-mm-dd", away_score, home_score
    FROM games
    WHERE season = 2025 AND week = 1 AND "game_date_yyyy-mm-dd" LIKE '2025-09%'
""").fetchall()

for row in misplaced:
    game_id = row[0]
    # Check if this is actually a playoff game
    matchup = f"{row[1]}@{row[2]}"
    playoff_matchups = [f"{g['away']}@{g['home']}" for g in espn_games]
    
    if matchup in playoff_matchups:
        print(f'  ❌ {game_id} - {matchup} - {row[3]} - MISLABELED PLAYOFF GAME')
        issues_found.append(f'MISLABELED: {game_id} is playoff game marked as Week 1')
    else:
        print(f'  ✅ {game_id} - {matchup} - Legitimate Week 1 game')

print(f'\n=== Summary ===')
print(f'Total issues found: {len(issues_found)}')
print(f'Fixes to apply: {len(fixes_to_apply)}')
print()

if fixes_to_apply:
    print('Fixes that would be applied:')
    for sql, params in fixes_to_apply:
        print(f'  {sql} | {params}')
    print()
    
    response = input('Apply these fixes? (yes/no): ')
    if response.lower() == 'yes':
        for sql, params in fixes_to_apply:
            conn.execute(sql, params)
        conn.commit()
        print(f'✅ Applied {len(fixes_to_apply)} fixes')
    else:
        print('❌ No changes made')
else:
    print('No automatic fixes needed')

print('\n=== Issues that need manual review ===')
for issue in issues_found:
    print(f'  • {issue}')

conn.close()
