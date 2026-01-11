#!/usr/bin/env python3
"""
SQLite DB cleaner: audits and deduplicates tables, removes incomplete rows.

- Audits: row counts, duplicate counts (by table keys), null critical fields
- Cleans: removes duplicates keeping latest row (MAX(rowid)), drops rows with null/empty critical keys
 - Skips log-like tables by default (ensemble_predictions*) unless `--include-logs`

Usage:
  python src/scripts/clean_sqlite_db.py --dry-run
  python src/scripts/clean_sqlite_db.py --apply
  python src/scripts/clean_sqlite_db.py --apply --include-logs
"""
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd

try:
    from utils.paths import DATA_DIR, OUTPUTS_DIR, ensure_dir
except Exception:
    # Fallback: derive paths relative to project root
    ROOT = Path(__file__).resolve().parents[2]
    DATA_DIR = ROOT / 'data'
    OUTPUTS_DIR = ROOT / 'outputs'
    def ensure_dir(p: Path):
        p.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / 'nfl_model.db'

# Table cleanup configuration
TABLES = [
    {
        'table': 'games',
        'keys': ['game_id'],
        'critical': ['game_id', 'away_team', 'home_team', 'season', 'week'],
        'skip': False,
    },
    {
        'table': 'team_games',
        'keys': ['game_id', 'team'],
        'critical': ['game_id', 'team'],
        'skip': False,
    },
    {
        'table': 'odds',
        'keys': ['game_id', 'sportsbook'],
        'critical': ['game_id', 'sportsbook'],
        'skip': False,
    },
    {
        'table': 'team_game_epa',
        'keys': ['game_id', 'team'],
        'critical': ['game_id', 'team'],
        'skip': False,
    },
    {
        'table': 'team_game_snaps',
        'keys': ['game_id', 'team'],
        'critical': ['game_id', 'team'],
        'skip': False,
    },
    {
        'table': 'team_season_splits',
        'keys': ['season', 'team'],
        'critical': ['season', 'team'],
        'skip': False,
    },
    {
        'table': 'pfr_seasons',
        'keys': ['boxscore_stats_link', 'tm_alias', 'opp_alias'],
        'critical': ['boxscore_stats_link'],
        'skip': False,
    },
    {
        'table': 'pfr_metadata',
        'keys': ['boxscore_stats_link'],
        'critical': ['boxscore_stats_link'],
        'skip': False,
    },
    {
        'table': 'pfr_stats',
        'keys': ['boxscore_stats_link', 'alias'],
        'critical': ['boxscore_stats_link'],
        'skip': False,
    },
    # Logs (skip unless explicitly requested)
    {
        'table': 'ensemble_predictions',
        'keys': ['game_id', 'timestamp'],
        'critical': ['game_id', 'timestamp'],
        'skip': True,
    },
    {
        'table': 'ensemble_predictions_detail',
        'keys': ['game_id', 'train_week', 'variant', 'timestamp'],
        'critical': ['game_id', 'train_week', 'variant', 'timestamp'],
        'skip': True,
    },
]


def table_exists(conn, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def audit_table(conn, name: str, keys: list, critical: list) -> dict:
    report = {'table': name, 'rows': 0, 'dups': 0, 'null_critical': 0}
    if not table_exists(conn, name):
        report['missing'] = True
        return report
    df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
    report['rows'] = len(df)
    if not df.empty:
        # Duplicate count by keys
        try:
            dups = df.duplicated(subset=keys, keep='last').sum()
            report['dups'] = int(dups)
        except Exception:
            report['dups'] = None
        # Null critical
        nulls = 0
        for c in critical:
            if c in df.columns:
                nulls += int(df[c].isna().sum())
        report['null_critical'] = nulls
    return report


def dedup_table(conn, name: str, keys: list) -> int:
    if not table_exists(conn, name):
        return 0
    # Delete rows not the latest per group
    # Keep MAX(rowid) per group of keys
    group_cols = ','.join(keys)
    sql = f"""
        DELETE FROM {name}
        WHERE rowid NOT IN (
            SELECT MAX(rowid) FROM {name}
            GROUP BY {group_cols}
        )
    """
    cur = conn.cursor()
    cur.execute(sql)
    return cur.rowcount


def drop_incomplete(conn, name: str, critical: list) -> int:
    if not table_exists(conn, name):
        return 0
    cur = conn.cursor()
    removed = 0
    # Remove rows where any critical column is NULL or empty string
    for c in critical:
        # Skip if column missing
        info = pd.read_sql_query(f"PRAGMA table_info({name})", conn)
        if c not in set(info['name'].tolist()):
            continue
        cur.execute(f"DELETE FROM {name} WHERE {c} IS NULL OR {c} = ''")
        removed += cur.rowcount
    return removed


def save_report(audit_before: list, audit_after: list):
    ensure_dir(OUTPUTS_DIR)
    ts = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    path = OUTPUTS_DIR / f'db_cleanup_report_{ts}.md'
    lines = ["# DB Cleanup Report", f"Timestamp: {ts}", ""]
    lines.append("## Before")
    for r in audit_before:
        lines.append(f"- {r['table']}: rows={r.get('rows')}, dups={r.get('dups')}, null_critical={r.get('null_critical')}")
    lines.append("")
    lines.append("## After")
    for r in audit_after:
        lines.append(f"- {r['table']}: rows={r.get('rows')}, dups={r.get('dups')}, null_critical={r.get('null_critical')}")
    content = "\n".join(lines)
    path.write_text(content, encoding='utf-8')
    print(f"Report written: {path}")
    return path


def main():
    ap = argparse.ArgumentParser(description='Audit and clean SQLite DB (dedup and drop incomplete rows)')
    ap.add_argument('--dry-run', action='store_true', help='Audit only, no changes')
    ap.add_argument('--apply', action='store_true', help='Apply dedup and drop incomplete')
    ap.add_argument('--include-logs', action='store_true', help='Include ensemble logs tables in cleaning')
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return

    # Adjust config based on include-logs flag
    tables = []
    for t in TABLES:
        if t['skip'] and not args.include_logs:
            continue
        tables.append(t)

    with sqlite3.connect(str(DB_PATH)) as conn:
        # Audit before
        audit_before = [audit_table(conn, t['table'], t['keys'], t['critical']) for t in tables]
        print("Audit (before):")
        for r in audit_before:
            print(r)

        if args.apply:
            total_removed = 0
            for t in tables:
                removed_dups = dedup_table(conn, t['table'], t['keys'])
                removed_nulls = drop_incomplete(conn, t['table'], t['critical'])
                total_removed += (removed_dups + removed_nulls)
                print(f"Cleaned {t['table']}: dups_removed={removed_dups}, nulls_removed={removed_nulls}")
            conn.commit()
            print(f"Total rows removed: {total_removed}")

        # Audit after
        audit_after = [audit_table(conn, t['table'], t['keys'], t['critical']) for t in tables]
        print("Audit (after):")
        for r in audit_after:
            print(r)

    # Save report
    save_report(audit_before, audit_after)


if __name__ == '__main__':
    main()
