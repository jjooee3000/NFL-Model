"""
Fetch upcoming NFL games (ESPN primary, nfl.com/DB fallback via utils.upcoming_games) and upsert into SQLite.

Usage:
    # Auto (week inferred + days-ahead scan)
    & ".venv/Scripts/python.exe" src/scripts/ingest_upcoming_to_db.py --season 2025 --days-ahead 4

    # Playoffs: force seasontype and week
    & ".venv/Scripts/python.exe" src/scripts/ingest_upcoming_to_db.py --season 2025 --week 19 --seasontype 3

Notes:
    - Writes into data/nfl_model.db `games` table using INSERT OR REPLACE semantics keyed by game_id.
    - Marks games as prediction targets (is_prediction_target=1).
    - Computes game_id as {season}_{week:02d}_{away}_{home}. If week unknown, uses 00.
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.schedule import fetch_upcoming_games, get_current_week, ESPN_TO_WORKBOOK_TEAMS
from utils.upcoming_games import fetch_upcoming_with_source
from utils.stadiums import is_indoor_game

DB_PATH = ROOT / "data" / "nfl_model.db"


def to_workbook_team(abbr: Optional[str]) -> Optional[str]:
    if not abbr:
        return None
    abbr = str(abbr).upper()
    return ESPN_TO_WORKBOOK_TEAMS.get(abbr, abbr)


def build_game_id(season: int, week: Optional[int], away: str, home: str) -> str:
    wk = week if week is not None else 0
    return f"{season}_{int(wk):02d}_{away}_{home}"


def upsert_games(games: List[Dict[str, Any]], season: int, week_override: Optional[int]) -> Dict[str, int]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite DB not found at {DB_PATH}")

    inserted = 0
    updated = 0

    with sqlite3.connect(str(DB_PATH)) as conn:
        for g in games:
            wk = week_override if week_override is not None else g.get("week")
            away = to_workbook_team(g.get("away_team_wb") or g.get("away_team") or g.get("away"))
            home = to_workbook_team(g.get("home_team_wb") or g.get("home_team") or g.get("home"))
            if not away or not home:
                continue
            game_id = build_game_id(season, wk, away, home)

            game_date = g.get("game_date") or g.get("date")
            game_time = g.get("game_time") or g.get("time") or g.get("kickoff_time_local")
            game_datetime = None
            if game_date and game_time:
                try:
                    game_datetime = datetime.strptime(f"{game_date} {game_time}", "%Y-%m-%d %H:%M")
                except Exception:
                    game_datetime = None

            neutral = 1 if g.get("neutral_site") else 0
            indoor_flag = is_indoor_game(home)
            indoor = 1 if indoor_flag else 0 if indoor_flag is False else None

            insert_payload = (
                game_id,
                season,
                wk,
                away,
                home,
                game_date,
                game_time,
                neutral,
                1,  # is_prediction_target
                indoor,
                game_datetime.isoformat() if game_datetime else None,
                None,
                None,
                None,
                None,
            )

            exists = conn.execute("SELECT 1 FROM games WHERE game_id = ? LIMIT 1", (game_id,)).fetchone()
            if exists:
                update_payload = (
                    season,
                    wk,
                    away,
                    home,
                    game_date,
                    game_time,
                    neutral,
                    1,
                    indoor,
                    game_datetime.isoformat() if game_datetime else None,
                    game_id,
                )
                conn.execute(
                    'UPDATE games SET season=?, week=?, away_team=?, home_team=?, "game_date_yyyy-mm-dd"=?, '
                    'kickoff_time_local=?, neutral_site_0_1=?, is_prediction_target=?, is_indoor=?, game_datetime=? '
                    'WHERE game_id=?',
                    update_payload,
                )
                updated += 1
            else:
                conn.execute(
                    'INSERT INTO games (game_id, season, week, away_team, home_team, "game_date_yyyy-mm-dd", '
                    'kickoff_time_local, neutral_site_0_1, is_prediction_target, is_indoor, game_datetime, '
                    'away_score, home_score, point_differential_home, total_points) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    insert_payload,
                )
                inserted += 1
        conn.commit()

    return {"inserted": inserted, "updated": updated}


def main():
    parser = argparse.ArgumentParser(description="Fetch upcoming games and upsert into SQLite")
    parser.add_argument("--season", type=int, default=2025, help="Season year")
    parser.add_argument("--week", type=int, default=None, help="Week to fetch (None = auto current)")
    parser.add_argument("--seasontype", type=int, default=2, help="Season type: 1=pre, 2=reg, 3=playoffs")
    parser.add_argument("--days-ahead", type=int, default=4, help="Also scan scoreboard for N days ahead (handles playoffs/off-calendar)")
    parser.add_argument("--include-completed", action="store_true", help="Include completed games (default: upcoming only)")
    args = parser.parse_args()

    season = args.season
    week = args.week if args.week is not None else get_current_week(season=season)

    # Primary: try ESPN schedule by week
    print(f"Fetching upcoming games: season={season}, week={week}, seasontype={args.seasontype}")
    games = fetch_upcoming_games(season=season, week=week, include_completed=args.include_completed, seasontype=args.seasontype)

    # Fallback: day-based scoreboard scan (handles playoffs when week param may not map)
    if not games:
        print(f"Week-based fetch returned 0; trying day-based scan for next {args.days_ahead} day(s)...")
        games, source = fetch_upcoming_with_source(days_ahead=args.days_ahead)
        print(f"Day-scan source={source}, games={len(games)}")
        # When week unknown from day-scan, favor the fallback-provided week
        if games and args.week is None:
            week = None

    if not games:
        print("No games returned from sources.")
        return

    print(f"Fetched {len(games)} games; writing to DB at {DB_PATH}")
    stats = upsert_games(games, season=season, week_override=week)
    print(f"Done. Inserted: {stats['inserted']}, Updated: {stats['updated']}")


if __name__ == "__main__":
    main()
