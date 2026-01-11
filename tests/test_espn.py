import sys
sys.path.insert(0, "src")
from utils.schedule import fetch_espn_schedule
import requests

# Test current ESPN scoreboard
print("Testing ESPN API...")
r = requests.get('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard')
data = r.json()

if 'events' in data:
    print(f"\nCurrent games on scoreboard: {len(data['events'])}")
    for event in data['events'][:5]:
        name = event.get('name', '')
        status = event.get('status', {}).get('type', {}).get('description', '')
        print(f"  {name} - {status}")

# Try playoffs (seasontype=3)
print("\n\nTrying playoffs (seasontype=3)...")
r = requests.get('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard', 
                 params={'seasontype': 3})
data = r.json()

if 'events' in data:
    print(f"Playoff games: {len(data['events'])}")
    for event in data['events'][:5]:
        name = event.get('name', '')
        status = event.get('status', {}).get('type', {}).get('description', '')
        completed = event.get('status', {}).get('type', {}).get('completed', False)
        print(f"  {name} - {status} (completed: {completed})")
