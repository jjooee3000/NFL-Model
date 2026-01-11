import sqlite3
from typing import List, Dict
import pandas as pd

# Configure unique key subsets per table
TABLE_KEYS: Dict[str, List[str]] = {
    'pfr_seasons': ['boxscore_stats_link', 'tm_alias', 'opp_alias'],
    'pfr_metadata': ['boxscore_stats_link'],
    'pfr_stats': ['boxscore_stats_link', 'alias'],
    'pfr_expected_points': ['boxscore_stats_link', 'alias'],
    'pfr_scoring': ['boxscore_stats_link', 'qtr', 'clock', 'alias'],
    'pfr_roster': ['boxscore_stats_link', 'alias'],
    'pfr_snap_counts': ['boxscore_stats_link', 'alias'],
    'pfr_splits': ['season', 'alias', 'for_against'],
    'fte_elo': ['date', 'season', 'team1', 'team2'],
}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def ensure_unique_index(conn: sqlite3.Connection, table: str, keys: List[str]) -> None:
    if not keys:
        return
    # Only include keys that exist in current schema
    cols = [c for c in keys if _column_exists(conn, table, c)]
    if not cols:
        return
    idx_name = f"idx_{table}_uniq"
    try:
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table} ({','.join(cols)})")
    except Exception:
        # Index creation may fail if table is empty or columns missing; ignore
        pass


def insert_ignore(conn: sqlite3.Connection, table: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    cols = list(df.columns)
    placeholders = ','.join(['?'] * len(cols))
    col_list = ','.join(cols)
    data = [tuple(row[c] for c in cols) for _, row in df.iterrows()]
    cur = conn.cursor()
    cur.executemany(f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})", data)
    return cur.rowcount


def to_sql_dedup_append(conn: sqlite3.Connection, df: pd.DataFrame, table: str) -> int:
    if df is None or df.empty:
        return 0
    df = df.replace({pd.NA: None})
    # Drop in-memory duplicates by configured keys
    keys = TABLE_KEYS.get(table, [])
    if keys:
        subset = [k for k in keys if k in df.columns]
        if subset:
            df = df.drop_duplicates(subset=subset, keep='last')
    # Ensure table exists (create schema if missing)
    if not _table_exists(conn, table):
        pd.DataFrame(columns=df.columns).to_sql(table, conn, if_exists='append', index=False)
    # Enforce uniqueness at DB level
    ensure_unique_index(conn, table, keys)
    # Insert with IGNORE to avoid duplicate violations
    return insert_ignore(conn, table, df)
