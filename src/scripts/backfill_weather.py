"""
Backfill historical weather data for NFL games in the workbook.

Usage:
    python src/scripts/backfill_weather.py [--dry-run] [--limit 10]

Fetches weather data from Open-Meteo API and adds columns to the games sheet.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, ensure_dir  # noqa: E402
from utils.weather import fetch_game_weather  # noqa: E402
from utils.stadiums import NFL_STADIUM_COORDS, is_indoor_game  # noqa: E402


DEFAULT_WORKBOOK = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"


def parse_game_datetime(row: pd.Series) -> datetime:
    """
    Parse game datetime from row data.
    
    Uses 'game_date (YYYY-MM-DD)' and 'kickoff_time_local' columns from workbook.
    If time is missing, defaults to 1:00 PM local (typical Sunday afternoon).
    """
    # Get date from game_date column
    date_col = row.get("game_date (YYYY-MM-DD)")
    if pd.isna(date_col):
        # Fallback to other date columns
        for col in ["date", "game_date"]:
            if col in row and pd.notna(row[col]):
                date_col = row[col]
                break
    
    if pd.isna(date_col):
        raise ValueError(f"No valid date found in row: {row}")
    
    game_date = pd.to_datetime(date_col)
    
    # Try to extract time from kickoff_time_local column
    time_col = row.get("kickoff_time_local")
    
    if pd.notna(time_col):
        # Parse time string (e.g., "13:00" or "1:00 PM")
        try:
            if isinstance(time_col, str):
                # Try parsing as HH:MM
                if ":" in time_col:
                    hour, minute = time_col.split(":")[:2]
                    hour = int(hour)
                    minute = int(minute.split()[0])  # Handle "00 PM" case
                    if "PM" in time_col.upper() and hour < 12:
                        hour += 12
                    elif "AM" in time_col.upper() and hour == 12:
                        hour = 0
                    game_time = pd.Timestamp(year=game_date.year, month=game_date.month,
                                            day=game_date.day, hour=hour, minute=minute)
                else:
                    game_time = pd.to_datetime(f"{game_date.date()} {time_col}")
            else:
                game_time = pd.to_datetime(time_col)
        except Exception:
            # Default to 1 PM if parsing fails
            game_time = game_date.replace(hour=13, minute=0)
    else:
        # Default to 1 PM ET for typical Sunday games
        game_time = game_date.replace(hour=13, minute=0)
    
    return game_time


def backfill_weather(
    workbook_path: Path,
    dry_run: bool = False,
    limit: int = None,
    delay_sec: float = 0.25,
) -> None:
    """
    Backfill weather data for all games in the workbook.
    
    Args:
        workbook_path: Path to Excel workbook.
        dry_run: If True, don't save changes.
        limit: Limit number of games to process (for testing).
        delay_sec: Delay between API calls.
    """
    print(f"\n=== Backfilling Weather Data ===")
    print(f"Workbook: {workbook_path}")
    print(f"Dry run: {dry_run}")
    
    # Load games sheet
    games = pd.read_excel(workbook_path, sheet_name="games")
    print(f"\nLoaded {len(games)} games")
    
    # Check if weather columns already exist
    weather_cols = [
        "temp_f", "humidity_pct", "precip_inch", "wind_mph",
        "wind_gust_mph", "wind_dir_deg", "pressure_hpa", "cloud_pct",
        "is_indoor", "game_datetime"
    ]
    
    new_cols = [col for col in weather_cols if col not in games.columns]
    if new_cols:
        print(f"Adding new columns: {', '.join(new_cols)}")
        for col in new_cols:
            games[col] = None
    
    # Parse game datetimes if not already present
    if "game_datetime" not in games.columns or games["game_datetime"].isna().all():
        print("Parsing game datetimes...")
        games["game_datetime"] = games.apply(parse_game_datetime, axis=1)
    
    # Add indoor flag
    games["is_indoor"] = games["home_team"].apply(is_indoor_game).astype(int)
    
    # Determine which games need weather data
    needs_weather = games["temp_f"].isna()
    games_to_fetch = games[needs_weather].copy()
    
    if limit:
        games_to_fetch = games_to_fetch.head(limit)
    
    print(f"\n{len(games_to_fetch)} games need weather data")
    
    if len(games_to_fetch) == 0:
        print("All games already have weather data. Exiting.")
        return
    
    # Fetch weather for each game
    import time
    success_count = 0
    fail_count = 0
    
    for idx, row in games_to_fetch.iterrows():
        home_team = row["home_team"]
        game_dt = row["game_datetime"]
        
        if home_team not in NFL_STADIUM_COORDS:
            print(f"Warning: No coordinates for '{home_team}', skipping")
            fail_count += 1
            continue
        
        lat, lon = NFL_STADIUM_COORDS[home_team]
        
        try:
            wx = fetch_game_weather(lat, lon, game_dt, window_hours=0)
            
            # Update games DataFrame
            for col, val in wx.items():
                games.at[idx, col] = val
            
            success_count += 1
            print(f"[{success_count}/{len(games_to_fetch)}] {home_team} on {game_dt.date()} - "
                  f"Temp: {wx.get('temp_f'):.1f}°F, Wind: {wx.get('wind_mph'):.1f} mph")
            
        except Exception as e:
            print(f"Failed: {home_team} on {game_dt.date()} - {e}")
            fail_count += 1
        
        time.sleep(delay_sec)  # Rate limiting
    
    print(f"\n=== Summary ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    
    if not dry_run:
        # Save updated workbook
        print(f"\nSaving updated workbook to {workbook_path}")
        
        # Read all sheets
        with pd.ExcelFile(workbook_path) as xls:
            sheet_dict = {sheet: pd.read_excel(xls, sheet) for sheet in xls.sheet_names}
        
        # Update games sheet
        sheet_dict["games"] = games
        
        # Write back
        with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
            for sheet_name, df in sheet_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print("✓ Workbook saved successfully")
    else:
        print("\nDry run - no changes saved")
    
    print("\nSample weather data:")
    print(games[["home_team", "game_datetime", "temp_f", "wind_mph", "precip_inch", "is_indoor"]].head(10))


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill weather data for NFL games")
    parser.add_argument("--workbook", type=str, default=str(DEFAULT_WORKBOOK),
                       help="Path to Excel workbook")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't save changes, just print what would happen")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of games to process (for testing)")
    parser.add_argument("--delay", type=float, default=0.25,
                       help="Delay between API calls in seconds (default: 0.25)")
    args = parser.parse_args()
    
    workbook_path = Path(args.workbook)
    if not workbook_path.exists():
        print(f"Error: Workbook not found at {workbook_path}")
        sys.exit(1)
    
    backfill_weather(workbook_path, args.dry_run, args.limit, args.delay)


if __name__ == "__main__":
    main()
