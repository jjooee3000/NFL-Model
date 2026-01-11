#!/usr/bin/env python3
"""
Update completed game scores in SQLite using PFR.

- Fetches week or season game list via `PFRScraper.get_game_scores()`
- Resolves final away/home scores via `get_boxscore_basic(boxscore_url)`
- Updates `games` table `home_score`, `away_score`, `total_points`, `margin_home`

Usage:
  python src/scripts/update_postgame_scores.py --season 2025 --week 1
  python src/scripts/update_postgame_scores.py --season 2025
"""
import argparse
import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd

try:
    # Prefer relative import when running inside src
    from utils.pfr_scraper import PFRScraper
    from utils.paths import DATA_DIR
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    ROOT = _Path(__file__).resolve().parents[2]
    _sys.path.insert(0, str(ROOT / 'src'))
    from src.utils.pfr_scraper import PFRScraper
    from src.utils.paths import DATA_DIR


def update_scores(season: int, week: Optional[int] = None) -> int:
    db_path = DATA_DIR / "nfl_model.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 0

    # Prefer existing DB `pfr_seasons` to avoid rate limits
    with sqlite3.connect(str(db_path)) as conn:
        try:
            pfr = pd.read_sql_query(
                "SELECT season, week, tm_alias, opp_alias, tm_score, opp_score FROM pfr_seasons WHERE season = ? AND (week = ? OR ? IS NULL)",
                conn,
                params=(season, week, week)
            )
        except Exception:
            pfr = pd.DataFrame()
    if not pfr.empty:
        code_map = {
            'JAC': 'JAX', 'KC': 'KAN', 'TB': 'TAM', 'GB': 'GNB', 'NO': 'NOR',
            'LV': 'LVR', 'LA': 'LAR', 'SF': 'SFO', 'NE': 'NWE'
        }
        updates = []
        for _, r in pfr.iterrows():
            away = code_map.get(str(r.get('opp_alias')).upper(), str(r.get('opp_alias')).upper())
            home = code_map.get(str(r.get('tm_alias')).upper(), str(r.get('tm_alias')).upper())
            a_sc = r.get('opp_score')
            h_sc = r.get('tm_score')
            if pd.isna(a_sc) or pd.isna(h_sc):
                continue
            updates.append({'away_team': away, 'home_team': home, 'away_score': int(a_sc), 'home_score': int(h_sc)})
    else:
        scraper = PFRScraper()
        games_df = scraper.get_game_scores(season=season, week=week)
        if games_df is None or games_df.empty:
            print("No PFR games returned.")
            return 0
        updates = []
        # Iterate PFR games and resolve final scores via boxscore
        for _, row in games_df.iterrows():
            url = row.get('boxscore_url')
            if not url:
                continue
            info = scraper.get_boxscore_basic(url)
            away = info.get('away_team')
            home = info.get('home_team')
            a_sc = info.get('away_score')
            h_sc = info.get('home_score')
            if not away or not home or a_sc is None or h_sc is None:
                continue
            updates.append({'away_team': away, 'home_team': home, 'away_score': int(a_sc), 'home_score': int(h_sc)})

    # updates list is prepared above in either branch

    if not updates:
        print("No updates resolved from PFR sources.")
        return 0

    updated = 0
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        # Inspect games schema to avoid updating missing columns
        info = pd.read_sql_query("PRAGMA table_info(games)", conn)
        cols = set(info['name'].tolist())
        for u in updates:
            # Prefer matching by teams & season/week to avoid game_id mismatches
            cur.execute(
                """
                SELECT game_id FROM games
                WHERE season = ? AND (week = ? OR ? IS NULL)
                  AND away_team = ? AND home_team = ?
                LIMIT 1
                """,
                (season, week, week, u['away_team'], u['home_team'])
            )
            row = cur.fetchone()
            game_id = row[0] if row else None

            if {'total_points', 'margin_home'}.issubset(cols):
                cur.execute(
                    """
                    UPDATE games SET away_score = ?, home_score = ?,
                        total_points = (? + ?),
                        margin_home = (? - ?)
                    WHERE game_id = ?
                    """,
                    (
                        u['away_score'], u['home_score'],
                        u['away_score'], u['home_score'],
                        u['home_score'], u['away_score'],
                        game_id if game_id else f"{season}_{(week or 1):02d}_{u['away_team']}_{u['home_team']}"
                    )
                )
            else:
                cur.execute(
                    """
                    UPDATE games SET away_score = ?, home_score = ?
                    WHERE game_id = ?
                    """,
                    (
                        u['away_score'], u['home_score'],
                        game_id if game_id else f"{season}_{(week or 1):02d}_{u['away_team']}_{u['home_team']}"
                    )
                )
            if cur.rowcount:
                updated += 1
        conn.commit()

    print(f"Updated {updated} games with final scores.")
    return updated


def main():
    ap = argparse.ArgumentParser(description="Update completed game scores in SQLite via PFR")
    ap.add_argument('--season', type=int, required=True, help='Season year (e.g., 2025)')
    ap.add_argument('--week', type=int, help='Week number (use 1 for playoffs round if applicable)')
    args = ap.parse_args()

    update_scores(args.season, args.week)


if __name__ == '__main__':
    main()
