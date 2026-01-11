import requests
import json
API_KEY = "e4fe23404e83e54cae3a61eff5772094"
url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
params = {"regions": "us", "markets": "spreads,totals,h2h", "oddsFormat": "american", "apiKey": API_KEY}
resp = requests.get(url, params=params, timeout=20)
resp.raise_for_status()
data = resp.json()
print(f"Fetched {len(data)} events")
for ev in data:
    ht = ev.get('home_team')
    at = ev.get('away_team')
    teams = ev.get('teams')
    sites = [b.get('key') for b in ev.get('bookmakers', [])]
    print(f"{ht} vs {at}  | teams={teams} | bookmakers={sites} | id={ev.get('id')}")
    # stop early if we see Chicago or Green Bay
    if 'Chicago' in ht or 'Chicago' in at or 'Green' in ht or 'Green' in at:
        break
