"""Find and extract a game WITH odds data"""
import requests
import json

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url, timeout=10)
data = response.json()

for event in data['events']:
    comp = event['competitions'][0]
    
    if 'odds' in comp and comp['odds']:
        print(f"Found game with odds: {event['name']}")
        print("\nOdds data:")
        print(json.dumps(comp['odds'], indent=2))
        
        # Save full event to file
        with open('espn_game_with_odds.json', 'w') as f:
            json.dump(event, f, indent=2)
        print("\n✓ Saved full game data to espn_game_with_odds.json")
        break
else:
    print("No games with odds found in current scoreboard")
    print("\nThis is likely because:")
    print("  - Current games are playoff games (live)")
    print("  - Odds are removed once games start")
    print("  - Need to fetch upcoming games for odds data")
