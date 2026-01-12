import requests
import time

print("Testing live scores endpoint...")
time.sleep(2)  # Wait for server

try:
    r = requests.get('http://127.0.0.1:8083/api/live-scores', timeout=5)
    print(f'Status: {r.status_code}')
    
    data = r.json()
    print(f'Source: {data.get("source")}')
    print(f'Games: {data.get("count")}')
    print()
    
    for g in data.get('games', [])[:4]:
        print(f'{g["short_name"]}:')
        print(f'  Score: {g["away_team"]} {g["away_score"]} @ {g["home_team"]} {g["home_score"]}')
        state_label = "🟢 LIVE" if g["state"] == "in" else "🔵 Final" if g["state"] == "post" else "⚪ Scheduled"
        print(f'  {state_label}: {g.get("clock", g["status_detail"])}')
        if g.get("is_live"):
            print(f'  ⏱️  {g["clock"]}')
        print()
        
except Exception as e:
    print(f'Error: {e}')
