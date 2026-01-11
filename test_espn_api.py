import requests
from datetime import datetime

today = datetime.utcnow().date()
date_str = today.strftime("%Y%m%d")

# Try different parameter combinations
test_urls = [
    f'https://site.api.espn.com/apis/v2/sports/football/nfl/scoreboard?dates={date_str}',
    f'https://site.api.espn.com/apis/v2/sports/football/nfl/scoreboard?dates={date_str}&seasontype=3',
    f'https://site.api.espn.com/apis/v2/sports/football/nfl/scoreboard',
    f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_str}',
    f'https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_str}',
]

for url in test_urls:
    print(f"\nTesting: {url}")
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        events = data.get('events', [])
        print(f'  Events: {len(events)}')
        if events:
            for e in events[:2]:
                print(f"    {e.get('name', 'unknown')}")
    except Exception as e:
        print(f'  Error: {e}')
