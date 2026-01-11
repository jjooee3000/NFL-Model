"""
NFL Model v4: Train on historical games using PFR team stats (2020-2025)

- Loads integrated workbook with standardized 'games' sheet (2020-2025)
- Merges team-season PFR stats for home/away
- Builds differential features (home - away)
- Trains RandomForest for margin and total
- Evaluates on 2025 as test; trains on 2020-2024
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKBOOK = PROJECT_ROOT / "data" / "nfl_model_data_historical_integrated.xlsx"


@dataclass
class FitReport:
    n_features: int
    margin_MAE_test: float
    total_MAE_test: float
    margin_MAE_train: float
    total_MAE_train: float


class NFLModelV4:
    def __init__(self, workbook_path: Path = DEFAULT_WORKBOOK, model_type: str = "randomforest", sqlite_path: Optional[Path] = None) -> None:
        self.workbook_path = Path(workbook_path) if workbook_path else DEFAULT_WORKBOOK
        self.sqlite_path = Path(sqlite_path) if sqlite_path else None
        self.model_type = model_type
        self._fit_report: Dict[str, Any] | None = None

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if self.sqlite_path and self.sqlite_path.exists():
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            games = pd.read_sql_query("SELECT * FROM games", conn)
            # Load both offensive and defensive stats
            try:
                team_stats_off = pd.read_sql_query("SELECT * FROM pfr_team_stats_historical", conn)
            except Exception:
                team_stats_off = pd.read_sql_query("SELECT * FROM pfr_team_stats", conn)
            
            try:
                team_stats_def = pd.read_sql_query("SELECT * FROM pfr_team_defense", conn)
            except Exception:
                team_stats_def = pd.DataFrame()
            
            # Merge offense and defense stats
            if not team_stats_def.empty:
                team_stats = team_stats_off.merge(team_stats_def, on=["team", "season"], how="outer")
            else:
                team_stats = team_stats_off
            
            # Team gamelogs for momentum features
            try:
                gamelogs = pd.read_sql_query("SELECT * FROM pfr_team_gamelogs", conn)
            except Exception:
                gamelogs = pd.DataFrame()
            conn.close()
        else:
            games = pd.read_excel(self.workbook_path, sheet_name="games")
            team_stats = pd.read_excel(self.workbook_path, sheet_name="pfr_team_stats_historical")
            # Historical workbook may not contain gamelogs; fallback to empty
            try:
                gamelogs = pd.read_excel(self.workbook_path, sheet_name="team_gamelogs")
            except Exception:
                gamelogs = pd.DataFrame()
        # Normalize team code column name
        if "team" not in team_stats.columns:
            # Attempt alternative columns
            for alt in ["Team", "TEAM"]:
                if alt in team_stats.columns:
                    team_stats = team_stats.rename(columns={alt: "team"})
                    break
        # Ensure numeric types for stats
        num_cols = team_stats.select_dtypes(include=[np.number]).columns
        team_stats[num_cols] = team_stats[num_cols].apply(pd.to_numeric, errors="coerce")
        # Normalize gamelogs
        if not gamelogs.empty:
            # Standardize column names to expected schema
            cols = {c: c.lower() for c in gamelogs.columns}
            gamelogs = gamelogs.rename(columns=cols)
            # Common fields
            if "year" in gamelogs.columns and "season" not in gamelogs.columns:
                gamelogs = gamelogs.rename(columns={"year": "season"})
            if "week_num" in gamelogs.columns:
                gamelogs = gamelogs.rename(columns={"week_num": "week"})
            # Ensure numeric types on relevant columns
            for c in ["week", "pts_off", "pts_def", "yards_off", "pass_yds_off", "rush_yds_off", "to_off",
                      "yards_def", "pass_yds_def", "rush_yds_def", "to_def", "exp_pts_off", "exp_pts_def", "exp_pts_st"]:
                if c in gamelogs.columns:
                    gamelogs[c] = pd.to_numeric(gamelogs[c], errors="coerce")
        return games, team_stats, gamelogs

    def build_features(self, games: pd.DataFrame, stats: pd.DataFrame, gamelogs: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        # Basic required columns
        required = ["season", "home_team", "away_team", "home_score", "away_score"]
        for c in required:
            if c not in games.columns:
                raise ValueError(f"games sheet missing required column: {c}")
        
        df = games.copy()
        
        # Rename stats columns to distinguish home vs away
        # Select all columns except "team" and "season" for prefixing
        stat_cols_to_prefix = [c for c in stats.columns if c not in ["team", "season"]]
        
        # Merge home team stats
        stats_home = stats[["team", "season"] + stat_cols_to_prefix].copy()
        stats_home.columns = ["team", "season"] + [f"home_{c}" for c in stat_cols_to_prefix]
        df = df.merge(stats_home, left_on=["home_team", "season"], right_on=["team", "season"], how="left")
        df = df.drop(columns=["team"], errors="ignore")
        
        # Merge away team stats
        stats_away = stats[["team", "season"] + stat_cols_to_prefix].copy()
        stats_away.columns = ["team", "season"] + [f"away_{c}" for c in stat_cols_to_prefix]
        df = df.merge(stats_away, left_on=["away_team", "season"], right_on=["team", "season"], how="left")
        df = df.drop(columns=["team"], errors="ignore")
        
        # Prepare targets aligned to df index
        margin = pd.to_numeric(df["home_score"], errors="coerce") - pd.to_numeric(df["away_score"], errors="coerce")
        total = pd.to_numeric(df["home_score"], errors="coerce") + pd.to_numeric(df["away_score"], errors="coerce")
        
        # Build differential features for all stat columns
        diff_features: List[str] = []
        
        for stat_col in stat_cols_to_prefix:
            hc = f"home_{stat_col}"
            ac = f"away_{stat_col}"
            if hc in df.columns and ac in df.columns:
                h_val = pd.to_numeric(df[hc], errors="coerce")
                a_val = pd.to_numeric(df[ac], errors="coerce")
                diff = h_val - a_val
                df[f"diff_{stat_col}"] = diff
                diff_features.append(f"diff_{stat_col}")
        
        # Momentum features from team gamelogs
        if not gamelogs.empty and {"team", "season", "week"}.issubset(set(gamelogs.columns)):
            gl = gamelogs.copy()
            gl = gl.sort_values(["team", "season", "week"])  # ensure order
            # Compute rolling means with lookback windows and shift to avoid leakage
            base_cols = [c for c in ["pts_off", "pts_def", "yards_off", "pass_yds_off", "rush_yds_off", "to_off",
                                     "yards_def", "pass_yds_def", "rush_yds_def", "to_def", "exp_pts_off", "exp_pts_def", "exp_pts_st"] if c in gl.columns]
            for win in [4, 8]:
                for c in base_cols:
                    roll_name = f"r{win}_{c}"
                    gl[roll_name] = gl.groupby(["team", "season"])[c].transform(lambda s: s.rolling(win, min_periods=1).mean().shift(1))
            # Keep only keys + rolling cols
            keep_cols = ["team", "season", "week"] + [f"r{win}_{c}" for win in [4, 8] for c in base_cols]
            gl_feat = gl[keep_cols].drop_duplicates(subset=["team", "season", "week"])  # ensure unique keys
            # Merge onto games for home and away
            df = df.merge(gl_feat.add_prefix("home_"), left_on=["home_team", "season", "week"], right_on=["home_team", "home_season", "home_week"], how="left")
            df = df.merge(gl_feat.add_prefix("away_"), left_on=["away_team", "season", "week"], right_on=["away_team", "away_season", "away_week"], how="left")
            # Build diffs for momentum features
            for c in base_cols:
                for win in [4, 8]:
                    r_col = f"r{win}_{c}"
                    hc = f"home_{r_col}"
                    ac = f"away_{r_col}"
                    if hc in df.columns and ac in df.columns:
                        df[f"diff_{r_col}"] = pd.to_numeric(df[hc], errors="coerce") - pd.to_numeric(df[ac], errors="coerce")
                        diff_features.append(f"diff_{r_col}")

        X = df[diff_features].fillna(0.0)
        return X, margin, total

    def fit(self) -> Dict[str, Any]:
        games, stats, gamelogs = self.load_data()
        
        # Train/test split by season
        X, y_margin, y_total = self.build_features(games, stats, gamelogs)
        # Filter valid targets
        valid = (~pd.isna(y_margin)) & (~pd.isna(y_total))
        X = X[valid.values]
        y_margin = y_margin[valid.values]
        y_total = y_total[valid.values]
        # Train/test split
        seasons_all = games.loc[X.index, "season"].values
        seasons = seasons_all
        train_idx = seasons <= 2024
        test_idx = seasons == 2025
        X_train, X_test = X[train_idx], X[test_idx]
        ym_train, ym_test = y_margin[train_idx], y_margin[test_idx]
        yt_train, yt_test = y_total[train_idx], y_total[test_idx]
        
        m_margin = RandomForestRegressor(n_estimators=200, random_state=42)
        m_total = RandomForestRegressor(n_estimators=200, random_state=42)
        m_margin.fit(X_train, ym_train)
        m_total.fit(X_train, yt_train)
        
        pred_m_test = m_margin.predict(X_test)
        pred_t_test = m_total.predict(X_test)
        
        report = {
            "n_features": X.shape[1],
            "margin_MAE_test": float(mean_absolute_error(ym_test, pred_m_test)),
            "total_MAE_test": float(mean_absolute_error(yt_test, pred_t_test)),
            "margin_MAE_train": float(mean_absolute_error(ym_train, m_margin.predict(X_train))),
            "total_MAE_train": float(mean_absolute_error(yt_train, m_total.predict(X_train))),
        }
        self._fit_report = report
        return report
