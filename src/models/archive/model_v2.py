"""
NFL 2025 v2 Hybrid Model with Momentum & Trend Features

Extends v1 with:
- Exponential Moving Averages (EMA) - weight recent games higher
- Trend slopes - is team improving or declining?
- Volatility measures - consistency of performance
- Season-to-date ratios - early vs recent form comparison
- All with non-linear models (RandomForest, XGBoost, LightGBM)

Expected: 15-25% accuracy improvement over v1 via better feature set
"""

from __future__ import annotations

import math
import json
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler

# Optional: XGBoost and LightGBM
try:
    import xgboost as xgb
except Exception:
    xgb = None

try:
    import lightgbm as lgb
except Exception:
    lgb = None

try:
    import requests
except Exception:
    requests = None

try:
    import joblib
except Exception:
    joblib = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKBOOK = PROJECT_ROOT / "data" / "nfl_2025_model_data_with_moneylines.xlsx"


def implied_prob(mlv: float) -> float:
    """Convert American moneyline to implied probability (vigged)."""
    mlv = float(mlv)
    if mlv < 0:
        return (-mlv) / ((-mlv) + 100.0)
    return 100.0 / (mlv + 100.0)


_TEAM_CODE_TO_NAME = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GNB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KAN": "Kansas City Chiefs", "LAC": "Los Angeles Chargers", "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings", "NWE": "New England Patriots",
    "NOR": "New Orleans Saints", "NYG": "New York Giants", "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SFO": "San Francisco 49ers",
    "SEA": "Seattle Seahawks", "TAM": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders", "LVR": "Las Vegas Raiders",
}


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _extract_market_probability(close_ml_home: float, close_ml_away: float) -> float:
    """Extract no-vig home win probability from moneylines."""
    ph = implied_prob(close_ml_home)
    pa = implied_prob(close_ml_away)
    return ph / (ph + pa)


@dataclass
class ModelArtifacts:
    features: List[str]
    window: int
    means: pd.Series
    sigma_margin: float
    m_margin: Any
    m_total: Any
    model_type: str = "randomforest"
    scaler_margin: Optional[Any] = None
    scaler_total: Optional[Any] = None


class NFLHybridModelV2:
    """Enhanced model with momentum/trend features and non-linear regression."""
    
    def __init__(self, workbook_path: str, window: int = 8, model_type: str = "randomforest") -> None:
        self.workbook_path = workbook_path
        self.window = int(window)
        self.model_type = model_type.lower()
        
        if self.model_type not in ["ridge", "xgboost", "lightgbm", "randomforest"]:
            raise ValueError(f"Unknown model_type: {model_type}")
        
        self._artifacts: Optional[ModelArtifacts] = None
        self._tg: Optional[pd.DataFrame] = None
        self._X_cols: Optional[List[str]] = None
        self._fit_report: Optional[Dict[str, Any]] = None

    def load_workbook(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        games = pd.read_excel(self.workbook_path, sheet_name="games")
        team_games = pd.read_excel(self.workbook_path, sheet_name="team_games")
        odds = pd.read_excel(self.workbook_path, sheet_name="odds")
        return games, team_games, odds

    def _prepare_team_games_with_week(self) -> pd.DataFrame:
        games, team_games, _ = self.load_workbook()
        g = games[["game_id", "week"]].copy()
        g["week"] = pd.to_numeric(g["week"], errors="coerce").astype("Int64")
        tg = team_games.merge(g, on="game_id", how="left", validate="many_to_one")
        if "is_home (0/1)" in tg.columns:
            tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)
        else:
            raise ValueError("team_games sheet missing required column: 'is_home (0/1)'")
        tg["week"] = pd.to_numeric(tg["week"], errors="coerce")
        return tg

    @staticmethod
    def _candidate_features(team_games: pd.DataFrame) -> List[str]:
        candidates = [
            "plays", "seconds_per_play", "yards_per_play", "yards_per_play_allowed",
            "rush_att", "rush_yds", "rush_ypa", "rush_td",
            "turnovers_give", "turnovers_take",
            "ints_thrown", "ints_got", "fumbles_lost", "fumbles_recovered",
            "sacks_allowed", "sacks_made",
            "pressures_made", "pressures_allowed",
            "hurries_made", "hurries_allowed",
            "blitzes_sent", "blitzes_faced",
            "penalties", "penalty_yards",
            "opp_first_downs", "opp_first_downs_rush", "opp_first_downs_pass", "opp_first_downs_pen",
            "opp_3d_att", "opp_3d_conv", "opp_3d_pct",
            "opp_4d_att", "opp_4d_conv", "opp_4d_pct",
            "punts", "punt_yards", "punt_yards_per_punt", "punts_blocked",
        ]
        return [c for c in candidates if c in team_games.columns]

    def _add_rolling_features(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        """Add rolling averages (same as v0/v1)."""
        out = df.sort_values(["team", "week", "game_id"]).copy()
        w = self.window
        for c in cols:
            out[f"{c}_pre{w}"] = (
                out.groupby("team")[c]
                .shift(1)
                .rolling(window=w, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )
        return out

    def _add_momentum_features(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        """Add EMA, trend, volatility, and season-to-date features."""
        out = df.copy()
        w = self.window
        
        for c in cols:
            team_group = out.groupby("team")[c].shift(1)  # Shift to avoid leakage
            
            # 1. Exponential Moving Average (EMA) - weight recent games more
            ema = team_group.ewm(span=w, adjust=False).mean()
            out[f"{c}_ema{w}"] = ema
            
            # 2. Trend (slope of last N games)
            def calc_trend(s):
                if len(s) < 2:
                    return 0.0
                x = np.arange(len(s))
                if np.std(x) == 0:
                    return 0.0
                try:
                    slope = np.polyfit(x, s.values, 1)[0]
                    return float(slope)
                except:
                    return 0.0
            
            trend = out.groupby("team")[c].shift(1).rolling(window=w, min_periods=2).apply(calc_trend, raw=False)
            out[f"{c}_trend{w}"] = trend
            
            # 3. Volatility (coefficient of variation)
            rolling_std = out.groupby("team")[c].shift(1).rolling(window=w, min_periods=1).std()
            rolling_mean = out.groupby("team")[c].shift(1).rolling(window=w, min_periods=1).mean()
            cv = rolling_std / (rolling_mean.abs() + 1e-6)  # Avoid division by zero
            out[f"{c}_vol{w}"] = cv
            
            # 4. Season-to-date stats (cumulative average up to current point)
            shifted = out.groupby("team")[c].shift(1)
            cumsum = shifted.cumsum()
            cumcount = out.groupby("team").cumcount()
            season_avg = cumsum / (cumcount + 1)
            out[f"{c}_season_avg"] = season_avg
            
            # 5. Ratio of recent to season performance
            recent_avg = out[f"{c}_pre{w}"]
            ratio = recent_avg / (season_avg.abs() + 1e-6)
            out[f"{c}_recent_ratio"] = ratio.fillna(1.0)
        
        return out

    def _build_model(self, model_type: str) -> Tuple[Any, Optional[StandardScaler]]:
        """Factory method to create model instance."""
        if model_type == "ridge":
            return Ridge(alpha=10.0, random_state=0), None
        elif model_type == "xgboost":
            if xgb is None:
                raise RuntimeError("xgboost not installed. Run: pip install xgboost")
            return xgb.XGBRegressor(
                n_estimators=150,
                max_depth=7,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=0,
                tree_method="hist"
            ), StandardScaler()
        elif model_type == "lightgbm":
            if lgb is None:
                raise RuntimeError("lightgbm not installed. Run: pip install lightgbm")
            return lgb.LGBMRegressor(
                n_estimators=150,
                max_depth=7,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=0,
                verbose=-1
            ), StandardScaler()
        elif model_type == "randomforest":
            return RandomForestRegressor(
                n_estimators=150,
                max_depth=13,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=0,
                n_jobs=-1
            ), StandardScaler()
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def fit(self, train_through_week: int = 14) -> Dict[str, float]:
        """Fit model with momentum features."""
        games, team_games, odds = self.load_workbook()

        g = games[["game_id", "week", "home_team", "away_team", "home_score", "away_score", "neutral_site (0/1)"]].copy()
        g["week"] = pd.to_numeric(g["week"], errors="coerce").astype(int)
        g["neutral_site (0/1)"] = pd.to_numeric(g["neutral_site (0/1)"], errors="coerce").fillna(0).astype(int)
        g["margin_home"] = g["home_score"] - g["away_score"]
        g["total_points"] = g["home_score"] + g["away_score"]
        g["home_win"] = (g["margin_home"] > 0).astype(int)

        tg = team_games.merge(g[["game_id", "week"]], on="game_id", how="left", validate="many_to_one")
        tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)

        feats = self._candidate_features(tg)
        
        # Add rolling features (v0 style)
        tg_roll = self._add_rolling_features(tg, feats)
        
        # Add momentum features (v2 NEW)
        tg_momentum = self._add_momentum_features(tg_roll, feats)
        
        # Collect all feature columns
        pre_cols = [f"{c}_pre{self.window}" for c in feats]
        ema_cols = [f"{c}_ema{self.window}" for c in feats]
        trend_cols = [f"{c}_trend{self.window}" for c in feats]
        vol_cols = [f"{c}_vol{self.window}" for c in feats]
        season_cols = [f"{c}_season_avg" for c in feats]
        ratio_cols = [f"{c}_recent_ratio" for c in feats]

        home_feat = tg_momentum[tg_momentum["is_home (0/1)"] == 1][
            ["game_id", "team"] + pre_cols + ema_cols + trend_cols + vol_cols + season_cols + ratio_cols
        ].rename(columns={"team": "home_team"})
        
        away_feat = tg_momentum[tg_momentum["is_home (0/1)"] == 0][
            ["game_id", "team"] + pre_cols + ema_cols + trend_cols + vol_cols + season_cols + ratio_cols
        ].rename(columns={"team": "away_team"})

        gf = g.merge(home_feat, on=["game_id", "home_team"], how="left").merge(
            away_feat, on=["game_id", "away_team"], how="left", suffixes=("_home", "_away")
        )

        # Build fundamentals delta features
        X_fund = pd.DataFrame(index=gf.index)
        for c in feats:
            # Rolling mean deltas
            X_fund[f"delta_{c}_pre{self.window}"] = (
                gf[f"{c}_pre{self.window}_home"] - gf[f"{c}_pre{self.window}_away"]
            )
            # EMA deltas
            X_fund[f"delta_{c}_ema{self.window}"] = (
                gf[f"{c}_ema{self.window}_home"] - gf[f"{c}_ema{self.window}_away"]
            )
            # Trend deltas
            X_fund[f"delta_{c}_trend{self.window}"] = (
                gf[f"{c}_trend{self.window}_home"] - gf[f"{c}_trend{self.window}_away"]
            )
            # Volatility deltas
            X_fund[f"delta_{c}_vol{self.window}"] = (
                gf[f"{c}_vol{self.window}_home"] - gf[f"{c}_vol{self.window}_away"]
            )
            # Season avg deltas
            X_fund[f"delta_{c}_season_avg"] = (
                gf[f"{c}_season_avg_home"] - gf[f"{c}_season_avg_away"]
            )
            # Recent ratio deltas
            X_fund[f"delta_{c}_recent_ratio"] = (
                gf[f"{c}_recent_ratio_home"] - gf[f"{c}_recent_ratio_away"]
            )
        
        X_fund["neutral_site"] = gf["neutral_site (0/1)"]

        # Market features
        odds_use = odds[[
            "game_id", "close_spread_home", "close_total",
            "open_spread_home", "open_total",
            "close_ml_home", "close_ml_away"
        ]].copy()

        odds_use["imp_p_home"] = odds_use["close_ml_home"].apply(implied_prob)
        odds_use["imp_p_away"] = odds_use["close_ml_away"].apply(implied_prob)
        odds_use["vig_sum"] = odds_use["imp_p_home"] + odds_use["imp_p_away"]
        odds_use["imp_p_home_novig"] = odds_use["imp_p_home"] / odds_use["vig_sum"]

        gf = gf.merge(
            odds_use[["game_id", "close_spread_home", "close_total", "open_spread_home", "open_total", "imp_p_home_novig"]],
            on="game_id",
            how="left"
        )
        X_market = gf[["close_spread_home", "close_total", "open_spread_home", "open_total", "imp_p_home_novig"]].copy()

        X = pd.concat([X_fund, X_market], axis=1)
        self._X_cols = list(X.columns)

        # Filter out games without outcomes to avoid NaNs in targets
        has_outcome = gf["margin_home"].notna() & gf["total_points"].notna()
        gf = gf[has_outcome].copy()
        X = X[has_outcome].copy()

        train_week = int(train_through_week)
        train_mask = gf["week"] <= train_week
        test_mask = gf["week"] >= train_week + 1

        X_train = X.loc[train_mask].copy()
        X_test = X.loc[test_mask].copy()

        means = X_train.mean(numeric_only=True)
        X_train.fillna(means, inplace=True)
        X_test.fillna(means, inplace=True)

        y_margin_train = gf.loc[train_mask, "margin_home"]
        y_margin_test = gf.loc[test_mask, "margin_home"]
        y_total_train = gf.loc[train_mask, "total_points"]
        y_total_test = gf.loc[test_mask, "total_points"]

        sigma = float(y_margin_train.std(ddof=0))
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = 14.0

        m_margin, scaler_margin = self._build_model(self.model_type)
        m_total, scaler_total = self._build_model(self.model_type)

        X_train_scaled = X_train.copy()
        X_test_scaled = X_test.copy()
        if scaler_margin is not None:
            X_train_scaled = scaler_margin.fit_transform(X_train)
            X_test_scaled = scaler_margin.transform(X_test)
            X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
            X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)

        m_margin.fit(X_train_scaled, y_margin_train)
        m_total.fit(X_train_scaled, y_total_train)

        self._artifacts = ModelArtifacts(
            features=feats,
            window=self.window,
            means=means,
            sigma_margin=sigma,
            m_margin=m_margin,
            m_total=m_total,
            model_type=self.model_type,
            scaler_margin=scaler_margin,
            scaler_total=scaler_total,
        )

        self._tg = tg_momentum

        pred_margin = m_margin.predict(X_test_scaled)
        pred_total = m_total.predict(X_test_scaled)

        report = {
            "n_train_games": int(train_mask.sum()),
            "n_test_games": int(test_mask.sum()),
            "n_features": X_train.shape[1],
            "margin_MAE_test": float(np.mean(np.abs(y_margin_test - pred_margin))),
            "total_MAE_test": float(np.mean(np.abs(y_total_test - pred_total))),
            "sigma_margin_train": sigma,
            "model_type": self.model_type,
        }
        self._fit_report = report
        return report

    def save_model(self, path: str) -> None:
        if joblib is None:
            raise RuntimeError("joblib is not available. Install it (pip install joblib) or install scikit-learn.")
        if self._artifacts is None or self._X_cols is None:
            raise RuntimeError("Model not fitted. Call fit() before save_model().")

        payload = {
            "version": "v2",
            "window": self.window,
            "X_cols": self._X_cols,
            "artifacts": self._artifacts,
            "fit_report": self._fit_report,
        }
        joblib.dump(payload, path)

    def load_model(self, path: str) -> None:
        if joblib is None:
            raise RuntimeError("joblib is not available. Install it (pip install joblib) or install scikit-learn.")
        payload = joblib.load(path)

        self.window = int(payload.get("window", self.window))
        self._X_cols = list(payload["X_cols"])
        self._artifacts = payload["artifacts"]
        self._fit_report = payload.get("fit_report")

        self._tg = self._prepare_team_games_with_week()

    def predict_game(
        self,
        home_team: str,
        away_team: str,
        close_spread_home: float,
        close_total: float,
        close_ml_home: float,
        close_ml_away: float,
        as_of_week: int = 19,
    ) -> Dict[str, float]:
        if self._artifacts is None or self._X_cols is None:
            raise RuntimeError("Model not fitted/loaded. Call fit() or load_model() first.")
        
        if self._tg is None:
            self._tg = self._prepare_team_games_with_week()

        A = self._artifacts
        tg = self._tg

        def last_n_means(team_code: str, col_suffix: str, n: int) -> Dict[str, float]:
            """Get last N games stats with feature suffixes."""
            hist = tg[(tg["team"] == team_code) & (tg["week"] < as_of_week)].sort_values(["week", "game_id"]).tail(n)
            result = {}
            for c in A.features:
                # Rolling mean
                col = f"{c}_{col_suffix}"
                result[col] = hist[col].mean() if col in hist.columns else np.nan
            return result

        # Get last N stats for each suffix
        home_stats_pre = last_n_means(home_team, f"pre{A.window}", A.window)
        away_stats_pre = last_n_means(away_team, f"pre{A.window}", A.window)
        
        home_stats_ema = last_n_means(home_team, f"ema{A.window}", A.window)
        away_stats_ema = last_n_means(away_team, f"ema{A.window}", A.window)
        
        home_stats_trend = last_n_means(home_team, f"trend{A.window}", A.window)
        away_stats_trend = last_n_means(away_team, f"trend{A.window}", A.window)
        
        home_stats_vol = last_n_means(home_team, f"vol{A.window}", A.window)
        away_stats_vol = last_n_means(away_team, f"vol{A.window}", A.window)
        
        home_stats_season = last_n_means(home_team, "season_avg", A.window)
        away_stats_season = last_n_means(away_team, "season_avg", A.window)
        
        home_stats_ratio = last_n_means(home_team, "recent_ratio", A.window)
        away_stats_ratio = last_n_means(away_team, "recent_ratio", A.window)

        row: Dict[str, float] = {}
        for c in A.features:
            # All deltas
            row[f"delta_{c}_pre{A.window}"] = float(home_stats_pre.get(f"{c}_pre{A.window}", np.nan) - away_stats_pre.get(f"{c}_pre{A.window}", np.nan))
            row[f"delta_{c}_ema{A.window}"] = float(home_stats_ema.get(f"{c}_ema{A.window}", np.nan) - away_stats_ema.get(f"{c}_ema{A.window}", np.nan))
            row[f"delta_{c}_trend{A.window}"] = float(home_stats_trend.get(f"{c}_trend{A.window}", np.nan) - away_stats_trend.get(f"{c}_trend{A.window}", np.nan))
            row[f"delta_{c}_vol{A.window}"] = float(home_stats_vol.get(f"{c}_vol{A.window}", np.nan) - away_stats_vol.get(f"{c}_vol{A.window}", np.nan))
            row[f"delta_{c}_season_avg"] = float(home_stats_season.get(f"{c}_season_avg", np.nan) - away_stats_season.get(f"{c}_season_avg", np.nan))
            row[f"delta_{c}_recent_ratio"] = float(home_stats_ratio.get(f"{c}_recent_ratio", np.nan) - away_stats_ratio.get(f"{c}_recent_ratio", np.nan))
        
        row["neutral_site"] = 0.0

        ph = implied_prob(close_ml_home)
        pa = implied_prob(close_ml_away)
        vig = ph + pa
        imp_home_novig = ph / vig

        row.update({
            "close_spread_home": close_spread_home,
            "close_total": close_total,
            "open_spread_home": np.nan,
            "open_total": np.nan,
            "imp_p_home_novig": imp_home_novig,
        })

        X_row = pd.DataFrame([row]).reindex(columns=self._X_cols, fill_value=np.nan).fillna(A.means)
        
        if A.scaler_margin is not None:
            X_row_scaled = A.scaler_margin.transform(X_row)
            X_row_scaled = pd.DataFrame(X_row_scaled, columns=X_row.columns, index=X_row.index)
        else:
            X_row_scaled = X_row

        pred_margin_home = A.m_margin.predict(X_row_scaled)[0]
        pred_total = A.m_total.predict(X_row_scaled)[0]

        pred_spread_away = -pred_margin_home

        p_home = norm_cdf(pred_margin_home / A.sigma_margin)
        p_away = 1.0 - p_home

        market_home_p = imp_home_novig
        market_away_p = 1.0 - market_home_p
        market_spread_away = -close_spread_home

        return {
            "pred_spread_away": pred_spread_away,
            "pred_total": pred_total,
            "pred_winprob_home": p_home,
            "pred_winprob_away": p_away,
            "market_spread_away": market_spread_away,
            "market_total": close_total,
            "market_winprob_home_novig": market_home_p,
            "market_winprob_away_novig": market_away_p,
            "edge_spread_points_model_minus_market": pred_spread_away - market_spread_away,
            "edge_total_points_model_minus_market": pred_total - close_total,
            "edge_winprob_away_points_model_minus_market": p_away - market_away_p,
        }


def main():
    import argparse
    import os
    import sys

    p = argparse.ArgumentParser(
        description="NFL 2025 v2 Hybrid Model: momentum features + non-linear models."
    )
    p.add_argument("--model", choices=["ridge", "xgboost", "lightgbm", "randomforest"], default="randomforest",
                   help="Model type to use (default: randomforest)")
    p.add_argument("--home", help="Home team code")
    p.add_argument("--away", help="Away team code")
    p.add_argument("--close_spread_home", type=float, help="Closing spread")
    p.add_argument("--close_total", type=float, help="Closing total")
    p.add_argument("--close_ml_home", type=float, help="Closing home ML")
    p.add_argument("--close_ml_away", type=float, help="Closing away ML")
    p.add_argument("--window", type=int, default=None, help="Rolling window (default: 8)")
    p.add_argument("--train_through_week", type=int, default=None, help="Train through week (default: 14)")
    p.add_argument("--as_of_week", type=int, default=None, help="As of week (default: 19)")
    p.add_argument("--save_model", default=None, help="Save model path")
    p.add_argument("--load_model", default=None, help="Load model path")
    p.add_argument("--json", action="store_true", help="JSON output only")

    args = p.parse_args()

    workbook = DEFAULT_WORKBOOK

    window = args.window or 8
    train_through_week = args.train_through_week or 14
    as_of_week = args.as_of_week or 19

    model = NFLHybridModelV2(workbook_path=workbook, window=window, model_type=args.model)

    fit_report = None
    if args.load_model:
        model.load_model(args.load_model)
        fit_report = model._fit_report
    else:
        fit_report = model.fit(train_through_week=train_through_week)
        if args.save_model:
            model.save_model(args.save_model)

    if args.home and args.away and args.close_spread_home is not None and args.close_total is not None:
        pred = model.predict_game(
            home_team=args.home,
            away_team=args.away,
            close_spread_home=args.close_spread_home,
            close_total=args.close_total,
            close_ml_home=args.close_ml_home or 0.0,
            close_ml_away=args.close_ml_away or 0.0,
            as_of_week=as_of_week,
        )

        if fit_report:
            print("\n=== FIT REPORT ===")
            for k, v in fit_report.items():
                print(f"{k:>24}: {v}")

        print(f"\n=== PREDICTION ({args.model.upper()}) ===")
        print(f"Matchup: {args.away} at {args.home}")
        print(f"\nModel outputs:")
        print(f"  Spread (away line): {pred['pred_spread_away']:+.2f}")
        print(f"  Total:             {pred['pred_total']:.2f}")
        print(f"  Win% (away):        {pred['pred_winprob_away']*100:.1f}%")
        print(f"  Win% (home):        {pred['pred_winprob_home']*100:.1f}%")

        print(f"\nMarket (no-vig) benchmarks:")
        print(f"  Spread (away line): {pred['market_spread_away']:+.2f}")
        print(f"  Total:             {pred['market_total']:.2f}")
        print(f"  Win% (away):        {pred['market_winprob_away_novig']*100:.1f}%")
        print(f"  Win% (home):        {pred['market_winprob_home_novig']*100:.1f}%")

        print(f"\nEdges (model - market):")
        print(f"  Spread points:      {pred['edge_spread_points_model_minus_market']:+.2f}")
        print(f"  Total points:       {pred['edge_total_points_model_minus_market']:+.2f}")
        print(f"  Win% (away) points: {pred['edge_winprob_away_points_model_minus_market']*100:+.1f}%")
    else:
        if fit_report:
            print("\n=== FIT REPORT ===")
            for k, v in fit_report.items():
                print(f"{k:>24}: {v}")


if __name__ == "__main__":
    main()
