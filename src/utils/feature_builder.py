"""
Feature Builder: Assemble model-ready features from SQLite tables.

Builds per-game feature vectors using rolling team aggregates for:
- Expected points (team_game_epa)
- Scoring summary rates (game_scoring_summary)
- Snap totals (team_game_snaps)
- Elo prior (game_elo)
- Odds (odds)
- Weather/stadium (games, pfr_metadata)

Outputs a DataFrame keyed by game_id with home/away combined features and target margin.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
import sqlite3
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / 'data' / 'nfl_model.db'


@dataclass
class FeatureConfig:
    windows: List[int] = (3, 5, 8)


def _load_table(conn: sqlite3.Connection, name: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(f'SELECT * FROM {name}', conn)
    except Exception:
        return pd.DataFrame()


def build_features(config: Optional[FeatureConfig] = None) -> pd.DataFrame:
    cfg = config or FeatureConfig()
    with sqlite3.connect(str(DB_PATH)) as conn:
        games = _load_table(conn, 'games')
        epa = _load_table(conn, 'team_game_epa')
        scoring = _load_table(conn, 'game_scoring_summary')
        snaps = _load_table(conn, 'team_game_snaps')
        elo = _load_table(conn, 'game_elo')
        odds = _load_table(conn, 'odds')
        splits = _load_table(conn, 'team_season_splits')

    if games.empty:
        raise RuntimeError('games table empty; run backfill first')

    # Prepare team-level time series by game
    # Build unified team_game index using EPA or snaps/scoring where available
    team_frames = []
    for df in [epa, snaps, scoring]:
        if not df.empty:
            cols = {'game_id', 'team'}
            df2 = df.copy()
            # Normalize column names for scoring
            if 'team' not in df2.columns and 'team_alias' in df2.columns:
                df2['team'] = df2['team_alias']
            if cols.issubset(df2.columns):
                team_frames.append(df2)
    if not team_frames:
        raise RuntimeError('No team-level feature tables present (EPA/snaps/scoring)')
    team_games = team_frames[0][['game_id','team']].drop_duplicates()
    # Merge all team-level features into one wide table
    base = team_games.copy()
    for df in team_frames:
        base = base.merge(df, on=['game_id','team'], how='left')

    # Attach week + home/away + opponents from games
    g = games[['game_id','season','week','home_team','away_team','home_score','away_score','temp_f','wind_mph','humidity_pct']].copy()
    base = base.merge(g, on='game_id', how='left')
    base['is_home'] = (base['team'] == base['home_team']).astype(int)
    base['opponent'] = np.where(base['is_home']==1, base['away_team'], base['home_team'])
    base['points_for'] = np.where(base['is_home']==1, base['home_score'], base['away_score'])
    base['points_against'] = np.where(base['is_home']==1, base['away_score'], base['home_score'])

    # Rolling aggregates per team
    base.sort_values(['team','season','week'], inplace=True)
    def add_roll(col: str, w: int):
        base[f'{col}_pre{w}'] = base.groupby('team')[col].shift(1).rolling(w, min_periods=1).mean().values

    for w in cfg.windows:
        for col in ['exp_pts','exp_pts_off','exp_pts_def','td_rush','td_pass','fg_made','safety','two_pt_success',
                    'snaps_offense','snaps_defense','snaps_special_teams','points_for','points_against']:
            if col in base.columns:
                add_roll(col, w)

    # Build game-level features: home minus away differences
    # First split home and away rows
    home_rows = base[base['is_home']==1].copy()
    away_rows = base[base['is_home']==0].copy()
    home_rows.set_index('game_id', inplace=True)
    away_rows.set_index('game_id', inplace=True)

    def diff_cols(prefix: str, cols: List[str]) -> pd.DataFrame:
        out = pd.DataFrame(index=home_rows.index)
        for c in cols:
            if c in home_rows.columns and c in away_rows.columns:
                out[f'{prefix}{c}'] = home_rows[c] - away_rows[c]
        return out

    roll_cols = [c for c in home_rows.columns if any(c.endswith(f'_pre{w}') for w in cfg.windows)]
    diff = diff_cols('d_', roll_cols)

    # Include priors: Elo home_prob and odds close_spread_home
    gp = games[['game_id','season','week','home_team','away_team']].copy()
    feat = gp.join(diff, on='game_id')
    # Integrate splits priors when available
    if not splits.empty:
        # Parse JSON payload into selected metrics per team-season
        def parse_metrics(row):
            try:
                payload = json.loads(row['metrics_json']) if isinstance(row.get('metrics_json'), str) else []
            except Exception:
                payload = []
            metrics = {}
            # Flatten and search heuristically for metric keys
            for item in payload if isinstance(payload, list) else []:
                for k, v in item.items():
                    if v is None:
                        continue
                    if isinstance(v, (int, float)):
                        kl = str(k).lower()
                        # Third down conversion % (offense/defense)
                        if 'third' in kl and 'down' in kl and '%' in kl or 'pct' in kl:
                            if 'opp' in kl or 'against' in kl or 'def' in kl:
                                metrics.setdefault('third_down_def_pct', float(v))
                            else:
                                metrics.setdefault('third_down_off_pct', float(v))
                        # Red zone TD % (offense/defense)
                        if 'red' in kl and 'zone' in kl and ('td' in kl or 'touchdown' in kl) and ('%' in kl or 'pct' in kl):
                            if 'opp' in kl or 'against' in kl or 'def' in kl:
                                metrics.setdefault('red_zone_def_td_pct', float(v))
                            else:
                                metrics.setdefault('red_zone_off_td_pct', float(v))
                        # Pass/Rush rate (offense)
                        if 'pass' in kl and ('rate' in kl or 'ratio' in kl) and not ('opp' in kl or 'against' in kl):
                            metrics.setdefault('pass_rate_off', float(v))
                        if 'rush' in kl and ('rate' in kl or 'ratio' in kl) and not ('opp' in kl or 'against' in kl):
                            metrics.setdefault('rush_rate_off', float(v))
            return pd.Series(metrics)

        splits_parsed = splits.copy()
        metrics_df = splits_parsed.apply(parse_metrics, axis=1)
        expected_cols = ['third_down_off_pct','third_down_def_pct','red_zone_off_td_pct','red_zone_def_td_pct','pass_rate_off','rush_rate_off','td_rate_off']
        for c in expected_cols:
            splits_parsed[c] = metrics_df[c] if c in metrics_df.columns else None
        # Deduplicate to one row per team-season
        splits_priors = splits_parsed[['team','season'] + expected_cols].drop_duplicates(subset=['team','season'])
        # Attach priors to home/away, then build differences
        feat = feat.merge(splits_priors.rename(columns={'team':'home_team'}), on=['home_team','season'], how='left', suffixes=('','_home_prior'))
        feat = feat.merge(splits_priors.rename(columns={'team':'away_team'}), on=['away_team','season'], how='left', suffixes=('','_away_prior'))
        # Difference: home minus away for each prior
        for col in expected_cols:
            hc = col
            ac = f"{col}_away_prior"
            if hc in feat.columns and ac in feat.columns:
                feat[f'd_{col}_prior'] = feat[hc] - feat[ac]
    if not elo.empty:
        feat = feat.merge(elo[['game_id','home_prob']], on='game_id', how='left')
    if not odds.empty:
        # Use PFR sportsbook if present
        odds_pfr = odds[odds['sportsbook']=='pfr'][['game_id','close_spread_home','close_total']]
        feat = feat.merge(odds_pfr, on='game_id', how='left')

    # Target: margin (home - away)
    scores = games[['game_id','home_score','away_score']].copy()
    scores['margin'] = scores['home_score'] - scores['away_score']
    feat = feat.merge(scores[['game_id','margin']], on='game_id', how='left')

    # Drop games missing target
    feat = feat.dropna(subset=['margin'])
    return feat
