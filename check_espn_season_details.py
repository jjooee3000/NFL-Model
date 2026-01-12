"""
Check ESPN API season/week details for current games
"""
import requests
import json

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
response = requests.get(url, timeout=10)
data = response.json()

print('=== ESPN API Season/Week Details ===\n')

for event in data.get('events', []):
    name = event.get('shortName', '')
    
    # Season info
    season = event.get('season', {})
    season_year = season.get('year', 'N/A')
    season_type = season.get('type', 0)
    season_display = season.get('displayName', 'N/A')
    
    # Week info
    week_info = event.get('week', {})
    week_num = week_info.get('number', 'N/A')
    
    # Competition info
    comp = event.get('competitions', [{}])[0]
    comp_type = comp.get('type', {}).get('abbreviation', 'N/A')
    
    # Date
    game_date = event.get('date', '')
    
    print(f'{name}:')
    print(f'  Date: {game_date}')
    print(f'  Season Year: {season_year}')
    print(f'  Season Type: {season_type} (1=Pre, 2=Reg, 3=Post, 4=Off)')
    print(f'  Season Display: {season_display}')
    print(f'  Week Number: {week_num}')
    print(f'  Competition Type: {comp_type}')
    
    # Extract full week details
    print(f'  Full Week Data: {json.dumps(week_info, indent=4)}')
    print()
