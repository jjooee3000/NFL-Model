from pathlib import Path
import sqlite3
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / 'data' / 'nfl_model.db'


def compute_priors_for_season(conn: sqlite3.Connection, season: int) -> pd.DataFrame:
    tg = pd.read_sql_query('SELECT * FROM team_games WHERE game_id IN (SELECT game_id FROM games WHERE season=?)', conn, params=(season,))
    sc = pd.read_sql_query('SELECT * FROM game_scoring_summary WHERE game_id IN (SELECT game_id FROM games WHERE season=?)', conn, params=(season,))
    if tg.empty:
        return pd.DataFrame()
    # Derive per game offense plays and rush attempts
    tg['plays'] = tg.get('plays') if 'plays' in tg.columns else None
    tg['rush_att'] = tg.get('rush_att') if 'rush_att' in tg.columns else None
    # Aggregate to team-season
    grp = tg.groupby('team').agg({
        'plays':'sum',
        'rush_att':'sum',
        'opp_3d_att':'sum',
        'opp_3d_conv':'sum'
    }).reset_index()
    grp['season'] = season
    # TD counts from scoring summary
    if not sc.empty:
        sc_team = sc.groupby('team').agg({'td_rush':'sum','td_pass':'sum'}).reset_index()
        grp = grp.merge(sc_team, on='team', how='left')
    else:
        grp[['td_rush','td_pass']] = 0
    # Compute metrics
    def safe_div(a, b):
        return float(a)/float(b) if (a is not None and b is not None and b != 0) else None
    priors = []
    for _, r in grp.iterrows():
        plays = r.get('plays') or 0
        rush = r.get('rush_att') or 0
        pass_est = plays - rush if plays and rush is not None else None
        pass_rate_off = safe_div(pass_est, plays) if pass_est is not None else None
        rush_rate_off = safe_div(rush, plays) if plays else None
        third_def_pct = safe_div(r.get('opp_3d_conv') or 0, r.get('opp_3d_att') or 0)
        td_total = (r.get('td_rush') or 0) + (r.get('td_pass') or 0)
        # Prepare JSON payload
        payload = {
            'pass_rate_off': pass_rate_off,
            'rush_rate_off': rush_rate_off,
            'third_down_def_pct': third_def_pct,
            'td_rate_off': td_total  # season total; feature_builder will diff raw totals as prior proxy
        }
        priors.append({'team': r['team'], 'season': season, 'metrics_json': json.dumps(payload)})
    return pd.DataFrame(priors)


def upsert_team_season_splits(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    if df.empty:
        return
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS team_season_splits (team TEXT, season INTEGER, metrics_json TEXT)')
    for _, r in df.iterrows():
        cur.execute('SELECT 1 FROM team_season_splits WHERE team=? AND season=?', (r['team'], int(r['season'])))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute('UPDATE team_season_splits SET metrics_json=? WHERE team=? AND season=?', (r['metrics_json'], r['team'], int(r['season'])))
        else:
            cur.execute('INSERT INTO team_season_splits (team, season, metrics_json) VALUES (?,?,?)', (r['team'], int(r['season']), r['metrics_json']))
    conn.commit()


def main():
    seasons = list(range(2020, 2026))
    with sqlite3.connect(str(DB_PATH)) as conn:
        for s in seasons:
            df = compute_priors_for_season(conn, s)
            upsert_team_season_splits(conn, df)
    print('✅ Synthetic splits priors computed')


if __name__ == '__main__':
    main()