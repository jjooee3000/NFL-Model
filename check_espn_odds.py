"""Check ESPN API for odds availability"""
import requests
import json

print("="*80)
print("ESPN API ODDS DATA EXPLORATION")
print("="*80)

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

try:
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if 'events' in data and len(data['events']) > 0:
        print(f"\nFound {len(data['events'])} games in scoreboard")
        
        games_with_odds = 0
        odds_providers = set()
        
        for i, event in enumerate(data['events']):
            comp = event['competitions'][0]
            
            # Check if odds exist
            if 'odds' in comp and comp['odds']:
                games_with_odds += 1
                
                if i == 0:  # Show details for first game
                    print(f"\n{'='*60}")
                    print(f"SAMPLE GAME: {event['name']}")
                    print(f"{'='*60}")
                    print("\nOdds data structure:")
                    print(json.dumps(comp['odds'], indent=2))
                
                # Collect provider names
                for odd in comp['odds']:
                    if 'provider' in odd and 'name' in odd['provider']:
                        odds_providers.add(odd['provider']['name'])
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Games with odds: {games_with_odds}/{len(data['events'])}")
        print(f"Odds providers found: {odds_providers if odds_providers else 'None'}")
        
        if games_with_odds == 0:
            print("\n⚠ WARNING: No odds data available in current scoreboard")
            print("Possible reasons:")
            print("  1. Games are playoff games (odds may not be in scoreboard API)")
            print("  2. Odds not available for completed games")
            print("  3. Need to check individual game endpoints")
            print("\nRecommendation: Check ESPN game summary API for odds")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
