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
from typing import Optional, List, Dict, Any
import pandas as pd
import requests
from datetime import date as date_cls

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
        missing_pairs = []
        for _, r in pfr.iterrows():
            away = code_map.get(str(r.get('opp_alias')).upper(), str(r.get('opp_alias')).upper())
            home = code_map.get(str(r.get('tm_alias')).upper(), str(r.get('tm_alias')).upper())
            a_sc = r.get('opp_score')
            h_sc = r.get('tm_score')
            # Treat NaN or 0-0 as missing (PFR playoff rows often start as 0-0)
            if pd.isna(a_sc) or pd.isna(h_sc) or (float(a_sc) == 0 and float(h_sc) == 0):
                missing_pairs.append((away, home))
                continue
            updates.append({'away_team': away, 'home_team': home, 'away_score': int(a_sc), 'home_score': int(h_sc)})

        if missing_pairs:
            scraper = PFRScraper()
            games_df = scraper.get_game_scores(season=season, week=week)
            if games_df is not None and not games_df.empty:
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
                    pair = (away, home)
                    if pair in missing_pairs:
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

    def fetch_espn_score(away: str, home: str, game_date: str) -> Optional[Dict[str, Any]]:
        """Fetch score/state for a specific date/teams via ESPN scoreboard."""
        try:
            resp = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
                params={"dates": game_date.replace("-", "")},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            for ev in data.get("events", []):
                comps = ev.get("competitions", [])
                if not comps:
                    continue
                teams = comps[0].get("competitors", [])
                if len(teams) != 2:
                    continue
                tmap = {t.get("homeAway"): t for t in teams}
                home_abbr = (tmap.get("home", {}).get("team", {}).get("abbreviation") or "").upper()
                away_abbr = (tmap.get("away", {}).get("team", {}).get("abbreviation") or "").upper()
                if home_abbr == home and away_abbr == away:
                    h_sc = tmap.get("home", {}).get("score")
                    a_sc = tmap.get("away", {}).get("score")
                    state = comps[0].get("status", {}).get("type", {}).get("state")
                    start = comps[0].get("date") or ev.get("date")
                    if h_sc is not None and a_sc is not None and state == "post":
                        return {"away_score": int(a_sc), "home_score": int(h_sc), "state": state, "start": start}
                    return {"state": state, "start": start}
        except Exception:
            return None
        return None

    updated = 0
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        # Inspect games schema to avoid updating missing columns
        info = pd.read_sql_query("PRAGMA table_info(games)", conn)
        cols = set(info['name'].tolist())

        # Build a lookup for games missing scores to try ESPN fallback
        missing_rows = conn.execute(
            """
            SELECT game_id, week, away_team, home_team, "game_date_yyyy-mm-dd"
            FROM games
            WHERE season = ?
              AND (week = ? OR ? IS NULL)
              AND (home_score IS NULL OR away_score IS NULL OR (home_score = 0 AND away_score = 0))
              AND "game_date_yyyy-mm-dd" IS NOT NULL
            """,
            (season, week, week),
        ).fetchall()

        # Merge ESPN fallback scores into updates for any missing entries
        today_str = date_cls.today().isoformat()
        updates_for_missing: List[Dict[str, Any]] = []
        pending_reset: List[str] = []
        for r in missing_rows:
            gid, wk, away_team, home_team, gdate = r
            if not gdate:
                continue
            if gdate > today_str:
                pending_reset.append(gid)
                continue
            score = fetch_espn_score(away_team, home_team, gdate)
            if not score:
                pending_reset.append(gid)
                continue
            if score.get("state") == "post" and "away_score" in score and "home_score" in score:
                updates_for_missing.append({
                    'away_team': away_team,
                    'home_team': home_team,
                    'away_score': score['away_score'],
                    'home_score': score['home_score'],
                })
            elif score.get("state") in {"pre", "scheduled", "in", "inprogress", "live"}:
                pending_reset.append(gid)

        updates.extend(updates_for_missing)

        if pending_reset:
            cur.executemany(
                "UPDATE games SET away_score = NULL, home_score = NULL WHERE game_id = ? AND away_score = 0 AND home_score = 0",
                [(gid,) for gid in pending_reset]
            )

        for u in updates:
            # Prefer matching by teams & season/week to avoid game_id mismatches
            cur.execute(
                """
                SELECT game_id, week FROM games
                WHERE season = ? AND (week = ? OR ? IS NULL)
                  AND away_team = ? AND home_team = ?
                LIMIT 1
                """,
                (season, week, week, u['away_team'], u['home_team'])
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT game_id, week FROM games
                    WHERE season = ? AND away_team = ? AND home_team = ?
                    ORDER BY week DESC
                    LIMIT 1
                    """,
                    (season, u['away_team'], u['home_team'])
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
