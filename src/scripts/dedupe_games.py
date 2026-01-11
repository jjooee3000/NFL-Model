"""Deduplicate games by canonical team codes and game_ids.

Dry-run by default. Use --apply to rewrite dependent tables and delete duplicate rows.
Priority rules per matchup/date:
- Keep rows with completed scores over incomplete.
- Prefer rows with a recorded date.
- Prefer rows whose game_id already matches the canonical form.
"""
import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
import sys
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.team_codes import canonical_team, canonical_game_id, normalize_matchup_key

DB_PATH = ROOT / "data" / "nfl_model.db"

GAME_ID_ONLY_TABLES = [
    "team_games",
    "odds",
    "team_game_epa",
    "game_scoring_summary",
    "team_game_snaps",
    "game_elo",
]
TABLES_WITH_TEAMS = [
    "ensemble_predictions",
    "ensemble_predictions_detail",
]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def load_games(conn: sqlite3.Connection, season: int = None) -> List[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    if season:
        return conn.execute(
            "SELECT game_id, season, week, away_team, home_team, away_score, home_score, \"game_date_yyyy-mm-dd\" FROM games WHERE season = ?",
            (season,),
        ).fetchall()
    return conn.execute(
        "SELECT game_id, season, week, away_team, home_team, away_score, home_score, \"game_date_yyyy-mm-dd\" FROM games",
    ).fetchall()


def choose_primary(rows: List[Dict]) -> Dict:
    def priority(r: Dict):
        complete = 1 if (r.get("home_score") is not None and r.get("away_score") is not None) else 0
        has_date = 1 if r.get("game_date_yyyy-mm-dd") else 0
        id_match = 1 if r.get("game_id") == r.get("canonical_id") else 0
        return (complete, has_date, id_match)

    return sorted(rows, key=priority, reverse=True)[0]


def build_buckets(rows: List[sqlite3.Row]) -> Dict[Tuple[str, str, str], List[Dict]]:
    buckets: Dict[Tuple[str, str, str], List[Dict]] = {}
    for r in rows:
        row = dict(r)
        away = canonical_team(row.get("away_team"))
        home = canonical_team(row.get("home_team"))
        row["away_team"] = away
        row["home_team"] = home
        try:
            wk = int(row.get("week") or 0)
        except Exception:
            wk = 0
        row["canonical_id"] = canonical_game_id(int(row.get("season")), wk, away, home)
        key = normalize_matchup_key(row.get("game_date_yyyy-mm-dd"), away, home)
        buckets.setdefault(key, []).append(row)
    return buckets


def plan_dedupe(buckets: Dict[Tuple[str, str, str], List[Dict]]):
    plans = []
    for key, rows in buckets.items():
        if len(rows) == 1 and all(r.get("game_id") == r.get("canonical_id") for r in rows):
            continue
        primary = choose_primary(rows)
        target_id = primary.get("canonical_id")
        aliases = [r for r in rows if r.get("game_id") != target_id]
        plans.append({
            "key": key,
            "primary": primary,
            "target_id": target_id,
            "alias_rows": aliases,
        })
    return plans


def apply_plan(conn: sqlite3.Connection, plans, apply: bool = False) -> None:
    updated = 0
    removed = 0
    remapped = 0

    for plan in plans:
        primary = plan["primary"]
        target_id = plan["target_id"]
        away = primary["away_team"]
        home = primary["home_team"]
        current_id = primary.get("game_id")

        # Ensure primary row carries canonical values
        if current_id != target_id or primary.get("away_team") != away or primary.get("home_team") != home:
            if apply and table_exists(conn, "games"):
                conn.execute(
                    "UPDATE games SET game_id = ?, away_team = ?, home_team = ? WHERE game_id = ?",
                    (target_id, away, home, current_id),
                )
            updated += 1
            if current_id != target_id:
                # Treat the old id as an alias that needs remapping
                plan["alias_rows"].append({"game_id": current_id})

        # Remap dependents for alias rows
        for alias in plan["alias_rows"]:
            alias_id = alias.get("game_id")
            if not alias_id or alias_id == target_id:
                continue
            if apply:
                for tbl in GAME_ID_ONLY_TABLES:
                    if table_exists(conn, tbl):
                        try:
                            conn.execute(f"UPDATE {tbl} SET game_id = ? WHERE game_id = ?", (target_id, alias_id))
                        except sqlite3.IntegrityError:
                            conn.execute(f"DELETE FROM {tbl} WHERE game_id = ?", (alias_id,))
                for tbl in TABLES_WITH_TEAMS:
                    if table_exists(conn, tbl):
                        try:
                            conn.execute(
                                f"UPDATE {tbl} SET game_id = ?, away_team = ?, home_team = ? WHERE game_id = ?",
                                (target_id, away, home, alias_id),
                            )
                        except sqlite3.IntegrityError:
                            conn.execute(f"DELETE FROM {tbl} WHERE game_id = ?", (alias_id,))
                if table_exists(conn, "games"):
                    conn.execute("DELETE FROM games WHERE game_id = ?", (alias_id,))
            remapped += 1
            removed += 1
    if apply:
        conn.commit()

    print(f"Planned primary rows: {len(plans)}")
    print(f"Would update canonical rows: {updated}")
    print(f"Would remap dependent rows: {remapped}")
    print(f"Would delete duplicate games: {removed}")


def main():
    parser = argparse.ArgumentParser(description="Deduplicate games and dependent tables using canonical team codes")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--season", type=int, default=None, help="Optional season filter")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        return

    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = load_games(conn, season=args.season)
        buckets = build_buckets(rows)
        plans = plan_dedupe(buckets)
        if not plans:
            print("No duplicates or alias game_ids detected.")
            return
        apply_plan(conn, plans, apply=args.apply)
        if not args.apply:
            print("Dry-run complete. Re-run with --apply to persist changes.")
        else:
            print("Deduplication applied.")


if __name__ == "__main__":
    main()