#!/usr/bin/env python3
"""
Enforce unique indexes and essential constraints across SQLite tables.

Run safely multiple times (idempotent).
"""
import sqlite3
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / 'data' / 'nfl_model.db'
SRC = ROOT / 'src'
import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

INDEXES = [
    # Core tables
    ("games", "idx_games_game_id", "game_id"),
    ("team_games", "idx_team_games_uniq", "game_id, team"),
    ("odds", "idx_odds_uniq", "game_id, sportsbook"),
    ("team_game_epa", "idx_team_game_epa_uniq", "game_id, team"),
    ("game_scoring_summary", "idx_game_scoring_summary_uniq", "game_id"),
    # Raw PFR tables
    ("pfr_seasons", "idx_pfr_seasons_uniq", "boxscore_stats_link, tm_alias, opp_alias"),
    ("pfr_metadata", "idx_pfr_metadata_uniq", "boxscore_stats_link"),
    ("pfr_stats", "idx_pfr_stats_uniq", "boxscore_stats_link, alias"),
    ("pfr_expected_points", "idx_pfr_expected_points_uniq", "boxscore_stats_link, alias"),
    ("pfr_scoring", "idx_pfr_scoring_uniq", "boxscore_stats_link, qtr, clock, alias"),
    ("pfr_roster", "idx_pfr_roster_uniq", "boxscore_stats_link, alias"),
    ("pfr_snap_counts", "idx_pfr_snap_counts_uniq", "boxscore_stats_link, alias"),
    ("pfr_splits", "idx_pfr_splits_uniq", "season, alias, for_against"),
    ("fte_elo", "idx_fte_elo_uniq", "date, season, team1, team2"),
    # Derived tables
    ("team_game_snaps", "idx_team_game_snaps_uniq", "game_id, team"),
    ("team_season_splits", "idx_team_season_splits_uniq", "team, season"),
    ("game_elo", "idx_game_elo_uniq", "game_id"),
]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def columns_exist(conn: sqlite3.Connection, table: str, cols: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    present = {row[1] for row in cur.fetchall()}
    for c in [c.strip() for c in cols.split(',')]:
        if c not in present:
            return False
    return True


def main():
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return
    from utils.db_dedupe import TABLE_KEYS as RAW_KEYS
    with sqlite3.connect(str(DB_PATH)) as conn:
        for table, idx, cols in INDEXES:
            if not table_exists(conn, table):
                continue
            if not columns_exist(conn, table, cols):
                continue
            try:
                # Pre-dedup rows based on configured keys if available
                keys = RAW_KEYS.get(table, [c.strip() for c in cols.split(',')])
                group_cols = ','.join(keys)
                try:
                    conn.execute(
                        f"DELETE FROM {table} WHERE rowid NOT IN (SELECT MAX(rowid) FROM {table} GROUP BY {group_cols})"
                    )
                except Exception:
                    pass
                conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table} ({cols})")
                print(f"Ensured unique index {idx} on {table} ({cols})")
            except Exception as e:
                print(f"Index create failed for {table}.{idx}: {e}")
        conn.commit()
    print("✅ Migrations complete")


if __name__ == '__main__':
    main()
