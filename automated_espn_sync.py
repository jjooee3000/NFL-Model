"""
Automated ESPN sync process - Run daily to keep database in sync
"""
import sqlite3
from pathlib import Path
import requests
from datetime import datetime
import pytz

def sync_with_espn():
    """Sync database with ESPN scoreboard API"""
    
    db = Path('data/nfl_model.db')
    conn = sqlite3.connect(db)
    
    print(f'=== ESPN Sync - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===\n')
    
    # Fetch ESPN data
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f'❌ ESPN API error: {e}')
        conn.close()
        return False
    
    data = response.json()
    games_updated = 0
    scores_updated = 0
    times_updated = 0
    
    eastern = pytz.timezone('America/New_York')
    
    for event in data.get('events', []):
        try:
            # Extract game data
            comps = event['competitions'][0]['competitors']
            away = next(c for c in comps if c['homeAway'] == 'away')
            home = next(c for c in comps if c['homeAway'] == 'home')
            
            away_abbr = away['team']['abbreviation']
            home_abbr = home['team']['abbreviation']
            away_score = int(away.get('score', 0))
            home_score = int(home.get('score', 0))
            
            # Date and time
            game_date = event.get('date', '')
            date_only = game_date.split('T')[0] if game_date else None
            
            # Parse kickoff time
            kickoff_time = None
            if game_date:
                dt_utc = datetime.strptime(game_date, '%Y-%m-%dT%H:%M%SZ')
                dt_utc = pytz.utc.localize(dt_utc)
                dt_eastern = dt_utc.astimezone(eastern)
                kickoff_time = dt_eastern.strftime('%I:%M %p ET').lstrip('0')
            
            # Season info
            season = event.get('season', {})
            season_year = season.get('year', 0)
            season_type = season.get('type', 0)
            
            # Game status
            status_info = event['status']['type']
            state = status_info['state']
            
            # Find matching game in database
            db_game = conn.execute("""
                SELECT game_id, "game_date_yyyy-mm-dd", away_score, home_score, kickoff_time_local, seasontype
                FROM games
                WHERE away_team = ? AND home_team = ? AND season = ?
                ORDER BY week DESC
                LIMIT 1
            """, (away_abbr, home_abbr, season_year)).fetchone()
            
            if db_game:
                game_id = db_game[0]
                updates = []
                params = []
                
                # Check date
                if date_only and db_game[1] != date_only:
                    updates.append('"game_date_yyyy-mm-dd" = ?')
                    params.append(date_only)
                
                # Check scores (only update if game is in progress or final)
                if state in ('in', 'post'):
                    if db_game[2] != away_score or db_game[3] != home_score:
                        updates.append('away_score = ?')
                        updates.append('home_score = ?')
                        params.extend([away_score, home_score])
                        scores_updated += 1
                
                # Check kickoff time
                if kickoff_time and db_game[4] != kickoff_time:
                    updates.append('kickoff_time_local = ?')
                    params.append(kickoff_time)
                    times_updated += 1
                
                # Check seasontype
                if season_type and db_game[5] != season_type:
                    updates.append('seasontype = ?')
                    params.append(season_type)
                
                # Apply updates
                if updates:
                    sql = f"UPDATE games SET {', '.join(updates)} WHERE game_id = ?"
                    params.append(game_id)
                    conn.execute(sql, params)
                    games_updated += 1
                    print(f'  ✅ Updated {game_id}: {away_abbr}@{home_abbr}')
        
        except Exception as e:
            print(f'  ⚠️  Error processing game: {e}')
            continue
    
    conn.commit()
    conn.close()
    
    print(f'\n=== Sync Complete ===')
    print(f'Games updated: {games_updated}')
    print(f'Scores updated: {scores_updated}')
    print(f'Times updated: {times_updated}')
    
    return True

if __name__ == '__main__':
    sync_with_espn()
