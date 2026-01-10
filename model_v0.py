\
"""
NFL 2025 v0 Hybrid Model (Fundamentals + Market Inputs)

What it does
------------
- Trains on 2025 regular season (workbook tabs: games, team_games, odds)
- Uses rolling last-N (default 8) "pregame" team features (shifted by 1 game to avoid leakage)
- Builds game-level deltas (home - away) and adds market inputs:
    close_spread_home, close_total, open_spread_home, open_total,
    implied home win probability (no-vig) from moneylines
- Outputs: spread (away line), total, and win probabilities coherent with predicted margin

Operational modes
-----------------
1) Fit + predict (default):
   python model_v0.py --workbook ... [game args...]

2) Fit once and save artifacts:
   python model_v0.py --workbook ... --save_model artifacts.joblib [game args...]

3) Load artifacts and predict without refitting:
   python model_v0.py --workbook ... --load_model artifacts.joblib [game args...]

Notes
-----
- This is a v0 baseline: regularized linear models, time-respecting split, mean imputation.
- Win probability is derived coherently from predicted margin using a normal approximation
  with sigma estimated from the training set margins.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression

try:
    import joblib
except Exception as e:  # pragma: no cover
    joblib = None


def implied_prob(mlv: float) -> float:
    """Convert American moneyline to implied probability (vigged)."""
    mlv = float(mlv)
    if mlv < 0:
        return (-mlv) / ((-mlv) + 100.0)
    return 100.0 / (mlv + 100.0)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class ModelArtifacts:
    features: List[str]
    window: int
    means: pd.Series
    sigma_margin: float
    m_margin: Ridge
    m_total: Ridge


class NFLHybridModelV0:
    def __init__(self, workbook_path: str, window: int = 8) -> None:
        self.workbook_path = workbook_path
        self.window = int(window)

        self._artifacts: Optional[ModelArtifacts] = None
        self._tg: Optional[pd.DataFrame] = None
        self._X_cols: Optional[List[str]] = None
        self._fit_report: Optional[Dict[str, Any]] = None

    # ----------------------------
    # IO
    # ----------------------------
    def load_workbook(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        games = pd.read_excel(self.workbook_path, sheet_name="games")
        team_games = pd.read_excel(self.workbook_path, sheet_name="team_games")
        odds = pd.read_excel(self.workbook_path, sheet_name="odds")
        return games, team_games, odds

    def _prepare_team_games_with_week(self) -> pd.DataFrame:
        """Load and store team_games with a reliable week column merged from games."""
        games, team_games, _ = self.load_workbook()
        g = games[["game_id", "week"]].copy()
        g["week"] = pd.to_numeric(g["week"], errors="coerce").astype("Int64")

        tg = team_games.merge(g, on="game_id", how="left", validate="many_to_one")
        if "is_home (0/1)" in tg.columns:
            tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)
        else:
            raise ValueError("team_games sheet missing required column: 'is_home (0/1)'")

        # Ensure expected columns exist
        tg["week"] = pd.to_numeric(tg["week"], errors="coerce")
        return tg

    # ----------------------------
    # Feature definitions
    # ----------------------------
    @staticmethod
    def _candidate_features(team_games: pd.DataFrame) -> List[str]:
        candidates = [
            "plays","seconds_per_play",
            "yards_per_play","yards_per_play_allowed",
            "rush_att","rush_yds","rush_ypa","rush_td",
            "turnovers_give","turnovers_take",
            "ints_thrown","ints_got","fumbles_lost","fumbles_recovered",
            "sacks_allowed","sacks_made",
            "pressures_made","pressures_allowed",
            "hurries_made","hurries_allowed",
            "blitzes_sent","blitzes_faced",
            "penalties","penalty_yards",
            "opp_first_downs","opp_first_downs_rush","opp_first_downs_pass","opp_first_downs_pen",
            "opp_3d_att","opp_3d_conv","opp_3d_pct",
            "opp_4d_att","opp_4d_conv","opp_4d_pct",
            "punts","punt_yards","punt_yards_per_punt","punts_blocked",
        ]
        return [c for c in candidates if c in team_games.columns]

    def _add_rolling_features(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        out = df.sort_values(["team","week","game_id"]).copy()
        w = self.window
        for c in cols:
            out[f"{c}_pre{w}"] = (
                out.groupby("team")[c]
                   .shift(1)  # no leakage: only prior games
                   .rolling(window=w, min_periods=1)
                   .mean()
                   .reset_index(level=0, drop=True)
            )
        return out

    # ----------------------------
    # Fit / Save / Load
    # ----------------------------
    def fit(self, train_through_week: int = 14) -> Dict[str, float]:
        games, team_games, odds = self.load_workbook()

        # Targets from games table
        g = games[["game_id","week","home_team","away_team","home_score","away_score","neutral_site (0/1)"]].copy()
        g["week"] = pd.to_numeric(g["week"], errors="coerce").astype(int)
        g["neutral_site (0/1)"] = pd.to_numeric(g["neutral_site (0/1)"], errors="coerce").fillna(0).astype(int)
        g["margin_home"] = g["home_score"] - g["away_score"]
        g["total_points"] = g["home_score"] + g["away_score"]
        g["home_win"] = (g["margin_home"] > 0).astype(int)

        # Attach week to team_games
        tg = team_games.merge(g[["game_id","week"]], on="game_id", how="left", validate="many_to_one")
        tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)

        feats = self._candidate_features(tg)
        tg_roll = self._add_rolling_features(tg, feats)
        pre_cols = [f"{c}_pre{self.window}" for c in feats]

        home_feat = tg_roll[tg_roll["is_home (0/1)"]==1][["game_id","team"] + pre_cols].rename(columns={"team":"home_team"})
        away_feat = tg_roll[tg_roll["is_home (0/1)"]==0][["game_id","team"] + pre_cols].rename(columns={"team":"away_team"})

        gf = g.merge(home_feat, on=["game_id","home_team"], how="left").merge(
            away_feat, on=["game_id","away_team"], how="left", suffixes=("_home","_away")
        )

        # Fundamentals delta features (home - away)
        X_fund = pd.DataFrame(index=gf.index)
        for c in feats:
            X_fund[f"delta_{c}_pre{self.window}"] = gf[f"{c}_pre{self.window}_home"] - gf[f"{c}_pre{self.window}_away"]
        X_fund["neutral_site"] = gf["neutral_site (0/1)"]

        # Market features from odds
        odds_use = odds[[
            "game_id","close_spread_home","close_total",
            "open_spread_home","open_total",
            "close_ml_home","close_ml_away"
        ]].copy()

        odds_use["imp_p_home"] = odds_use["close_ml_home"].apply(implied_prob)
        odds_use["imp_p_away"] = odds_use["close_ml_away"].apply(implied_prob)
        odds_use["vig_sum"] = odds_use["imp_p_home"] + odds_use["imp_p_away"]
        odds_use["imp_p_home_novig"] = odds_use["imp_p_home"] / odds_use["vig_sum"]

        gf = gf.merge(
            odds_use[["game_id","close_spread_home","close_total","open_spread_home","open_total","imp_p_home_novig"]],
            on="game_id",
            how="left"
        )
        X_market = gf[["close_spread_home","close_total","open_spread_home","open_total","imp_p_home_novig"]].copy()

        # Hybrid matrix
        X = pd.concat([X_fund, X_market], axis=1)
        self._X_cols = list(X.columns)

        # Time-respecting split
        train_mask = gf["week"] <= int(train_through_week)
        test_mask = gf["week"] >= int(train_through_week + 1)

        X_train = X.loc[train_mask].copy()
        X_test = X.loc[test_mask].copy()

        means = X_train.mean(numeric_only=True)
        X_train = X_train.fillna(means)
        X_test = X_test.fillna(means)

        y_margin_train, y_margin_test = gf.loc[train_mask,"margin_home"], gf.loc[test_mask,"margin_home"]
        y_total_train, y_total_test = gf.loc[train_mask,"total_points"], gf.loc[test_mask,"total_points"]
        y_win_train = gf.loc[train_mask,"home_win"]

        m_margin = Ridge(alpha=10.0, random_state=0).fit(X_train, y_margin_train)
        m_total = Ridge(alpha=10.0, random_state=0).fit(X_train, y_total_train)

        # Margin volatility for prob mapping
        sigma = float(gf.loc[train_mask, "margin_home"].std(ddof=0))
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = 14.0

        # Optional: fit logistic win model (not used for final prob in v0 output)
        _ = LogisticRegression(max_iter=4000).fit(X_train, y_win_train)

        self._artifacts = ModelArtifacts(
            features=feats,
            window=self.window,
            means=means,
            sigma_margin=sigma,
            m_margin=m_margin,
            m_total=m_total,
        )

        # Store team_games with week for scoring
        self._tg = tg

        pred_margin = m_margin.predict(X_test)
        pred_total = m_total.predict(X_test)

        report = {
            "n_train_games": int(train_mask.sum()),
            "n_test_games": int(test_mask.sum()),
            "n_features": int(X_train.shape[1]),
            "margin_MAE_test": float(np.mean(np.abs(y_margin_test - pred_margin))),
            "total_MAE_test": float(np.mean(np.abs(y_total_test - pred_total))),
            "sigma_margin_train": float(sigma),
        }
        self._fit_report = report
        return report

    def save_model(self, path: str) -> None:
        """Save fitted artifacts to disk (joblib). You still need the workbook to score games (for last-N form)."""
        if joblib is None:
            raise RuntimeError("joblib is not available. Install it (pip install joblib) or install scikit-learn.")
        if self._artifacts is None or self._X_cols is None:
            raise RuntimeError("Model not fitted. Call fit() before save_model().")

        payload = {
            "version": "v0",
            "window": self.window,
            "X_cols": self._X_cols,
            "artifacts": self._artifacts,
            "fit_report": self._fit_report,
        }
        joblib.dump(payload, path)

    def load_model(self, path: str) -> None:
        """Load fitted artifacts from disk (joblib)."""
        if joblib is None:
            raise RuntimeError("joblib is not available. Install it (pip install joblib) or install scikit-learn.")
        payload = joblib.load(path)

        self.window = int(payload.get("window", self.window))
        self._X_cols = list(payload["X_cols"])
        self._artifacts = payload["artifacts"]
        self._fit_report = payload.get("fit_report")

        # For scoring, we still need team_games + weeks from the workbook
        self._tg = self._prepare_team_games_with_week()

    # ----------------------------
    # Predict
    # ----------------------------
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
            # If fit() was not called (e.g., manual injection), prepare team_games for scoring.
            self._tg = self._prepare_team_games_with_week()

        A = self._artifacts
        tg = self._tg

        def last_n_means(team_code: str, n: int) -> pd.Series:
            hist = tg[(tg["team"] == team_code) & (tg["week"] < as_of_week)].sort_values(["week","game_id"]).tail(n)
            return hist[A.features].mean(numeric_only=True)

        home_m = last_n_means(home_team, A.window)
        away_m = last_n_means(away_team, A.window)

        row: Dict[str, float] = {}
        for c in A.features:
            row[f"delta_{c}_pre{A.window}"] = float(home_m.get(c, np.nan) - away_m.get(c, np.nan))
        row["neutral_site"] = 0.0

        # Market no-vig home probability
        ph = implied_prob(close_ml_home)
        pa = implied_prob(close_ml_away)
        vig = ph + pa
        imp_home_novig = ph / vig

        row.update({
            "close_spread_home": float(close_spread_home),
            "close_total": float(close_total),
            "open_spread_home": np.nan,
            "open_total": np.nan,
            "imp_p_home_novig": float(imp_home_novig),
        })

        X_row = pd.DataFrame([row]).reindex(columns=self._X_cols, fill_value=np.nan).fillna(A.means)

        pred_margin_home = float(A.m_margin.predict(X_row)[0])
        pred_total = float(A.m_total.predict(X_row)[0])

        # Away line convention: away -X means away expected margin ~ +X; line = -X
        exp_away_margin = -pred_margin_home
        pred_spread_away = -exp_away_margin

        # Coherent win prob from margin (normal approx)
        p_home = float(norm_cdf(pred_margin_home / A.sigma_margin))
        p_away = 1.0 - p_home

        # Market benchmarks
        market_home_p = float(imp_home_novig)
        market_away_p = 1.0 - market_home_p
        market_spread_away = -float(close_spread_home)

        return {
            "pred_spread_away": pred_spread_away,
            "pred_total": pred_total,
            "pred_winprob_home": p_home,
            "pred_winprob_away": p_away,
            "market_spread_away": market_spread_away,
            "market_total": float(close_total),
            "market_winprob_home_novig": market_home_p,
            "market_winprob_away_novig": market_away_p,
            "edge_spread_points_model_minus_market": float(pred_spread_away - market_spread_away),
            "edge_total_points_model_minus_market": float(pred_total - float(close_total)),
            "edge_winprob_away_points_model_minus_market": float(p_away - market_away_p),
        }


def main():
    import argparse
    import json
    import os
    import sys

    p = argparse.ArgumentParser(
        description="NFL 2025 v0 Hybrid Model: predict spread/total/winprob using fundamentals + closing market inputs."
    )
    p.add_argument("--workbook", required=True, help="Path to the Excel workbook")
    p.add_argument("--home", required=True, help="Home team code (e.g., CHI)")
    p.add_argument("--away", required=True, help="Away team code (e.g., GNB)")
    p.add_argument("--close_spread_home", required=True, type=float, help="Closing spread from HOME perspective (e.g., +1.5 means home is +1.5)")
    p.add_argument("--close_total", required=True, type=float, help="Closing total points (e.g., 44.5)")
    p.add_argument("--close_ml_home", required=True, type=float, help="Closing home moneyline (American odds, e.g., +105)")
    p.add_argument("--close_ml_away", required=True, type=float, help="Closing away moneyline (American odds, e.g., -125)")
    p.add_argument("--window", type=int, default=8, help="Rolling window for fundamentals form (default: 8)")
    p.add_argument("--train_through_week", type=int, default=14, help="Train through week N (default: 14)")
    p.add_argument("--as_of_week", type=int, default=19, help="Use team form from games with week < as_of_week (default: 19)")
    p.add_argument("--save_model", default=None, help="Path to save fitted artifacts (joblib). If provided, the model will be fit and then saved.")
    p.add_argument("--load_model", default=None, help="Path to load fitted artifacts (joblib). If provided, fit() is skipped.")
    p.add_argument("--json", action="store_true", help="Output JSON only (useful for piping)")
    args = p.parse_args()

    model = NFLHybridModelV0(workbook_path=args.workbook, window=args.window)

    fit_report = None
    if args.load_model:
        model.load_model(args.load_model)
        fit_report = model._fit_report
    else:
        fit_report = model.fit(train_through_week=args.train_through_week)
        if args.save_model:
            model.save_model(args.save_model)

    pred = model.predict_game(
        home_team=args.home,
        away_team=args.away,
        close_spread_home=args.close_spread_home,
        close_total=args.close_total,
        close_ml_home=args.close_ml_home,
        close_ml_away=args.close_ml_away,
        as_of_week=args.as_of_week,
    )

    out = {"fit_report": fit_report, "prediction": pred}

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return

    if fit_report:
        print("\n=== FIT REPORT (time-respecting holdout) ===")
        for k, v in fit_report.items():
            print(f"{k:>24}: {v}")

    print("\n=== PREDICTION ===")
    print(f"Matchup: {args.away} at {args.home}")

    print("\nModel outputs:")
    print(f"  Spread (away line): {pred['pred_spread_away']:+.2f}")
    print(f"  Total:             {pred['pred_total']:.2f}")
    print(f"  Win% (away):        {pred['pred_winprob_away']*100:.1f}%")
    print(f"  Win% (home):        {pred['pred_winprob_home']*100:.1f}%")

    print("\nMarket (no-vig) benchmarks:")
    print(f"  Spread (away line): {pred['market_spread_away']:+.2f}")
    print(f"  Total:             {pred['market_total']:.2f}")
    print(f"  Win% (away):        {pred['market_winprob_away_novig']*100:.1f}%")
    print(f"  Win% (home):        {pred['market_winprob_home_novig']*100:.1f}%")

    print("\nEdges (model - market):")
    print(f"  Spread points:      {pred['edge_spread_points_model_minus_market']:+.2f}")
    print(f"  Total points:       {pred['edge_total_points_model_minus_market']:+.2f}")
    print(f"  Win% (away) points: {pred['edge_winprob_away_points_model_minus_market']*100:+.1f}%")
    print("")


if __name__ == "__main__":
    main()
