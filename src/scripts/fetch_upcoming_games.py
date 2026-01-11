"""
Fetch upcoming NFL games from ESPN and populate the workbook.

This script:
1. Fetches upcoming games from ESPN API
2. Adds them to the games sheet in the workbook
3. Backfills weather data for new games
4. Marks games as prediction targets

Usage:
    python src/scripts/fetch_upcoming_games.py --week 19
    python src/scripts/fetch_upcoming_games.py --week 19 --season 2025
    python src/scripts/fetch_upcoming_games.py --auto  # Auto-detect current week
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pandas as pd
from datetime import datetime
from utils.schedule import fetch_upcoming_games, get_current_week
from utils.weather import fetch_game_weather
from utils.stadiums import get_stadium_coords, is_indoor_game


def main():
    parser = argparse.ArgumentParser(description="Fetch upcoming games and add to workbook")
    parser.add_argument("--week", type=int, help="Week number to fetch (1-18)")
    parser.add_argument("--season", type=int, default=2025, help="Season year (default: 2025)")
    parser.add_argument("--auto", action="store_true", help="Auto-fetch current/upcoming games")
    parser.add_argument("--workbook", type=str, 
                       default="data/nfl_2025_model_data_with_moneylines.xlsx",
                       help="Path to workbook")
    parser.add_argument("--dry-run", action="store_true", help="Don't save, just preview")
    args = parser.parse_args()
    
    # Determine how to fetch
    if args.auto:
        week = None  # Fetch current scoreboard
        print(f"Fetching current/upcoming games...")
    elif args.week:
        week = args.week
        print(f"Fetching Week {week} games from ESPN...")
    else:
        print("Error: Must specify --week or --auto")
        sys.exit(1)
    
    # Fetch upcoming games
    upcoming = fetch_upcoming_games(season=args.season, week=week, include_completed=False)
    
    if not upcoming:
        print(f"No upcoming games found.")
        return
    
    print(f"Found {len(upcoming)} upcoming game(s):\n")
    for g in upcoming:
        print(f"  Week {g['week']}: {g['away_team_wb']} @ {g['home_team_wb']}")
        print(f"    Date: {g['game_date']} {g['game_time']}")
        print(f"    Venue: {g['venue']}")
        print()
    
    # Load workbook
    workbook_path = Path(args.workbook)
    if not workbook_path.exists():
        print(f"Error: Workbook not found at {workbook_path}")
        sys.exit(1)
    
    print(f"Loading workbook: {workbook_path}")
    games_df = pd.read_excel(workbook_path, sheet_name="games")
    
    # Check if is_prediction_target column exists
    if "is_prediction_target" not in games_df.columns:
        games_df["is_prediction_target"] = 0
    
    # Generate game IDs and prepare rows
    new_rows = []
    
    for game in upcoming:
        week = game["week"]  # Get week from game data
        # Generate game_id: {season}_{week}_{away}_{home}
        game_id = f"{args.season}_{week:02d}_{game['away_team_wb']}_{game['home_team_wb']}"
        
        # Check if game already exists
        if game_id in games_df["game_id"].values:
            print(f"  ⏭️  Skipping {game_id} (already in workbook)")
            continue
        
        # Parse game datetime for weather
        game_datetime = None
        if game["game_date"] and game["game_time"]:
            try:
                game_datetime = datetime.strptime(
                    f"{game['game_date']} {game['game_time']}", 
                    "%Y-%m-%d %H:%M"
                )
            except ValueError:
                pass
        
        # Get stadium coordinates for weather
        home_team_code = game["home_team_wb"]
        coords = get_stadium_coords(home_team_code)
        indoor = is_indoor_game(home_team_code)
        
        # Fetch weather if outdoor and we have coordinates
        weather_data = {}
        if coords and not indoor and game_datetime:
            print(f"  🌤️  Fetching weather for {game_id}...")
            try:
                weather = fetch_game_weather(coords[0], coords[1], game_datetime, window_hours=3)
                if weather:
                    weather_data = {
                        "temp_f": weather.get("temperature_f"),
                        "humidity_pct": weather.get("relative_humidity"),
                        "precip_inch": weather.get("precipitation_inch"),
                        "wind_mph": weather.get("wind_speed_mph"),
                        "wind_gust_mph": weather.get("wind_gusts_mph"),
                        "wind_dir_deg": weather.get("wind_direction_deg"),
                        "pressure_hpa": weather.get("pressure_hpa"),
                        "cloud_pct": weather.get("cloud_cover_pct"),
                    }
            except Exception as e:
                print(f"    Warning: Weather fetch failed: {e}")
        
        # Build new row
        new_row = {
            "game_id": game_id,
            "season": args.season,
            "week": week,
            "game_date (YYYY-MM-DD)": game["game_date"],
            "kickoff_time_local": game["game_time"],
            "home_team": home_team_code,
            "away_team": game["away_team_wb"],
            "home_score": None,
            "away_score": None,
            "point_differential_home": None,
            "total_points": None,
            "neutral_site (0/1)": 1 if game["neutral_site"] else 0,
            "is_prediction_target": 1,
            "is_indoor": 1 if indoor else 0,
            "game_datetime": game_datetime,
            **weather_data
        }
        
        new_rows.append(new_row)
        print(f"  ✅ Added {game_id}")
    
    if not new_rows:
        print("\nNo new games to add.")
        return
    
    # Append new rows
    new_df = pd.DataFrame(new_rows)
    updated_df = pd.concat([games_df, new_df], ignore_index=True)
    
    print(f"\n📊 Summary:")
    print(f"  Original games: {len(games_df)}")
    print(f"  New games: {len(new_rows)}")
    print(f"  Total games: {len(updated_df)}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No changes saved.")
        print("\nNew rows preview:")
        print(new_df[["game_id", "week", "away_team", "home_team", "game_date (YYYY-MM-DD)", 
                      "is_prediction_target"]].to_string(index=False))
    else:
        # Save back to workbook
        print(f"\n💾 Saving to {workbook_path}...")
        with pd.ExcelWriter(workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            updated_df.to_excel(writer, sheet_name="games", index=False)
        
        print("✅ Workbook updated successfully!")
        print("\nNext steps:")
        print(f"  1. Review games added to workbook")
        print(f"  2. Run predictions: python src/scripts/predict_upcoming.py --week <WEEK> --train-through <WEEK-1>")
        print(f"  3. Check outputs/prediction_log.csv for results")


if __name__ == "__main__":
    main()
