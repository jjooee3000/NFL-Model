"""
Fetch Pro Football Reference data using nflscraPy and store in SQLite.

Datasets:
- Seasons (gamelogs overview)
- Metadata (weather, odds, stadium info)
- Statistics (boxscore totals)
- Expected Points
- Scoring events
- Roster
- Snap counts
- Season splits
- FiveThirtyEight Elo (CSV)

Writes tables into data/nfl_model.db:
- pfr_seasons
- pfr_metadata
- pfr_stats
- pfr_expected_points
- pfr_scoring
- pfr_roster
- pfr_snap_counts
- pfr_splits
- fte_elo

Usage:
  python src/scripts/fetch_pfr_nflscrapy.py --season 2025 --since 2020 --tables stats metadata --limit 50
  python src/scripts/fetch_pfr_nflscrapy.py --season 2025 --tables stats metadata scoring roster splits expected_points snap_counts fte

Notes:
- nflscraPy enforces polite request sleeps (3.5-5.5s) per request.
- For large backfills, prefer narrow table selection or run overnight.
"""
import sys
from pathlib import Path
import argparse
import sqlite3
import pandas as pd
from typing import Optional, List

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
DATA = ROOT / "data"
DB_PATH = DATA / "nfl_model.db"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.paths import ensure_dir, DATA_DIR
from utils.db_dedupe import to_sql_dedup_append
from utils.db_logging import log_event

# Import nflscraPy package functions
import nflscraPy


def to_sql_append(df: pd.DataFrame, table: str) -> None:
    if df is None or df.empty:
        print(f"  ⚠️  No rows to write for {table}")
        return
    ensure_dir(DATA_DIR)
    with sqlite3.connect(str(DB_PATH)) as conn:
        written = to_sql_dedup_append(conn, df, table)
        try:
            log_event(conn, pipeline='fetch_pfr_nflscrapy', table=table, action='append_dedup', rows=written)
        except Exception:
            pass
    print(f"  ✅ Wrote {written} rows to {table} (dedup-aware)")


def fetch_seasons(season: int) -> pd.DataFrame:
    print(f"Fetching season gamelogs for {season}...")
    df = nflscraPy._gamelogs(season)
    return df


def fetch_all_tables_for_season(season: int, tables: List[str], limit: Optional[int] = None) -> None:
    # Get gamelogs to iterate boxscore_stats_link
    season_df = fetch_seasons(season)
    to_sql_append(season_df, "pfr_seasons")

    links = list(season_df.get("boxscore_stats_link", []))
    if limit:
        links = links[:limit]
    print(f"Processing {len(links)} gamelogs for season {season}...")

    for href in links:
        if not isinstance(href, str) or not href.startswith("http"):
            continue
        print("-"*80)
        print(f"Game: {href}")

        if "metadata" in tables:
            try:
                md = nflscraPy._gamelog_metadata(href)
                to_sql_append(md, "pfr_metadata")
            except Exception as e:
                print(f"  Metadata error: {e}")

        if "stats" in tables:
            try:
                st = nflscraPy._gamelog_statistics(href)
                to_sql_append(st, "pfr_stats")
            except Exception as e:
                print(f"  Stats error: {e}")

        if "expected_points" in tables:
            try:
                ep = nflscraPy._gamelog_expected_points(href)
                to_sql_append(ep, "pfr_expected_points")
            except Exception as e:
                print(f"  Expected points error: {e}")

        if "scoring" in tables:
            try:
                sc = nflscraPy._gamelog_scoring(href)
                to_sql_append(sc, "pfr_scoring")
            except Exception as e:
                print(f"  Scoring error: {e}")

        if "roster" in tables:
            try:
                ro = nflscraPy._gamelog_roster(href)
                to_sql_append(ro, "pfr_roster")
            except Exception as e:
                print(f"  Roster error: {e}")

        if "snap_counts" in tables:
            try:
                sn = nflscraPy._gamelog_snap_counts(href)
                to_sql_append(sn, "pfr_snap_counts")
            except Exception as e:
                print(f"  Snap counts error: {e}")

    if "splits" in tables:
        # Splits require team alias and For/Against; sample across teams
        print(f"Fetching season splits for {season} across teams (For/Against)...")
        # Use team aliases from nflscraPy teams map
        tms = nflscraPy._tms()
        aliases = sorted({v.get("alias") for v in tms.values() if v.get("alias")})
        # Limit volume for initial run
        aliases = aliases[:32]
        rows = []
        for alias in aliases:
            for side in ["For", "Against"]:
                try:
                    sp = nflscraPy._season_splits(season, alias.lower(), side)
                    rows.append(sp)
                except Exception as e:
                    print(f"  Splits error ({alias} {side}): {e}")
        if rows:
            to_sql_append(pd.concat(rows, ignore_index=True), "pfr_splits")

    if "fte" in tables:
        print("Fetching FiveThirtyEight Elo dataset...")
        try:
            elo = nflscraPy._five_thirty_eight()
            to_sql_append(elo, "fte_elo")
        except Exception as e:
            print(f"  FTE error: {e}")
            print("  Falling back to direct CSV fetch from FiveThirtyEight...")
            try:
                # Prefer full historical Elo dataset
                url = "https://projects.fivethirtyeight.com/nfl-api/nfl_elo.csv"
                elo = pd.read_csv(url, encoding="utf-8", on_bad_lines="skip")
                # Normalize a subset of columns to expected names if present
                rename_map = {
                    'date': 'date',
                    'season': 'season',
                    'team1': 'team1',
                    'team2': 'team2',
                    'elo1_pre': 'elo1_pre',
                    'elo2_pre': 'elo2_pre',
                    'qbelo1_pre': 'qbelo1_pre',
                    'qbelo2_pre': 'qbelo2_pre',
                    'prob1': 'prob1'
                }
                elo = elo.rename(columns=rename_map)
                to_sql_append(elo, "fte_elo")
            except Exception as e2:
                print(f"  FTE fallback error: {e2}")


def main():
    ap = argparse.ArgumentParser(description="Backfill PFR data via nflscraPy into SQLite")
    ap.add_argument("--season", type=int, default=2025, help="Season year to backfill (default: 2025)")
    ap.add_argument("--since", type=int, help="Backfill starting season (e.g., 2020)")
    ap.add_argument("--tables", nargs="+", default=["metadata", "stats"],
                    choices=["seasons","metadata","stats","expected_points","scoring","roster","snap_counts","splits","fte"],
                    help="Tables to fetch")
    ap.add_argument("--limit", type=int, help="Limit number of gamelogs processed per season")
    args = ap.parse_args()

    ensure_dir(DATA_DIR)

    seasons = [args.season]
    if args.since and args.since < args.season:
        seasons = list(range(args.since, args.season + 1))

    for szn in seasons:
        # Include seasons table if requested
        if "seasons" in args.tables:
            try:
                to_sql_append(fetch_seasons(szn), "pfr_seasons")
            except Exception as e:
                print(f"Seasons fetch error: {e}")
        fetch_all_tables_for_season(szn, args.tables, limit=args.limit)

    print(f"\nDone. Data written to {DB_PATH}")


if __name__ == "__main__":
    main()
