"""
Open-Meteo Historical Weather API client for NFL game weather data.

Fetches hourly weather observations at kickoff time for stadium locations.
Free for non-commercial use, no API key required.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

import pandas as pd


BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    hourly_vars: Optional[List[str]] = None,
) -> Dict:
    """
    Fetch historical weather data from Open-Meteo API.

    Args:
        latitude: Location latitude (WGS84).
        longitude: Location longitude (WGS84).
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        hourly_vars: List of hourly weather variables to fetch.

    Returns:
        Dict with 'hourly' data and metadata.
    """
    if requests is None:
        raise RuntimeError("requests library not installed. Run: pip install requests")

    if hourly_vars is None:
        hourly_vars = [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_gusts_10m",
            "wind_direction_10m",
            "pressure_msl",
            "cloud_cover",
        ]

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly_vars),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York",  # Will auto-adjust to local TZ if needed
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Weather API request failed: {e}")


def extract_weather_at_time(
    weather_data: Dict,
    target_datetime: datetime,
) -> Dict[str, float]:
    """
    Extract weather values at a specific datetime from hourly data.

    Args:
        weather_data: Response dict from fetch_weather().
        target_datetime: Target datetime (will match to nearest hour).

    Returns:
        Dict of weather variables at target time.
    """
    if "hourly" not in weather_data:
        return {}

    hourly = weather_data["hourly"]
    times = hourly.get("time", [])

    # Convert target to ISO string (hour precision)
    target_str = target_datetime.strftime("%Y-%m-%dT%H:00")

    # Find matching time index
    try:
        idx = times.index(target_str)
    except ValueError:
        # If exact match not found, try nearest hour
        target_ts = target_datetime.timestamp()
        time_diffs = [
            abs(datetime.fromisoformat(t).timestamp() - target_ts) for t in times
        ]
        idx = time_diffs.index(min(time_diffs))

    # Extract all variables at that index
    result = {}
    for key, values in hourly.items():
        if key == "time":
            continue
        result[key] = values[idx] if idx < len(values) else None

    return result


def fetch_game_weather(
    latitude: float,
    longitude: float,
    game_datetime: datetime,
    window_hours: int = 0,
) -> Dict[str, float]:
    """
    Fetch weather data for a single game at kickoff time.

    Args:
        latitude: Stadium latitude.
        longitude: Stadium longitude.
        game_datetime: Game kickoff datetime (aware or naive).
        window_hours: Hours before/after to average (0 = exact time).

    Returns:
        Dict with weather variables (temp_f, wind_mph, etc.).
    """
    # Query single day
    game_date = game_datetime.date()
    start_date = (game_date - timedelta(days=1)).isoformat()
    end_date = (game_date + timedelta(days=1)).isoformat()

    weather_data = fetch_weather(latitude, longitude, start_date, end_date)

    if window_hours == 0:
        # Exact time
        wx = extract_weather_at_time(weather_data, game_datetime)
    else:
        # Average over window
        wx_values = []
        for offset in range(-window_hours, window_hours + 1):
            dt = game_datetime + timedelta(hours=offset)
            wx_values.append(extract_weather_at_time(weather_data, dt))

        # Average numeric values
        wx = {}
        for key in wx_values[0].keys():
            vals = [w.get(key) for w in wx_values if w.get(key) is not None]
            wx[key] = sum(vals) / len(vals) if vals else None

    # Rename to cleaner column names
    return {
        "temp_f": wx.get("temperature_2m"),
        "humidity_pct": wx.get("relative_humidity_2m"),
        "precip_inch": wx.get("precipitation"),
        "wind_mph": wx.get("wind_speed_10m"),
        "wind_gust_mph": wx.get("wind_gusts_10m"),
        "wind_dir_deg": wx.get("wind_direction_10m"),
        "pressure_hpa": wx.get("pressure_msl"),
        "cloud_pct": wx.get("cloud_cover"),
    }


def backfill_weather_for_games(
    games_df: pd.DataFrame,
    stadium_coords: Dict[str, tuple],
    datetime_col: str = "game_datetime",
    home_team_col: str = "home_team",
    delay_sec: float = 0.2,
) -> pd.DataFrame:
    """
    Backfill weather data for all games in a DataFrame.

    Args:
        games_df: DataFrame with game records.
        stadium_coords: Dict mapping team name -> (lat, lon).
        datetime_col: Column name for game datetime.
        home_team_col: Column name for home team.
        delay_sec: Delay between API calls (rate limiting).

    Returns:
        DataFrame with weather columns added.
    """
    result = games_df.copy()

    # Initialize weather columns
    weather_cols = [
        "temp_f",
        "humidity_pct",
        "precip_inch",
        "wind_mph",
        "wind_gust_mph",
        "wind_dir_deg",
        "pressure_hpa",
        "cloud_pct",
    ]
    for col in weather_cols:
        result[col] = None

    for idx, row in result.iterrows():
        home_team = row[home_team_col]
        if home_team not in stadium_coords:
            print(f"Warning: No coordinates for {home_team}, skipping weather fetch")
            continue

        lat, lon = stadium_coords[home_team]
        game_dt = pd.to_datetime(row[datetime_col])

        try:
            wx = fetch_game_weather(lat, lon, game_dt)
            for col in weather_cols:
                result.at[idx, col] = wx.get(col)
            print(f"Fetched weather for {home_team} on {game_dt.date()}")
        except Exception as e:
            print(f"Failed to fetch weather for {home_team} on {game_dt.date()}: {e}")

        time.sleep(delay_sec)  # Rate limiting

    return result
