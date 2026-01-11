import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List
import pandas as pd
import nflscraPy

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
DB_PATH = DATA / 'nfl_model.db'
HIST = DATA / 'pfr_historical'


def name_alias_map() -> Dict[str, str]:
    t = nflscraPy._tms()
    m: Dict[str, str] = {}
    for _, v in t.items():
        full = f"{v.get('market','').strip()} {v.get('name','').strip()}".strip()
        alias = v.get('alias')
        if full and alias:
            m[full] = alias
    return m


def import_season(season: int) -> pd.DataFrame:
    games_path = HIST / f"{season}_games.csv"
    if not games_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(games_path)
    name_to_alias = name_alias_map()
    out_rows: List[Dict[str, object]] = []
    for _, r in df.iterrows():
        wk = r.get('week_num')
        try:
            week = int(float(wk))
        except Exception:
            # Skip non-numeric playoff labels (handled separately in other pipelines)
            continue
        date = r['game_date']
        winner = str(r['winner']).strip()
        loser = str(r['loser']).strip()
        loc = str(r['game_location']).strip()
        link = r['boxscore_url']
        # Determine home/away using location marker
        def to_int(x):
            try:
                return int(float(x))
            except Exception:
                return None
        if loc == '@':
            home_name, away_name = loser, winner
            home_points = to_int(r['pts_lose'])
            away_points = to_int(r['pts_win'])
        else:
            home_name, away_name = winner, loser
            home_points = to_int(r['pts_win'])
            away_points = to_int(r['pts_lose'])
        home_alias = name_to_alias.get(home_name)
        away_alias = name_to_alias.get(away_name)
        out_rows.append({
            'boxscore_stats_link': link,
            'season': season,
            'week': week,
            'tm_name': home_name,
            'opp_name': away_name,
            'tm_alias': home_alias,
            'opp_alias': away_alias,
            'tm_location': 'H',
            'opp_location': 'A',
            'tm_score': home_points,
            'opp_score': away_points,
            'event_date': date,
        })
    return pd.DataFrame(out_rows)


def import_team_stats(season: int, seasons_df: pd.DataFrame) -> pd.DataFrame:
    stats_path = HIST / f"{season}_team_gamelogs.csv"
    if not stats_path.exists() or seasons_df.empty:
        return pd.DataFrame()
    df = pd.read_csv(stats_path)
    # Build seasons index by date + participants aliases
    idx = seasons_df[['event_date','boxscore_stats_link','tm_alias','opp_alias']].copy()
    # Map 'team' (alias codes like NWE) to standard alias using nflscraPy
    alias_norm = {v['alias']: v['alias'] for _, v in nflscraPy._tms().items()}
    df['alias'] = df['team'].map(lambda x: alias_norm.get(str(x).upper(), str(x).upper()))
    # Map opponent name to alias via name map
    name_to_alias = name_alias_map()
    df['opp_alias'] = df['opp'].map(lambda n: name_to_alias.get(str(n).strip()))
    # Join to seasons to get boxscore link
    merged = df.merge(idx, left_on=['game_date','alias','opp_alias'], right_on=['event_date','tm_alias','opp_alias'], how='left')
    alt = df.merge(idx, left_on=['game_date','alias','opp_alias'], right_on=['event_date','opp_alias','tm_alias'], how='left')
    merged['boxscore_stats_link'] = merged['boxscore_stats_link'].fillna(alt['boxscore_stats_link'])
    # Minimal columns for pfr_stats
    out = merged[['boxscore_stats_link','alias','yards_off','pass_yds_off','rush_yds_off','pts_off']].copy()
    out = out.rename(columns={
        'yards_off':'total_yds',
        'pass_yds_off':'pass_yds',
        'rush_yds_off':'rush_yds',
        'pts_off':'points_for'
    })
    out['season'] = season
    return out.dropna(subset=['boxscore_stats_link'])


from utils.db_dedupe import to_sql_dedup_append
from utils.db_logging import log_event

def to_sql_append(df: pd.DataFrame, table: str) -> None:
    if df is None or df.empty:
        return
    with sqlite3.connect(str(DB_PATH)) as conn:
        written = to_sql_dedup_append(conn, df, table)
        try:
            log_event(conn, pipeline='import_pfr_historical', table=table, action='append_dedup', rows=written)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description='Import historical PFR CSVs into raw tables')
    ap.add_argument('--start', type=int, default=2020)
    ap.add_argument('--end', type=int, default=2024)
    args = ap.parse_args()
    for season in range(args.start, args.end+1):
        seasons_df = import_season(season)
        to_sql_append(seasons_df, 'pfr_seasons')
        stats_df = import_team_stats(season, seasons_df)
        to_sql_append(stats_df, 'pfr_stats')
    print('✅ Historical import complete')


if __name__ == '__main__':
    main()