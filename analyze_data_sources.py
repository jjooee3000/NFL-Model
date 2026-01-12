"""Analyze available data sources and identify enrichment opportunities"""
import sqlite3
import requests
import json
from pprint import pprint

print("="*80)
print("DATA SOURCE ANALYSIS FOR MODEL ENRICHMENT")
print("="*80)

# 1. Check current database schema
print("\n1. CURRENT DATABASE SCHEMA (games table)")
print("-"*80)
conn = sqlite3.connect('data/nfl_model.db')
cursor = conn.execute('PRAGMA table_info(games)')
db_columns = []
for row in cursor:
    col_name = row[1]
    col_type = row[2]
    db_columns.append(col_name)
    print(f"  {col_name}: {col_type}")

print(f"\n  Total columns: {len(db_columns)}")

# 2. Fetch ESPN API data to see what's available
print("\n2. ESPN API - AVAILABLE DATA FIELDS")
print("-"*80)
try:
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if 'events' in data and len(data['events']) > 0:
        event = data['events'][0]  # Look at first game
        
        print("\n  Top-level event fields:")
        for key in event.keys():
            print(f"    - {key}")
        
        print("\n  Competition data:")
        comp = event['competitions'][0]
        for key in comp.keys():
            print(f"    - {key}")
        
        print("\n  Team data (per team):")
        team = comp['competitors'][0]
        for key in team.keys():
            print(f"    - {key}")
        
        # Check for statistics
        if 'statistics' in comp:
            print("\n  Game statistics available:")
            for stat in comp['statistics']:
                print(f"    - {stat.get('name', 'unknown')}")
        
        # Check for odds/betting data
        if 'odds' in comp:
            print("\n  Betting/Odds data available:")
            for odd in comp.get('odds', []):
                print(f"    - Provider: {odd.get('provider', {}).get('name', 'unknown')}")
                if 'details' in odd:
                    print(f"      Details: {odd['details']}")
                if 'overUnder' in odd:
                    print(f"      Over/Under: {odd['overUnder']}")
                if 'spread' in odd:
                    print(f"      Spread: {odd['spread']}")
        
        # Check for weather
        if 'weather' in comp:
            print("\n  Weather data:")
            weather = comp['weather']
            for key in weather.keys():
                print(f"    - {key}: {weather[key]}")
        
        # Check for venue details
        if 'venue' in comp:
            print("\n  Venue data:")
            venue = comp['venue']
            for key in venue.keys():
                if key != 'address':
                    print(f"    - {key}: {venue.get(key)}")
        
        # Check for situation/play-by-play
        if 'situation' in comp:
            print("\n  Live situation data:")
            situation = comp['situation']
            for key in situation.keys():
                print(f"    - {key}")
        
        # Save sample to file for detailed inspection
        print("\n  Saving full sample game data to espn_sample.json...")
        with open('espn_sample.json', 'w') as f:
            json.dump(event, f, indent=2)
        print("  ✓ Saved")
        
except Exception as e:
    print(f"  Error fetching ESPN data: {e}")

# 3. Check what we're currently NOT capturing
print("\n3. MISSING DATA OPPORTUNITIES")
print("-"*80)

missing_opportunities = []

# Fields we should check for
potential_fields = [
    'attendance', 'weather_temp', 'weather_condition', 'weather_wind_speed',
    'odds_spread', 'odds_total', 'odds_moneyline', 
    'venue_capacity', 'venue_grass', 'venue_indoor',
    'broadcast_network', 'referee', 
    'team_record', 'team_ranking', 'team_division_rank',
    'injuries_count', 'starters_out',
    'time_of_possession', 'turnovers', 'penalties',
    'third_down_pct', 'fourth_down_pct',
    'red_zone_efficiency', 'sacks', 'qb_hits'
]

for field in potential_fields:
    if field not in db_columns:
        missing_opportunities.append(field)

print(f"\n  Potentially valuable fields NOT in database ({len(missing_opportunities)}):")
for field in missing_opportunities:
    print(f"    - {field}")

# 4. Check PFR data availability
print("\n4. PRO FOOTBALL REFERENCE (PFR) DATA")
print("-"*80)
import os
pfr_dir = 'data/pfr_historical'
if os.path.exists(pfr_dir):
    pfr_files = [f for f in os.listdir(pfr_dir) if f.endswith('.csv')]
    print(f"\n  Available PFR files: {len(pfr_files)}")
    
    # Categorize by type
    categories = {}
    for f in pfr_files:
        if 'advanced' in f:
            cat = 'Advanced Stats'
        elif 'situational' in f:
            cat = 'Situational Stats'
        elif 'defense' in f:
            cat = 'Defense'
        elif 'games' in f:
            cat = 'Games/Schedule'
        else:
            cat = 'Other'
        
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)
    
    for cat, files in categories.items():
        print(f"\n  {cat}: {len(files)} files")
        for f in files[:3]:  # Show first 3
            print(f"    - {f}")
        if len(files) > 3:
            print(f"    ... and {len(files)-3} more")

# 5. Recommendations
print("\n5. ENRICHMENT RECOMMENDATIONS")
print("-"*80)
print("""
Priority 1 - Immediately Available from ESPN API:
  ✓ Weather data (temp, conditions, wind) - AVAILABLE NOW
  ✓ Betting lines (spread, total, moneyline) - AVAILABLE NOW  
  ✓ Venue details (capacity, surface type, indoor/outdoor) - AVAILABLE NOW
  ✓ Broadcast network - AVAILABLE NOW
  
Priority 2 - Available from PFR Data:
  ✓ Advanced team statistics (3rd down %, red zone %, time of possession)
  ✓ Drive efficiency metrics
  ✓ Turnover margins
  ✓ Penalty statistics
  
Priority 3 - Requires Additional Sources:
  • Injury reports (may need NFL.com or other API)
  • Referee assignments and historical bias
  • Team rest days / travel distance
  • Strength of schedule metrics

Next Steps:
  1. Add weather columns to games table
  2. Add betting lines columns (spread, total, moneyline)
  3. Add venue characteristics (indoor, surface_type, capacity)
  4. Create feature engineering pipeline for PFR advanced stats
  5. Build injury tracking system
""")

conn.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE - See espn_sample.json for full API response")
print("="*80)
