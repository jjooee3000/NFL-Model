"""
ESPN Odds Enrichment Script
Fetches and populates betting lines, team records, attendance from ESPN API
"""
import sqlite3
import requests
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path('data/nfl_model.db')

def extract_odds_from_espn(competition):
    """
    Extract betting lines from ESPN competition odds data
    
    Returns dict with:
        - spread (closing line, negative = home favored)
        - total (closing over/under)
        - moneyline_home (e.g., "+130")
        - moneyline_away (e.g., "-155")
        - open_spread (opening line)
        - open_total (opening total)
        - provider (sportsbook name)
    """
    if 'odds' not in competition or not competition['odds']:
        return None
    
    # Use first odds provider (usually Draft Kings)
    odds = competition['odds'][0]
    
    result = {
        'provider': odds.get('provider', {}).get('name', 'Unknown'),
        'spread': odds.get('spread'),  # Closing spread
        'total': odds.get('overUnder'),  # Closing total
    }
    
    # Extract moneylines
    if 'moneyline' in odds:
        ml = odds['moneyline']
        result['moneyline_home'] = ml.get('home', {}).get('close', {}).get('odds')
        result['moneyline_away'] = ml.get('away', {}).get('close', {}).get('odds')
    
    # Extract opening lines
    if 'pointSpread' in odds:
        ps = odds['pointSpread']
        home_open = ps.get('home', {}).get('open', {}).get('line', '')
        if home_open:
            # Parse "+2.5" or "-2.5" to float
            result['open_spread'] = float(home_open.replace('+', ''))
    
    if 'total' in odds:
        total = odds['total']
        over_open = total.get('over', {}).get('open', {}).get('line', '')
        if over_open:
            # Parse "o39.5" to 39.5
            result['open_total'] = float(over_open.replace('o', '').replace('u', ''))
    
    return result

def extract_team_records(competitor):
    """
    Extract team win-loss record from competitor data
    
    Returns tuple: (wins, losses) or (None, None)
    """
    if 'records' not in competitor or not competitor['records']:
        return None, None
    
    # Find 'overall' record
    for record in competitor['records']:
        if record.get('name') == 'overall':
            summary = record.get('summary', '')  # e.g., "14-3"
            if '-' in summary:
                try:
                    wins, losses = summary.split('-')
                    return int(wins), int(losses)
                except:
                    return None, None
    
    return None, None

def fetch_and_enrich_game(game_id, season=2025, week=None):
    """
    Fetch enrichment data for a specific game from ESPN API
    
    Returns dict with all enrichment fields or None if not found
    """
    # ESPN API expects different date formats for different seasons
    # For current/recent games, use the scoreboard endpoint
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    params = {}
    if week:
        params['week'] = week
        params['seasontype'] = 2  # Regular season
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Find the matching game
        for event in data.get('events', []):
            comp = event['competitions'][0]
            
            # Match by teams and approximate date
            competitors = comp['competitors']
            away = next(c for c in competitors if c['homeAway'] == 'away')
            home = next(c for c in competitors if c['homeAway'] == 'home')
            
            # Extract data
            enrichment = {
                'attendance': comp.get('attendance', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Odds
            odds_data = extract_odds_from_espn(comp)
            if odds_data:
                enrichment.update({
                    'odds_spread': odds_data['spread'],
                    'odds_total': odds_data['total'],
                    'odds_moneyline_home': odds_data.get('moneyline_home'),
                    'odds_moneyline_away': odds_data.get('moneyline_away'),
                    'odds_open_spread': odds_data.get('open_spread'),
                    'odds_open_total': odds_data.get('open_total'),
                    'odds_provider': odds_data['provider'],
                })
            
            # Team records
            home_wins, home_losses = extract_team_records(home)
            away_wins, away_losses = extract_team_records(away)
            
            enrichment.update({
                'home_record_wins': home_wins,
                'home_record_losses': home_losses,
                'away_record_wins': away_wins,
                'away_record_losses': away_losses,
            })
            
            # Broadcast
            if 'broadcasts' in comp:
                broadcasts = comp['broadcasts']
                if broadcasts:
                    network = broadcasts[0].get('names', ['Unknown'])[0]
                    enrichment['broadcast_network'] = network
                    # Check if primetime
                    primetime_networks = ['NBC', 'ESPN', 'Amazon']
                    enrichment['broadcast_primetime'] = 1 if network in primetime_networks else 0
            
            return enrichment
        
        return None
        
    except Exception as e:
        print(f"  Error fetching data: {e}")
        return None

def enrich_current_games():
    """Enrich games from current scoreboard (today's games)"""
    
    conn = sqlite3.connect(DB_PATH)
    
    print("\nFetching current scoreboard...")
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        updated = 0
        for event in data.get('events', []):
            comp = event['competitions'][0]
            competitors = comp['competitors']
            
            away = next(c for c in competitors if c['homeAway'] == 'away')
            home = next(c for c in competitors if c['homeAway'] == 'home')
            
            away_team = away['team']['abbreviation']
            home_team = home['team']['abbreviation']
            
            # Map ESPN abbreviations to database abbreviations
            team_map = {'NE': 'NWE', 'KC': 'KAN', 'GB': 'GNB', 'NO': 'NOR', 'SF': 'SFO', 'TB': 'TAM', 'LV': 'LVR'}
            away_team = team_map.get(away_team, away_team)
            home_team = team_map.get(home_team, home_team)
            
            # Find game in database
            game_row = conn.execute("""
                SELECT game_id FROM games 
                WHERE away_team = ? AND home_team = ?
                AND season = 2025
                ORDER BY week DESC
                LIMIT 1
            """, (away_team, home_team)).fetchone()
            
            if not game_row:
                continue
            
            game_id = game_row[0]
            
            # Extract enrichment data
            updates = {}
            
            # Attendance
            if 'attendance' in comp:
                updates['attendance'] = comp['attendance']
            
            # Odds
            odds_data = extract_odds_from_espn(comp)
            if odds_data:
                updates['odds_spread'] = odds_data['spread']
                updates['odds_total'] = odds_data['total']
                updates['odds_moneyline_home'] = odds_data.get('moneyline_home')
                updates['odds_moneyline_away'] = odds_data.get('moneyline_away')
                updates['odds_open_spread'] = odds_data.get('open_spread')
                updates['odds_open_total'] = odds_data.get('open_total')
                updates['odds_provider'] = odds_data['provider']
                updates['odds_timestamp'] = datetime.utcnow().isoformat()
            
            # Team records
            home_wins, home_losses = extract_team_records(home)
            away_wins, away_losses = extract_team_records(away)
            
            if home_wins is not None:
                updates['home_record_wins'] = home_wins
                updates['home_record_losses'] = home_losses
            if away_wins is not None:
                updates['away_record_wins'] = away_wins
                updates['away_record_losses'] = away_losses
            
            # Broadcast
            if 'broadcast' in comp:
                broadcast = comp['broadcast']
                if isinstance(broadcast, str):
                    updates['broadcast_network'] = broadcast.split('/')[0]  # "NBC/Peacock" -> "NBC"
                    primetime = 1 if updates['broadcast_network'] in ['NBC', 'ESPN', 'Amazon'] else 0
                    updates['broadcast_primetime'] = primetime
            
            # Update database
            if updates:
                set_clause = ', '.join([f'"{k}" = ?' for k in updates.keys()])
                values = list(updates.values()) + [game_id]
                
                conn.execute(f'UPDATE games SET {set_clause} WHERE game_id = ?', values)
                
                updated += 1
                odds_status = "✓ odds" if odds_data else "✗ no odds"
                print(f"  ✓ {game_id}: {away_team}@{home_team} - {odds_status}, attendance: {updates.get('attendance', 'N/A')}")
        
        conn.commit()
        print(f"\n✓ Updated {updated} games with enrichment data")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    print("="*80)
    print("ESPN ODDS & ENRICHMENT DATA BACKFILL")
    print("="*80)
    print("\nThis script fetches from ESPN API:")
    print("  - Betting lines (spread, total, moneyline)")
    print("  - Team records (wins/losses)")
    print("  - Attendance")
    print("  - Broadcast network")
    print()
    
    enrich_current_games()
    
    print("\n" + "="*80)
    print("BACKFILL COMPLETE")
    print("="*80)
