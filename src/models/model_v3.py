"""
NFL Model v3: Fixed Momentum Features + Expanded Data Sources

Key improvements over v2:
1. FIX: Store actual feature columns (230+) instead of base 38 features
2. ADD: points_for, points_against to candidate features
3. ENHANCE: Momentum features now properly integrated and tracked
4. ROBUST: Better NaN handling for momentum features
"""

from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
except ImportError as e:
    raise ImportError(f"Missing required package: {e}")

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKBOOK = PROJECT_ROOT / "data" / "nfl_2025_model_data_with_moneylines.xlsx"


def implied_prob(odds: float) -> float:
    """Convert American odds to implied probability."""
    if pd.isna(odds):
        return np.nan
    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    else:
        return (-odds) / (-odds + 100.0)


@dataclass
class ModelArtifacts:
    features: List[str]  # All feature column names (including momentum)
    window: int
    means: pd.Series
    sigma_margin: float
    m_margin: Any
    m_total: Any
    model_type: str = "randomforest"
    scaler_margin: Optional[Any] = None
    scaler_total: Optional[Any] = None


class NFLHybridModelV3:
    """Enhanced model with working momentum features and expanded data sources."""

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
        """v3: Expanded candidate features including points_for and points_against"""
        candidates = [
            # Score-based metrics (NEW in v3)
            "points_for", "points_against",
            # Play-level metrics
            "plays", "seconds_per_play", "yards_per_play", "yards_per_play_allowed",
            # Rushing
            "rush_att", "rush_yds", "rush_ypa", "rush_td",
            # Turnovers
            "turnovers_give", "turnovers_take",
            "ints_thrown", "ints_got", "fumbles_lost", "fumbles_recovered",
            # Pass rush
            "sacks_allowed", "sacks_made",
            "pressures_made", "pressures_allowed",
            "hurries_made", "hurries_allowed",
            # Blitzes
            "blitzes_sent", "blitzes_faced",
            # Penalties
            "penalties", "penalty_yards",
            # Opponent efficiency
            "opp_first_downs", "opp_first_downs_rush", "opp_first_downs_pass", "opp_first_downs_pen",
            "opp_3d_att", "opp_3d_conv", "opp_3d_pct",
            "opp_4d_att", "opp_4d_conv", "opp_4d_pct",
            # Special teams
            "punts", "punt_yards", "punt_yards_per_punt", "punts_blocked",
        ]
        return [c for c in candidates if c in team_games.columns]

    def _add_rolling_features(self, tg: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """Add N-game rolling averages."""
        out = tg.copy()
        for c in feature_cols:
            if c not in tg.columns:
                continue
            grp = tg.groupby("team")[c].shift(1).rolling(self.window, min_periods=1).mean()
            out[f"{c}_pre{self.window}"] = grp.values
        return out

    def _add_momentum_features(self, tg: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """
        v3: Enhanced momentum features with better NaN handling.
        
        For each base feature, creates:
        - EMA: Exponential moving average (emphasizes recent games)
        - Trend: Linear slope of recent games
        - Volatility: Coefficient of variation
        - Season avg: Cumulative average from start of season
        - Recent ratio: Recent avg / Season avg ratio
        """
        out = tg.copy()

        for c in feature_cols:
            if c not in tg.columns:
                continue

            w = self.window
            grp = tg.groupby("team")[c].shift(1)

            # EMA: Exponential weight recent games more
            ema = grp.rolling(window=w, min_periods=1).mean()
            ema_exp = grp.ewm(span=w, adjust=False, min_periods=1).mean()
            out[f"{c}_ema{w}"] = ema_exp.values

            # Trend: Linear slope of recent values
            def slope(x):
                if len(x) < 2:
                    return np.nan
                try:
                    z = np.polyfit(range(len(x)), x.dropna(), 1)
                    return z[0]
                except:
                    return np.nan

            trend = grp.rolling(window=w, min_periods=2).apply(slope, raw=False)
            out[f"{c}_trend{w}"] = trend.values

            # Volatility: Coefficient of variation
            vol_mean = grp.rolling(window=w, min_periods=1).mean()
            vol_std = grp.rolling(window=w, min_periods=1).std()
            cv = (vol_std / vol_mean).replace([np.inf, -np.inf], np.nan)
            out[f"{c}_vol{w}"] = cv.values

            # Season-to-date cumulative average
            season_avg = grp.groupby(grp.index.get_level_values(0)).cumsum() / (grp.groupby(grp.index.get_level_values(0)).cumcount() + 1)
            # Better approach: cumulative mean from start of season
            season_avg = grp.expanding(min_periods=1).mean()
            out[f"{c}_season_avg"] = season_avg.values

            # Recent vs Season ratio (identify form changes)
            recent = grp.rolling(window=w, min_periods=1).mean()
            ratio = recent / season_avg
            ratio = ratio.replace([np.inf, -np.inf], 1.0).fillna(1.0)
            out[f"{c}_recent_ratio"] = ratio.values

        return out

    def _build_model(self, model_type: str = "randomforest") -> Tuple[Any, Optional[Any]]:
        """Build and return model + optional scaler."""
        scaler = None

        if model_type == "ridge":
            m = Ridge(alpha=1.0, random_state=42, max_iter=10000)
        elif model_type == "randomforest":
            m = RandomForestRegressor(
                n_estimators=100,
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
                verbose=0,
            )
        elif model_type == "xgboost":
            try:
                from xgboost import XGBRegressor
                m = XGBRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    verbosity=0,
                )
                scaler = StandardScaler()
            except ImportError:
                raise ImportError("xgboost not installed. Install with: pip install xgboost")
        elif model_type == "lightgbm":
            try:
                from lightgbm import LGBMRegressor
                m = LGBMRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    verbose=-1,
                )
                scaler = StandardScaler()
            except ImportError:
                raise ImportError("lightgbm not installed. Install with: pip install lightgbm")
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        return m, scaler

    def fit(self, train_through_week: int = 14) -> Dict[str, Any]:
        """Fit the model with momentum and expanded features."""

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

        # Add momentum features (v3: fixed and enhanced)
        tg_momentum = self._add_momentum_features(tg_roll, feats)

        # Collect all feature columns (THE FIX: store actual columns, not just base names)
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

        # Build delta features for all momentum types
        X_fund = pd.DataFrame(index=gf.index)
        for c in feats:
            X_fund[f"delta_{c}_pre{self.window}"] = (
                gf[f"{c}_pre{self.window}_home"] - gf[f"{c}_pre{self.window}_away"]
            )
            X_fund[f"delta_{c}_ema{self.window}"] = (
                gf[f"{c}_ema{self.window}_home"] - gf[f"{c}_ema{self.window}_away"]
            )
            X_fund[f"delta_{c}_trend{self.window}"] = (
                gf[f"{c}_trend{self.window}_home"] - gf[f"{c}_trend{self.window}_away"]
            )
            X_fund[f"delta_{c}_vol{self.window}"] = (
                gf[f"{c}_vol{self.window}_home"] - gf[f"{c}_vol{self.window}_away"]
            )
            X_fund[f"delta_{c}_season_avg"] = (
                gf[f"{c}_season_avg_home"] - gf[f"{c}_season_avg_away"]
            )
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
        
        # v3 FIX: Store the actual feature column names, not just base feature names
        self._X_cols = list(X.columns)

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

        # v3 FIX: Store actual feature column names from X_train, not just base feature names
        self._artifacts = ModelArtifacts(
            features=self._X_cols,  # All 300+ feature columns
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
            "version": "v3",
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
        self.window = payload["window"]
        self._X_cols = payload["X_cols"]
        self._artifacts = payload["artifacts"]
        self._fit_report = payload["fit_report"]

    def predict_game(self, away_team: str, home_team: str, week: int = None) -> Dict[str, Any]:
        """Make prediction for a specific game."""
        if self._artifacts is None:
            raise RuntimeError("Model not fitted. Call fit() or load_model() first.")

        # ... prediction logic would go here ...
        # For now, return placeholder
        return {
            "away_team": away_team,
            "home_team": home_team,
            "spread_away": 0.0,
            "total": 0.0,
            "win_prob_away": 50.0,
            "win_prob_home": 50.0,
        }


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Train NFL prediction model v3")
    parser.add_argument("--model", type=str, default="randomforest", help="Model type: ridge, xgboost, lightgbm, randomforest")
    parser.add_argument("--train-week", type=int, default=14, help="Train through week N")
    args = parser.parse_args()

    workbook = DEFAULT_WORKBOOK

    model = NFLHybridModelV3(workbook_path=workbook, window=8, model_type=args.model)

    print(f"\n{'='*80}")
    print(f"TRAINING MODEL_V3 (RandomForest with FIXED MOMENTUM FEATURES)")
    print(f"{'='*80}\n")

    report = model.fit(train_through_week=args.train_week)

    print("\n=== FIT REPORT ===")
    for k, v in report.items():
        print(f"{k:30s}: {v}")

    print(f"\n{'='*80}")
