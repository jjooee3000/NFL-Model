"""
Map nflscraPy tables into existing model DB schema (games, team_games, odds).

- Source tables: pfr_seasons, pfr_metadata, pfr_stats
- Target tables: games, team_games, odds

Usage:
  python src/scripts/map_nflscrapy_to_db.py --season 2025 --limit 50

Notes:
- Idempotent upsert: will insert new rows and update existing by game_id.
- Handles home/away determination via season 'tm_location'/'opp_location'.
- Derives 'game_id' as season + Week + AWAY_HOME (e.g., 2025_W01_BUF_JAX).
"""
import sys
from pathlib import Path
import argparse
import sqlite3
from typing import Optional
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
DB_PATH = DATA / 'nfl_model.db'

TEAM_CODE_FIXES = {
    # Normalize any historic PFR codes to our alias set
    'SDG': 'LAC',
    'OTI': 'TEN',
    'LAR': 'LAR',
    'RAI': 'LVR',
    'CRD': 'ARI',
    'GNB': 'GNB',
    'KAN': 'KAN',
    'NOR': 'NOR',
}


def norm_team(code: str) -> str:
    if not isinstance(code, str):
        return str(code)
    c = code.upper()
    return TEAM_CODE_FIXES.get(c, c)


def derive_game_id(season: int, week: int, away: str, home: str) -> str:
    return f"{int(season)}_W{int(week):02d}_{norm_team(away)}_{norm_team(home)}"


def upsert_games(conn: sqlite3.Connection, seasons_df: pd.DataFrame, metadata_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    # Merge seasons + metadata on boxscore_stats_link
    df = seasons_df.merge(
        metadata_df,
        on='boxscore_stats_link',
        how='left',
        suffixes=('', '_md')
    )
    if limit:
        df = df.head(limit)
    cur = conn.cursor()
    for _, r in df.iterrows():
        season = int(r['season'])
        week = int(r['week']) if pd.notna(r['week']) else 0
        tm_alias = norm_team(r['tm_alias'])
        opp_alias = norm_team(r['opp_alias'])
        # Determine home/away based on location
        tm_loc = str(r.get('tm_location') or '').upper()
        opp_loc = str(r.get('opp_location') or '').upper()
        if tm_loc == 'H':
            home, away = tm_alias, opp_alias
        elif opp_loc == 'H':
            home, away = opp_alias, tm_alias
        else:
            # Default to tm as home if unknown; mark neutral
            home, away = tm_alias, opp_alias
        game_id = derive_game_id(season, week, away, home)
        # Basic weather
        temp_f = r.get('temperature')
        humidity_pct = r.get('humidity_pct')
        wind_mph = r.get('wind_speed')
        roof = r.get('roof_type')
        surface = r.get('surface_type')
        # scores from seasons
        home_score = int(r.get('tm_score') or 0) if home == tm_alias else int(r.get('opp_score') or 0)
        away_score = int(r.get('opp_score') or 0) if home == tm_alias else int(r.get('tm_score') or 0)
        # Insert or update via existence check (handles DBs without unique constraints)
        cur.execute("SELECT 1 FROM games WHERE game_id = ?", (game_id,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                """
                UPDATE games SET
                  season=?, week=?, home_team=?, away_team=?, home_score=?, away_score=?,
                  temp_f=?, humidity_pct=?, wind_mph=?, roof_dome_outdoor_retractable_unknown=?, surface=?,
                  "game_date_yyyy-mm-dd"=?, neutral_site_0_1=?
                WHERE game_id=?
                """,
                (
                    season, week, home, away, home_score, away_score,
                    temp_f, humidity_pct, wind_mph, roof, surface,
                    r.get('event_date'), 1 if (tm_loc == 'N' or opp_loc == 'N') else None,
                    game_id,
                )
            )
        else:
            cur.execute(
                """
                INSERT INTO games (game_id, season, week, home_team, away_team, home_score, away_score,
                                   temp_f, humidity_pct, wind_mph, roof_dome_outdoor_retractable_unknown, surface,
                                   "game_date_yyyy-mm-dd", is_indoor, neutral_site_0_1)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    game_id, season, week, home, away, home_score, away_score,
                    temp_f, humidity_pct, wind_mph, roof, surface,
                    r.get('event_date'), None,
                    1 if (tm_loc == 'N' or opp_loc == 'N') else None,
                )
            )
    conn.commit()


def upsert_team_games(conn: sqlite3.Connection, seasons_df: pd.DataFrame, stats_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    # Build game_id per stats row by joining to seasons via href
    df = stats_df.merge(
        seasons_df[['boxscore_stats_link','season','week','tm_alias','opp_alias','tm_location','opp_location','tm_score','opp_score']],
        on='boxscore_stats_link',
        how='left',
        suffixes=('', '_s')
    )
    if limit:
        df = df.head(limit)
    cur = conn.cursor()
    for _, r in df.iterrows():
        season = int(r['season_s']) if 'season_s' in r else int(r['season'])
        week = int(r['week_s']) if 'week_s' in r and pd.notna(r['week_s']) else (int(r['week']) if pd.notna(r['week']) else 0)
        alias = norm_team(r['alias'])
        tm_alias = norm_team(r['tm_alias_s']) if 'tm_alias_s' in r else norm_team(r['tm_alias'])
        opp_alias = norm_team(r['opp_alias_s']) if 'opp_alias_s' in r else norm_team(r['opp_alias'])
        tm_loc = str(r.get('tm_location_s') or r.get('tm_location') or '').upper()
        opp_loc = str(r.get('opp_location_s') or r.get('opp_location') or '').upper()
        # Determine home team to set is_home
        if tm_loc == 'H':
            home = tm_alias
        elif opp_loc == 'H':
            home = opp_alias
        else:
            home = tm_alias
        # compute away based on who is not home
        away = opp_alias if home == tm_alias else tm_alias
        game_id = derive_game_id(season, week, away, home)
        is_home = 1 if alias == home else 0
        # points_for/against from seasons scores
        tm_score = r['tm_score_s'] if 'tm_score_s' in r else r.get('tm_score')
        opp_score = r['opp_score_s'] if 'opp_score_s' in r else r.get('opp_score')
        points_for = int(tm_score) if alias == tm_alias else int(opp_score)
        points_against = int(opp_score) if alias == tm_alias else int(tm_score)
        # Map stats
        rush_att = r.get('rush_att')
        rush_yds = r.get('rush_yds')
        rush_tds = r.get('rush_tds')
        pass_att = r.get('pass_att')
        pass_cmp = r.get('pass_cmp')
        pass_yds = r.get('pass_yds')
        total_yds = r.get('total_yds')
        fumbles_lost = r.get('fumbles_lost')
        penalties = r.get('penalties')
        penalty_yds = r.get('penalty_yds')
        third_att = r.get('third_down_att')
        third_conv = r.get('third_down_conv')
        third_pct = r.get('third_down_conv_pct')
        fourth_att = r.get('fourth_down_att')
        fourth_conv = r.get('fourth_down_conv')
        fourth_pct = r.get('fourth_down_conv_pct')
        # Insert or update minimal columns via existence check
        cur.execute("SELECT 1 FROM team_games WHERE game_id = ? AND team = ?", (game_id, alias))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                """
                UPDATE team_games SET
                  opponent=?, is_home_0_1=?,
                  points_for=?, points_against=?,
                  rush_att=?, rush_yds=?, rush_td=?,
                  penalties=?, penalty_yards=?,
                  opp_3d_att=?, opp_3d_conv=?, opp_3d_pct=?,
                  opp_4d_att=?, opp_4d_conv=?, opp_4d_pct=?
                WHERE game_id=? AND team=?
                """,
                (
                    (opp_alias if alias == tm_alias else tm_alias), is_home,
                    points_for, points_against,
                    rush_att, rush_yds, rush_tds,
                    penalties, penalty_yds,
                    third_att, third_conv, third_pct,
                    fourth_att, fourth_conv, fourth_pct,
                    game_id, alias,
                )
            )
        else:
            cur.execute(
                """
                INSERT INTO team_games (
                  game_id, team, opponent, is_home_0_1,
                  points_for, points_against,
                  rush_att, rush_yds, rush_td,
                  penalties, penalty_yards,
                  opp_3d_att, opp_3d_conv, opp_3d_pct,
                  opp_4d_att, opp_4d_conv, opp_4d_pct
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    game_id, alias, (opp_alias if alias == tm_alias else tm_alias), is_home,
                    points_for, points_against,
                    rush_att, rush_yds, rush_tds,
                    penalties, penalty_yds,
                    third_att, third_conv, third_pct,
                    fourth_att, fourth_conv, fourth_pct,
                )
            )
    conn.commit()


def upsert_odds(conn: sqlite3.Connection, metadata_df: pd.DataFrame, seasons_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    df = metadata_df.merge(
        seasons_df[['boxscore_stats_link','season','week','tm_alias','opp_alias']],
        on='boxscore_stats_link',
        how='left',
        suffixes=('', '_s')
    )
    if limit:
        df = df.head(limit)
    cur = conn.cursor()
    for _, r in df.iterrows():
        season = int(r['season_s']) if 'season_s' in r else int(r['season'])
        week = int(r['week_s']) if 'week_s' in r and pd.notna(r['week_s']) else (int(r['week']) if pd.notna(r['week']) else 0)
        home = norm_team(r['tm_alias_s']) if 'tm_alias_s' in r else norm_team(r['tm_alias'])
        away = norm_team(r['opp_alias_s']) if 'opp_alias_s' in r else norm_team(r['opp_alias'])
        game_id = derive_game_id(season, week, away, home)
        # Use metadata's consensus numbers as 'close' values, sportsbook 'pfr'
        close_spread_home = r.get('tm_spread')
        close_total = r.get('total')
        cur.execute("SELECT 1 FROM odds WHERE game_id = ? AND sportsbook = ?", (game_id, 'pfr'))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                "UPDATE odds SET close_spread_home=?, close_total=? WHERE game_id=? AND sportsbook=?",
                (close_spread_home, close_total, game_id, 'pfr')
            )
        else:
            cur.execute(
                "INSERT INTO odds (game_id, sportsbook, close_spread_home, close_total) VALUES (?,?,?,?)",
                (game_id, 'pfr', close_spread_home, close_total)
            )
    conn.commit()


def upsert_team_game_epa(conn: sqlite3.Connection, seasons_df: pd.DataFrame, expected_points_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    # Join expected_points to seasons to derive game_id and normalize team alias
    df = expected_points_df.merge(
        seasons_df[['boxscore_stats_link','season','week','tm_alias','opp_alias','tm_location','opp_location']],
        on='boxscore_stats_link', how='left', suffixes=('', '_s')
    )
    if limit:
        df = df.head(limit)
    cur = conn.cursor()
    for _, r in df.iterrows():
        season = int(r['season_s']) if 'season_s' in r else int(r['season'])
        week = int(r['week']) if pd.notna(r['week']) else 0
        tm_alias = norm_team(r['tm_alias'])
        opp_alias = norm_team(r['opp_alias'])
        tm_loc = str(r.get('tm_location') or '').upper()
        opp_loc = str(r.get('opp_location') or '').upper()
        # Determine home/away
        if tm_loc == 'H':
            home, away = tm_alias, opp_alias
        elif opp_loc == 'H':
            home, away = opp_alias, tm_alias
        else:
            home, away = tm_alias, opp_alias
        game_id = derive_game_id(season, week, away, home)
        team = norm_team(r['alias'])
        # Values
        fields = [
            'exp_pts','exp_pts_off','exp_pts_off_pass','exp_pts_off_rush','exp_pts_off_turnover',
            'exp_pts_def','exp_pts_def_pass','exp_pts_def_rush','exp_pts_def_turnover',
            'exp_pts_st','exp_pts_kickoff','exp_pts_kick_return','exp_pts_punt','exp_pts_punt_return','exp_pts_fg_xp'
        ]
        values = [r.get(f) for f in fields]
        # Upsert into team_game_epa
        cur.execute("SELECT 1 FROM team_game_epa WHERE game_id = ? AND team = ?", (game_id, team))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                f"UPDATE team_game_epa SET {', '.join([f + '=?' for f in fields])} WHERE game_id=? AND team=?",
                (*values, game_id, team)
            )
        else:
            cur.execute(
                f"INSERT INTO team_game_epa (game_id, team, {', '.join(fields)}) VALUES ({','.join(['?']*(2+len(fields)))})",
                (game_id, team, *values)
            )
    conn.commit()


def upsert_game_scoring_summary(conn: sqlite3.Connection, seasons_df: pd.DataFrame, scoring_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    # Join scoring to seasons to derive game_id
    df = scoring_df.merge(
        seasons_df[['boxscore_stats_link','season','week','tm_name','tm_alias','opp_name','opp_alias']],
        on='boxscore_stats_link', how='left', suffixes=('', '_s')
    )
    if limit:
        df = df.head(limit)
    # Derive team alias from scoring_team name
    def team_from_row(row):
        if str(row.get('scoring_team') or '').strip() == str(row.get('tm_name') or '').strip():
            return norm_team(row.get('tm_alias'))
        elif str(row.get('scoring_team') or '').strip() == str(row.get('opp_name') or '').strip():
            return norm_team(row.get('opp_alias'))
        return None
    df['team_alias'] = df.apply(team_from_row, axis=1)
    # Classify scoring types from description text
    def classify(desc: str):
        d = (desc or '').lower()
        return {
            'td_rush': int('rush' in d and 'yard' in d and 'kick' in d or 'rush' in d and 'touchdown' in d),
            'td_pass': int('pass' in d and ('yard' in d or 'touchdown' in d) and 'kick' in d or ('pass' in d and 'touchdown' in d)),
            'fg_made': int('field goal' in d or 'fg is good' in d),
            'safety': int('safety' in d),
            'two_pt_success': int('two-point' in d and ('is good' in d or 'conversion' in d))
        }
    class_cols = ['td_rush','td_pass','fg_made','safety','two_pt_success']
    for c in class_cols:
        df[c] = 0
    for idx, row in df.iterrows():
        classified = classify(row.get('description') or '')
        for c in class_cols:
            df.at[idx, c] = classified[c]
    # Aggregate per game/team
    agg = df.groupby(['boxscore_stats_link','team_alias']).agg({c:'sum' for c in class_cols}).reset_index()
    # Attach season/week/home/away to form game_id
    agg = agg.merge(seasons_df[['boxscore_stats_link','season','week','tm_alias','opp_alias','tm_location','opp_location']], on='boxscore_stats_link', how='left')
    cur = conn.cursor()
    for _, r in agg.iterrows():
        season = int(r['season'])
        week = int(r['week']) if pd.notna(r['week']) else 0
        tm_alias = norm_team(r['tm_alias'])
        opp_alias = norm_team(r['opp_alias'])
        tm_loc = str(r.get('tm_location') or '').upper()
        opp_loc = str(r.get('opp_location') or '').upper()
        if tm_loc == 'H':
            home, away = tm_alias, opp_alias
        elif opp_loc == 'H':
            home, away = opp_alias, tm_alias
        else:
            home, away = tm_alias, opp_alias
        game_id = derive_game_id(season, week, away, home)
        team = norm_team(r['team_alias'])
        values = [int(r.get(c) or 0) for c in class_cols]
        # Upsert into game_scoring_summary
        cur.execute("SELECT 1 FROM game_scoring_summary WHERE game_id = ? AND team = ?", (game_id, team))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                f"UPDATE game_scoring_summary SET {', '.join([f + '=?' for f in class_cols])} WHERE game_id=? AND team=?",
                (*values, game_id, team)
            )
        else:
            cur.execute(
                f"INSERT INTO game_scoring_summary (game_id, team, {', '.join(class_cols)}) VALUES ({','.join(['?']*(2+len(class_cols)))})",
                (game_id, team, *values)
            )
    conn.commit()


def upsert_team_game_snaps(conn: sqlite3.Connection, seasons_df: pd.DataFrame, snaps_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    # Aggregate player-level snaps to team totals per game
    df = snaps_df.merge(
        seasons_df[['boxscore_stats_link','season','week','tm_alias','opp_alias','tm_location','opp_location']],
        on='boxscore_stats_link', how='left', suffixes=('', '_s')
    )
    if limit:
        df = df.head(limit)
    agg = df.groupby(['boxscore_stats_link','alias']).agg({
        'snap_count_offense':'sum',
        'snap_count_defense':'sum',
        'snap_count_special_teams':'sum'
    }).reset_index().rename(columns={'alias':'team'})
    cur = conn.cursor()
    for _, r in agg.iterrows():
        link = r['boxscore_stats_link']
        row = seasons_df[seasons_df['boxscore_stats_link'] == link].iloc[0]
        season = int(row['season'])
        week = int(row['week']) if pd.notna(row['week']) else 0
        tm_alias = norm_team(row['tm_alias'])
        opp_alias = norm_team(row['opp_alias'])
        tm_loc = str(row.get('tm_location') or '').upper()
        opp_loc = str(row.get('opp_location') or '').upper()
        if tm_loc == 'H':
            home, away = tm_alias, opp_alias
        elif opp_loc == 'H':
            home, away = opp_alias, tm_alias
        else:
            home, away = tm_alias, opp_alias
        game_id = derive_game_id(season, week, away, home)
        team = norm_team(r['team'])
        off = int(r.get('snap_count_offense') or 0)
        deff = int(r.get('snap_count_defense') or 0)
        st = int(r.get('snap_count_special_teams') or 0)
        # Create table if needed and upsert
        cur.execute("CREATE TABLE IF NOT EXISTS team_game_snaps (game_id TEXT, team TEXT, snaps_offense INTEGER, snaps_defense INTEGER, snaps_special_teams INTEGER)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_team_game_snaps ON team_game_snaps (game_id, team)")
        cur.execute("SELECT 1 FROM team_game_snaps WHERE game_id = ? AND team = ?", (game_id, team))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute("UPDATE team_game_snaps SET snaps_offense=?, snaps_defense=?, snaps_special_teams=? WHERE game_id=? AND team=?",
                        (off, deff, st, game_id, team))
        else:
            cur.execute("INSERT INTO team_game_snaps (game_id, team, snaps_offense, snaps_defense, snaps_special_teams) VALUES (?,?,?,?,?)",
                        (game_id, team, off, deff, st))
    conn.commit()


def upsert_team_season_splits(conn: sqlite3.Connection, splits_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    """
    Store team-season splits as JSON payload for flexible prior features.

    Schema: team_season_splits(team TEXT, season INTEGER, metrics_json TEXT)
    Upsert by (team, season).
    """
    if splits_df.empty:
        return
    df = splits_df.copy()
    # Normalize team alias
    team_col = 'alias' if 'alias' in df.columns else ('tm_alias' if 'tm_alias' in df.columns else None)
    season_col = 'season' if 'season' in df.columns else None
    if team_col is None or season_col is None:
        return
    df['team'] = df[team_col].apply(norm_team)
    df['season'] = df[season_col].astype(int)
    # Group rows per team-season and serialize as JSON list of dicts
    groups = df.groupby(['team','season'])
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS team_season_splits (team TEXT, season INTEGER, metrics_json TEXT)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_team_season_splits ON team_season_splits (team, season)")
    count = 0
    for (team, season), grp in groups:
        if limit and count >= limit:
            break
        # Drop obviously non-data columns when present
        drop_cols = [c for c in grp.columns if 'link' in c or 'url' in c]
        payload_rows = grp.drop(columns=drop_cols, errors='ignore')
        payload = payload_rows.to_dict(orient='records')
        metrics_json = json.dumps(payload)
        # Upsert
        cur.execute("SELECT 1 FROM team_season_splits WHERE team = ? AND season = ?", (team, season))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute("UPDATE team_season_splits SET metrics_json=? WHERE team=? AND season=?",
                        (metrics_json, team, season))
        else:
            cur.execute("INSERT INTO team_season_splits (team, season, metrics_json) VALUES (?,?,?)",
                        (team, season, metrics_json))
        count += 1
    conn.commit()


def upsert_game_elo(conn: sqlite3.Connection, seasons_df: pd.DataFrame, elo_df: pd.DataFrame, limit: Optional[int] = None) -> None:
    # Attempt to map Elo rows to game_id via season+event_date+aliases
    df = elo_df.copy()
    # Normalize columns heuristically if present
    # Expect columns: date, season, team1, team2, elo1_pre, elo2_pre, prob1, prob2
    if 'season' not in df.columns:
        return
    # Build candidate join keys
    seasons_keyed = seasons_df[['season','event_date','tm_alias','opp_alias','tm_location','opp_location']].copy()
    seasons_keyed['event_date'] = pd.to_datetime(seasons_keyed['event_date'])
    df['date'] = pd.to_datetime(df.get('date') or df.get('event_date') or df.get('game_date') )
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS game_elo (game_id TEXT, home_elo REAL, away_elo REAL, home_prob REAL)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_game_elo ON game_elo (game_id)")
    # Iterate seasons rows and match by date and teams
    if limit:
        seasons_keyed = seasons_keyed.head(limit)
    for _, s in seasons_keyed.iterrows():
        season = int(s['season'])
        dt = s['event_date']
        home, away = None, None
        tm_alias = norm_team(s['tm_alias'])
        opp_alias = norm_team(s['opp_alias'])
        tm_loc = str(s.get('tm_location') or '').upper()
        opp_loc = str(s.get('opp_location') or '').upper()
        if tm_loc == 'H':
            home, away = tm_alias, opp_alias
        elif opp_loc == 'H':
            home, away = opp_alias, tm_alias
        else:
            home, away = tm_alias, opp_alias
        # Find Elo row(s) for that date and teams
        matches = df[(df['season'] == season) & (df['date'] == pd.to_datetime(dt))]
        if matches.empty:
            continue
        row = matches.iloc[0]
        # Columns vary; try common names
        team1 = norm_team(str(row.get('team1') or row.get('home_team') or ''))
        team2 = norm_team(str(row.get('team2') or row.get('away_team') or ''))
        elo1 = row.get('elo1_pre') or row.get('team1_elo')
        elo2 = row.get('elo2_pre') or row.get('team2_elo')
        prob1 = row.get('prob1') or row.get('home_prob')
        # Assign to home/away orientation
        if team1 == home and team2 == away:
            home_elo, away_elo, home_prob = elo1, elo2, prob1
        elif team2 == home and team1 == away:
            home_elo, away_elo, home_prob = elo2, elo1, (1.0 - (prob1 or 0.5))
        else:
            continue
        game_id = derive_game_id(season, int(pd.to_datetime(dt).strftime('%U')) if pd.isna(s['event_date']) else int(s.get('week') or 0), away, home)
        # Upsert
        cur.execute("SELECT 1 FROM game_elo WHERE game_id = ?", (game_id,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute("UPDATE game_elo SET home_elo=?, away_elo=?, home_prob=? WHERE game_id=?",
                        (home_elo, away_elo, home_prob, game_id))
        else:
            cur.execute("INSERT INTO game_elo (game_id, home_elo, away_elo, home_prob) VALUES (?,?,?,?)",
                        (game_id, home_elo, away_elo, home_prob))
    conn.commit()


def main():
    ap = argparse.ArgumentParser(description='Map nflscraPy tables to model DB')
    ap.add_argument('--season', type=int, default=2025)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()

    with sqlite3.connect(str(DB_PATH)) as conn:
        # Load sources
        seasons = pd.read_sql_query('SELECT * FROM pfr_seasons WHERE season = ?', conn, params=(args.season,))
        metadata = pd.read_sql_query('SELECT * FROM pfr_metadata WHERE season = ?', conn, params=(args.season,))
        stats = pd.read_sql_query('SELECT * FROM pfr_stats WHERE season = ?', conn, params=(args.season,))
        # Optional tables
        try:
            expected_points = pd.read_sql_query('SELECT * FROM pfr_expected_points WHERE season = ?', conn, params=(args.season,))
        except Exception:
            expected_points = pd.DataFrame()
        try:
            scoring = pd.read_sql_query('SELECT * FROM pfr_scoring WHERE season = ?', conn, params=(args.season,))
        except Exception:
            scoring = pd.DataFrame()
        try:
            snaps = pd.read_sql_query('SELECT * FROM pfr_snap_counts WHERE season = ?', conn, params=(args.season,))
        except Exception:
            snaps = pd.DataFrame()
        try:
            elo = pd.read_sql_query('SELECT * FROM fte_elo WHERE season = ?', conn, params=(args.season,))
        except Exception:
            elo = pd.DataFrame()
        try:
            splits = pd.read_sql_query('SELECT * FROM pfr_splits WHERE season = ?', conn, params=(args.season,))
        except Exception:
            splits = pd.DataFrame()
        if seasons.empty:
            print('No pfr_seasons rows found; run fetch_pfr_nflscrapy.py first')
            return
        upsert_games(conn, seasons, metadata, limit=args.limit)
        upsert_team_games(conn, seasons, stats, limit=args.limit)
        upsert_odds(conn, metadata, seasons, limit=args.limit)
        if not expected_points.empty:
            upsert_team_game_epa(conn, seasons, expected_points, limit=args.limit)
        if not scoring.empty:
            upsert_game_scoring_summary(conn, seasons, scoring, limit=args.limit)
        if not snaps.empty:
            upsert_team_game_snaps(conn, seasons, snaps, limit=args.limit)
        if not elo.empty:
            upsert_game_elo(conn, seasons, elo, limit=args.limit)
        if not splits.empty:
            upsert_team_season_splits(conn, splits, limit=args.limit)
    print('✅ Mapping complete')


if __name__ == '__main__':
    main()
