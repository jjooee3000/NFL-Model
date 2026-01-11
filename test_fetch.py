import sys
sys.path.insert(0, 'src')

from utils.upcoming_games import fetch_espn_upcoming, fetch_upcoming_with_source

print("Testing ESPN fetcher...")
games = fetch_espn_upcoming(7)
print(f'ESPN returned {len(games)} games:')
for g in games:
    print(f'  {g["away"]} @ {g["home"]} on {g["date"]}')

print("\n" + "="*60)
print("Testing unified fetcher...")
games, source = fetch_upcoming_with_source(7)
print(f'Source: {source}')
print(f'Games: {len(games)}')
for g in games[:5]:
    print(f'  {g["away"]} @ {g["home"]} on {g.get("date", "TBD")}')
