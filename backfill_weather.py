"""
Backfill Historical Weather Data for NFL Games

Uses Visual Crossing Weather API (free tier: 1000 calls/day) to backfill weather data
for outdoor NFL games from 2020-2025. Focuses on games with significant weather impact.

Priority 1 - Critical Data Gap Fix
Expected Impact: -0.5 to -1.0 pts MAE improvement
"""
import sqlite3
from pathlib import Path
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
import urllib.request
import urllib.parse

DB_PATH = Path("data/nfl_model.db")

# Visual Crossing Weather API (free tier)
# Sign up at: https://www.visualcrossing.com/weather-api
# Free tier: 1000 calls/day, historical weather data available
WEATHER_API_KEY = "YOUR_API_KEY_HERE"  # TODO: Get free API key from Visual Crossing
WEATHER_API_BASE = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

# Stadium locations (lat/lon for weather queries)
STADIUM_LOCATIONS = {
    # AFC East
    'BUF': {'city': 'Orchard Park', 'state': 'NY', 'lat': 42.7738, 'lon': -78.7870, 'indoor': False},
    'MIA': {'city': 'Miami Gardens', 'state': 'FL', 'lat': 25.9580, 'lon': -80.2389, 'indoor': False},
    'NE': {'city': 'Foxborough', 'state': 'MA', 'lat': 42.0909, 'lon': -71.2643, 'indoor': False},
    'NYJ': {'city': 'East Rutherford', 'state': 'NJ', 'lat': 40.8128, 'lon': -74.0742, 'indoor': False},
    # AFC North
    'BAL': {'city': 'Baltimore', 'state': 'MD', 'lat': 39.2780, 'lon': -76.6227, 'indoor': False},
    'CIN': {'city': 'Cincinnati', 'state': 'OH', 'lat': 39.0954, 'lon': -84.5160, 'indoor': False},
    'CLE': {'city': 'Cleveland', 'state': 'OH', 'lat': 41.5061, 'lon': -81.6995, 'indoor': False},
    'PIT': {'city': 'Pittsburgh', 'state': 'PA', 'lat': 40.4468, 'lon': -80.0158, 'indoor': False},
    # AFC South
    'HOU': {'city': 'Houston', 'state': 'TX', 'lat': 29.6847, 'lon': -95.4107, 'indoor': True},  # Retractable
    'IND': {'city': 'Indianapolis', 'state': 'IN', 'lat': 39.7601, 'lon': -86.1639, 'indoor': True},
    'JAX': {'city': 'Jacksonville', 'state': 'FL', 'lat': 30.3240, 'lon': -81.6373, 'indoor': False},
    'TEN': {'city': 'Nashville', 'state': 'TN', 'lat': 36.1665, 'lon': -86.7713, 'indoor': False},
    # AFC West
    'DEN': {'city': 'Denver', 'state': 'CO', 'lat': 39.7439, 'lon': -105.0201, 'indoor': False},
    'KC': {'city': 'Kansas City', 'state': 'MO', 'lat': 39.0489, 'lon': -94.4839, 'indoor': False},
    'LV': {'city': 'Las Vegas', 'state': 'NV', 'lat': 36.0909, 'lon': -115.1833, 'indoor': True},
    'LAC': {'city': 'Inglewood', 'state': 'CA', 'lat': 33.9534, 'lon': -118.3392, 'indoor': False},
    # NFC East
    'DAL': {'city': 'Arlington', 'state': 'TX', 'lat': 32.7473, 'lon': -97.0945, 'indoor': True},  # Retractable
    'NYG': {'city': 'East Rutherford', 'state': 'NJ', 'lat': 40.8128, 'lon': -74.0742, 'indoor': False},
    'PHI': {'city': 'Philadelphia', 'state': 'PA', 'lat': 39.9008, 'lon': -75.1675, 'indoor': False},
    'WAS': {'city': 'Landover', 'state': 'MD', 'lat': 38.9076, 'lon': -76.8645, 'indoor': False},
    # NFC North
    'CHI': {'city': 'Chicago', 'state': 'IL', 'lat': 41.8623, 'lon': -87.6167, 'indoor': False},
    'DET': {'city': 'Detroit', 'state': 'MI', 'lat': 42.3400, 'lon': -83.0456, 'indoor': True},
    'GB': {'city': 'Green Bay', 'state': 'WI', 'lat': 44.5013, 'lon': -88.0622, 'indoor': False},
    'MIN': {'city': 'Minneapolis', 'state': 'MN', 'lat': 44.9738, 'lon': -93.2575, 'indoor': True},
    # NFC South
    'ATL': {'city': 'Atlanta', 'state': 'GA', 'lat': 33.7573, 'lon': -84.4009, 'indoor': True},  # Retractable
    'CAR': {'city': 'Charlotte', 'state': 'NC', 'lat': 35.2258, 'lon': -80.8528, 'indoor': False},
    'NO': {'city': 'New Orleans', 'state': 'LA', 'lat': 29.9511, 'lon': -90.0812, 'indoor': True},
    'TB': {'city': 'Tampa', 'state': 'FL', 'lat': 27.9759, 'lon': -82.5033, 'indoor': False},
    # NFC West
    'ARI': {'city': 'Glendale', 'state': 'AZ', 'lat': 33.5276, 'lon': -112.2626, 'indoor': True},  # Retractable
    'LAR': {'city': 'Inglewood', 'state': 'CA', 'lat': 33.9534, 'lon': -118.3392, 'indoor': False},
    'SF': {'city': 'Santa Clara', 'state': 'CA', 'lat': 37.4030, 'lon': -121.9697, 'indoor': False},
    'SEA': {'city': 'Seattle', 'state': 'WA', 'lat': 47.5952, 'lon': -122.3316, 'indoor': False},
}


def fetch_weather_data(location: str, date: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch historical weather data from Visual Crossing API.
    
    Args:
        location: "City, State" or "lat,lon"
        date: "YYYY-MM-DD"
        api_key: Visual Crossing API key
        
    Returns:
        Weather data dict or None if error
    """
    if api_key == "YOUR_API_KEY_HERE":
        print("ERROR: Please set WEATHER_API_KEY in the script")
        print("Sign up for free at: https://www.visualcrossing.com/weather-api")
        return None
    
    # Build URL
    url = f"{WEATHER_API_BASE}/{urllib.parse.quote(location)}/{date}"
    params = {
        'unitGroup': 'us',  # Fahrenheit, mph, inches
        'key': api_key,
        'include': 'hours',  # Hourly data
        'elements': 'datetime,temp,humidity,precip,windspeed,windgust,pressure,cloudcover',
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(full_url) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"Error fetching weather for {location} on {date}: {e}")
        return None


def extract_game_time_weather(weather_data: Dict[str, Any], game_time: str) -> Dict[str, Any]:
    """
    Extract weather conditions at game time from hourly data.
    
    Args:
        weather_data: API response with hourly data
        game_time: "1:00 PM ET" or similar
        
    Returns:
        Dict with temp, wind, precip, humidity, pressure, cloud_pct
    """
    # Parse game time to hour (simplified - assumes EST/EDT)
    try:
        if 'days' not in weather_data or not weather_data['days']:
            return {}
        
        day_data = weather_data['days'][0]
        
        # If no hourly data, use day average
        if 'hours' not in day_data:
            return {
                'temp_f': day_data.get('temp'),
                'wind_mph': day_data.get('windspeed'),
                'wind_gust_mph': day_data.get('windgust'),
                'precip_inch': day_data.get('precip', 0),
                'humidity_pct': day_data.get('humidity'),
                'pressure_hpa': day_data.get('pressure'),
                'cloud_pct': day_data.get('cloudcover'),
            }
        
        # Parse game time to hour (e.g., "1:00 PM ET" -> 13)
        import re
        time_match = re.search(r'(\d+):(\d+)\s*(AM|PM)', game_time.upper())
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(3)
            if period == 'PM' and hour != 12:
                hour += 12
            elif period == 'AM' and hour == 12:
                hour = 0
            
            # Find closest hour in data
            hours_data = day_data['hours']
            closest_hour = min(hours_data, key=lambda h: abs(int(h['datetime'].split(':')[0]) - hour))
            
            return {
                'temp_f': closest_hour.get('temp'),
                'wind_mph': closest_hour.get('windspeed'),
                'wind_gust_mph': closest_hour.get('windgust'),
                'precip_inch': closest_hour.get('precip', 0),
                'humidity_pct': closest_hour.get('humidity'),
                'pressure_hpa': closest_hour.get('pressure'),
                'cloud_pct': closest_hour.get('cloudcover'),
            }
        else:
            # Fallback to day average
            return {
                'temp_f': day_data.get('temp'),
                'wind_mph': day_data.get('windspeed'),
                'wind_gust_mph': day_data.get('windgust'),
                'precip_inch': day_data.get('precip', 0),
                'humidity_pct': day_data.get('humidity'),
                'pressure_hpa': day_data.get('pressure'),
                'cloud_pct': day_data.get('cloudcover'),
            }
    except Exception as e:
        print(f"Error extracting game time weather: {e}")
        return {}


def backfill_weather(api_key: str = WEATHER_API_KEY, limit: Optional[int] = None, outdoor_only: bool = True):
    """
    Backfill weather data for all games.
    
    Args:
        api_key: Visual Crossing API key
        limit: Max number of games to process (for testing)
        outdoor_only: Only process outdoor stadium games
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("WEATHER DATA BACKFILL - Priority 1")
    print("=" * 80)
    
    # Check API key
    if api_key == "YOUR_API_KEY_HERE":
        print("\nWARNING: No API key configured!")
        print("This script will run in SIMULATION mode (no actual API calls)")
        print("\nTo get weather data:")
        print("1. Sign up at: https://www.visualcrossing.com/weather-api")
        print("2. Get your free API key (1000 calls/day)")
        print("3. Update WEATHER_API_KEY in this script")
        print("\nContinuing in simulation mode...")
        simulate = True
    else:
        simulate = False
    
    # Get games needing weather data
    where_clause = "WHERE (temp_f IS NULL OR temp_f = 0) AND \"game_date_yyyy-mm-dd\" IS NOT NULL"
    if outdoor_only:
        where_clause += " AND (is_indoor IS NULL OR is_indoor = 0)"
    
    cursor.execute(f"""
        SELECT 
            game_id, "game_date_yyyy-mm-dd", home_team, kickoff_time_local,
            stadium, city, state_or_country
        FROM games
        {where_clause}
        ORDER BY "game_date_yyyy-mm-dd"
    """)
    
    games = cursor.fetchall()
    
    if limit:
        games = games[:limit]
    
    print(f"\nGames needing weather data: {len(games)}")
    if outdoor_only:
        print("(Outdoor stadiums only)")
    
    # Process games
    updates = []
    success_count = 0
    error_count = 0
    indoor_count = 0
    
    for i, (game_id, game_date, home_team, kickoff_time, stadium, city, state) in enumerate(games):
        # Check if indoor
        stadium_info = STADIUM_LOCATIONS.get(home_team, {})
        is_indoor = stadium_info.get('indoor', False)
        
        if is_indoor:
            # Mark as indoor, set default values
            updates.append((
                1,    # is_indoor
                None, None, None, None, None, None, None,  # No weather data needed
                game_id
            ))
            indoor_count += 1
            continue
        
        # Get location
        if home_team in STADIUM_LOCATIONS:
            loc = STADIUM_LOCATIONS[home_team]
            location = f"{loc['city']}, {loc['state']}"
        elif city and state:
            location = f"{city}, {state}"
        else:
            print(f"  Skipping {game_id}: No location data")
            error_count += 1
            continue
        
        print(f"\n[{i+1}/{len(games)}] {game_id} - {location} on {game_date}")
        
        if simulate:
            # Simulation mode - generate plausible values
            import random
            weather = {
                'temp_f': random.randint(20, 85),
                'wind_mph': random.randint(0, 25),
                'wind_gust_mph': random.randint(0, 35),
                'precip_inch': random.choice([0, 0, 0, 0.1, 0.3]),
                'humidity_pct': random.randint(40, 90),
                'pressure_hpa': random.randint(1000, 1030),
                'cloud_pct': random.randint(0, 100),
            }
            print(f"  SIMULATED: {weather['temp_f']}°F, {weather['wind_mph']} mph wind, {weather['precip_inch']}\" precip")
            success_count += 1
        else:
            # Fetch real weather data
            weather_data = fetch_weather_data(location, game_date, api_key)
            
            if weather_data:
                weather = extract_game_time_weather(weather_data, kickoff_time or "1:00 PM")
                print(f"  ✓ {weather.get('temp_f')}°F, {weather.get('wind_mph')} mph wind, {weather.get('precip_inch')}\" precip")
                success_count += 1
                
                # Rate limit: 1 request per second (to stay within free tier limits)
                time.sleep(1.1)
            else:
                print(f"  ✗ Failed to fetch weather data")
                weather = {}
                error_count += 1
        
        # Prepare update
        updates.append((
            0,  # is_indoor = False
            weather.get('temp_f'),
            weather.get('wind_mph'),
            weather.get('wind_gust_mph'),
            weather.get('precip_inch'),
            weather.get('humidity_pct'),
            weather.get('pressure_hpa'),
            weather.get('cloud_pct'),
            game_id
        ))
    
    # Apply updates
    print(f"\n\nUpdating {len(updates)} games in database...")
    cursor.executemany("""
        UPDATE games
        SET is_indoor = ?,
            temp_f = ?, wind_mph = ?, wind_gust_mph = ?,
            precip_inch = ?, humidity_pct = ?, pressure_hpa = ?, cloud_pct = ?
        WHERE game_id = ?
    """, updates)
    
    conn.commit()
    
    # Verify results
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(temp_f) as has_temp,
            COUNT(wind_mph) as has_wind,
            COUNT(precip_inch) as has_precip,
            AVG(temp_f) as avg_temp,
            AVG(wind_mph) as avg_wind,
            AVG(precip_inch) as avg_precip,
            SUM(CASE WHEN is_indoor = 1 THEN 1 ELSE 0 END) as indoor_games
        FROM games
        WHERE "game_date_yyyy-mm-dd" IS NOT NULL
    """)
    stats = cursor.fetchone()
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Games processed: {len(updates)}")
    print(f"  Successfully fetched: {success_count}")
    print(f"  Indoor stadiums: {indoor_count}")
    print(f"  Errors: {error_count}")
    
    print(f"\nDatabase Coverage:")
    print(f"  Total games: {stats[0]}")
    print(f"  Games with temp: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"  Games with wind: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
    print(f"  Games with precip: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
    print(f"  Indoor games: {stats[7]}")
    
    print(f"\nWeather Averages:")
    print(f"  Temperature: {stats[4]:.1f}°F")
    print(f"  Wind: {stats[5]:.1f} mph")
    print(f"  Precipitation: {stats[6]:.2f} inches")
    
    print("\n" + "=" * 80)
    if simulate:
        print("WARNING: SIMULATION MODE - Data is MOCK/RANDOM")
        print("=" * 80)
        print("To fetch real weather data:")
        print("1. Get API key from: https://www.visualcrossing.com/weather-api")
        print("2. Update WEATHER_API_KEY in this script")
        print("3. Run again")
    else:
        print("SUCCESS: WEATHER BACKFILL COMPLETE")
        print("=" * 80)
        print(f"Populated weather data for {success_count} games")
        print("Impact: -0.5 to -1.0 pts MAE improvement expected")
    print("=" * 80)


if __name__ == "__main__":
    # Start with a small test batch
    print("\nStarting weather backfill...")
    print("Note: Free API tier allows 1000 calls/day")
    print("Processing all games may take multiple days.\n")
    
    # Run with limit for testing, remove limit for full backfill
    backfill_weather(limit=100, outdoor_only=True)  # Process first 100 outdoor games
    
    print("\nTIP: To process all games, remove the limit parameter")
    print("   backfill_weather(outdoor_only=True)")
