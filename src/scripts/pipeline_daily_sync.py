#!/usr/bin/env python3
"""
Daily sync pipeline:
1) Postgame score sync
2) Optional fetch and map (if nflscraPy available)
3) Clean DB (apply, include logs)
4) Write summary report
"""
import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / 'data' / 'nfl_model.db'
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def safe_import_update_scores():
    try:
        from src.scripts.update_postgame_scores import update_scores
        return update_scores
    except Exception:
        try:
            import sys
            SRC = ROOT / 'src'
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))
            from scripts.update_postgame_scores import update_scores
            return update_scores
        except Exception:
            return None


def run_cleaner(include_logs: bool = True):
    from .clean_sqlite_db import main as clean_main  # type: ignore
    import sys
    args = ['--apply'] + (['--include-logs'] if include_logs else [])
    sys.argv = ['clean_sqlite_db.py'] + args
    clean_main()


def log_pipeline_event(table: str, action: str, rows: int, status: str = 'ok', details: str = ''):
    from utils.db_logging import log_event
    with sqlite3.connect(str(DB_PATH)) as conn:
        try:
            log_event(conn, pipeline='pipeline_daily_sync', table=table, action=action, rows=rows, status=status, details=details)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description='Run daily sync pipeline')
    ap.add_argument('--season', type=int, default=2025)
    ap.add_argument('--week', type=int)
    ap.add_argument('--fetch', action='store_true', help='Fetch PFR data if nflscraPy is available')
    ap.add_argument('--limit', type=int, help='Limit games per season during fetch/map')
    args = ap.parse_args()

    # 1) Postgame sync
    update_scores = safe_import_update_scores()
    if update_scores:
        try:
            updated = update_scores(season=args.season, week=args.week)
            log_pipeline_event('games', 'postgame_sync', rows=int(updated or 0))
        except Exception as e:
            log_pipeline_event('games', 'postgame_sync', rows=0, status='error', details=str(e))

    # 2) Optional fetch + map
    if args.fetch:
        try:
            import importlib
            fetch_mod = importlib.import_module('src.scripts.fetch_pfr_nflscrapy')
            map_mod = importlib.import_module('src.scripts.map_nflscrapy_to_db')
            # Run fetcher minimally
            fetch_mod.main()
            # Run mapper for season
            map_mod.main()
            log_pipeline_event('pfr_*', 'fetch_map', rows=0)
        except Exception as e:
            log_pipeline_event('pfr_*', 'fetch_map', rows=0, status='error', details=str(e))

    # 3) Cleaner
    try:
        run_cleaner(include_logs=True)
        log_pipeline_event('ALL', 'clean_apply', rows=0)
    except Exception as e:
        log_pipeline_event('ALL', 'clean_apply', rows=0, status='error', details=str(e))

    print('✅ Daily sync pipeline complete')


if __name__ == '__main__':
    main()
