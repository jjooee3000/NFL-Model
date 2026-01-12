"""
Check ESPN API for today's games and live scores
"""
import requests
import json
from datetime import datetime

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    events = data.get('events', [])
    
    print(f"=== ESPN Scoreboard ({len(events)} games found) ===\n")
    
    for event in events:
        name = event.get('name', '')
        short_name = event.get('shortName', '')
        date = event.get('date', '')
        status = event['status']['type']['name']
        status_detail = event['status']['type']['detail']
        state = event['status']['type']['state']
        
        comps = event['competitions'][0]['competitors']
        away = next(c for c in comps if c['homeAway'] == 'away')
        home = next(c for c in comps if c['homeAway'] == 'home')
        
        away_team = away['team']['abbreviation']
        home_team = home['team']['abbreviation']
        away_score = away.get('score', '0')
        home_score = home.get('score', '0')
        
        # Extract time
        game_time = None
        try:
            dt = datetime.strptime(date, '%Y-%m-%dT%H:%M%SZ')
            game_time = dt.strftime('%I:%M %p ET')
        except:
            game_time = status_detail
        
        print(f"{short_name}")
        print(f"  Status: {status} ({state}) - {status_detail}")
        print(f"  Score: {away_team} {away_score} @ {home_team} {home_score}")
        print(f"  Time: {game_time}")
        print(f"  Date: {date}")
        print()
else:
    print(f"Error fetching ESPN API: {response.status_code}")
