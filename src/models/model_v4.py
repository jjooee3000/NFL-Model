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
from typing import Dict, Any, List, Tuple

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
    def __init__(self, workbook_path: Path = DEFAULT_WORKBOOK, model_type: str = "randomforest") -> None:
        self.workbook_path = Path(workbook_path)
        self.model_type = model_type
        self._fit_report: Dict[str, Any] | None = None

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        games = pd.read_excel(self.workbook_path, sheet_name="games")
        team_stats = pd.read_excel(self.workbook_path, sheet_name="pfr_team_stats_historical")
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
        return games, team_stats

    def build_features(self, games: pd.DataFrame, stats: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        # Basic required columns
        required = ["season", "home_team", "away_team", "home_score", "away_score"]
        for c in required:
            if c not in games.columns:
                raise ValueError(f"games sheet missing required column: {c}")
        
        # Prepare targets
        margin = pd.to_numeric(games["home_score"], errors="coerce") - pd.to_numeric(games["away_score"], errors="coerce")
        total = pd.to_numeric(games["home_score"], errors="coerce") + pd.to_numeric(games["away_score"], errors="coerce")
        
        # Merge team-season stats
        s_home = stats.rename(columns={col: f"home_{col}" for col in stats.columns if col not in ["team", "season"]})
        s_away = stats.rename(columns={col: f"away_{col}" for col in stats.columns if col not in ["team", "season"]})
        
        df = games.copy()
        df = df.merge(stats, left_on=["home_team", "season"], right_on=["team", "season"], how="left")
        df = df.merge(stats, left_on=["away_team", "season"], right_on=["team", "season"], how="left", suffixes=("_home","_away"))
        
        # Build differential features for numeric columns
        home_cols = [c for c in df.columns if c.endswith("_home")]
        away_cols = [c for c in df.columns if c.endswith("_away")]
        # Align pairs by base column name
        diff_features: List[str] = []
        for hc in home_cols:
            base = hc[:-5]  # remove _home
            ac = base + "_away"
            if ac in df.columns:
                diff = pd.to_numeric(df[hc], errors="coerce") - pd.to_numeric(df[ac], errors="coerce")
                df[f"diff_{base}"] = diff
                diff_features.append(f"diff_{base}")
        
        # Feature matrix
        X = df[diff_features].fillna(0.0)
        return X, margin, total

    def fit(self) -> Dict[str, Any]:
        games, stats = self.load_data()
        
        # Train/test split by season
        X, y_margin, y_total = self.build_features(games, stats)
        # Filter valid targets
        valid = (~pd.isna(y_margin)) & (~pd.isna(y_total))
        X = X[valid]
        y_margin = y_margin[valid]
        y_total = y_total[valid]
        # Train/test split
        seasons = games.loc[valid, "season"].values
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
