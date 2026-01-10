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
import json
import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression

# Optional HTTP fetching for market data
try:
    import requests
except Exception:  # pragma: no cover
    requests = None

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

# Minimal mapping from common ESPN-like 3-letter codes to team names used by odds providers
_TEAM_CODE_TO_NAME = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GNB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KAN": "Kansas City Chiefs",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NWE": "New England Patriots",
    "NOR": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SFO": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TAM": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
    "LVR": "Las Vegas Raiders",
}


def _choose_bookmaker(bookmakers: list) -> dict:
    """Prefer well-known US books, otherwise pick first."""
    pref = ["draftkings", "fanduel", "betmgm", "caesars", "pointsbet", "williamhill"]
    lower = {b.get("key", "").lower(): b for b in bookmakers}
    for k in pref:
        if k in lower:
            return lower[k]
    return bookmakers[0] if bookmakers else {}


def fetch_market_data_from_odds_api(home_code: str, away_code: str, api_key: str, region: str = "us") -> tuple:
    """Fetch market data (spread, total, home ML, away ML) for a matchup from The Odds API.

    Returns: (close_spread_home, close_total, close_ml_home, close_ml_away)

    Raises RuntimeError with a helpful message if fetching or matching fails.
    """
    if requests is None:
        raise RuntimeError("requests is required for market fetching. Install it via 'pip install requests'.")

    sport_key = "americanfootball_nfl"
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "regions": region,
        "markets": "spreads,totals,h2h",
        "oddsFormat": "american",
        "dateFormat": "unix",
        "apiKey": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch odds from API: {e}")

    data = resp.json()
    home_name = _TEAM_CODE_TO_NAME.get(home_code.upper(), home_code)
    away_name = _TEAM_CODE_TO_NAME.get(away_code.upper(), away_code)

    # Try to find matching event
    def _norm(s: str) -> str:
        return ''.join(ch for ch in s.lower() if ch.isalnum() or ch.isspace())

    target_home = _norm(home_name)
    target_away = _norm(away_name)

    match_event = None
    for ev in data:
        teams_field = ev.get("teams") or []
        teams = [ _norm(t) for t in teams_field ]
        # Check home/away explicit fields from the API feed if present
        ht = _norm(str(ev.get("home_team", "")))
        at = _norm(str(ev.get("away_team", "")))
        if (target_home == ht and target_away == at) or (target_home in teams and target_away in teams):
            match_event = ev
            break
        # also allow substring matches across available team fields
        joined = ' '.join(teams + [ht, at])
        if target_home in joined and target_away in joined:
            match_event = ev
            break

    if match_event is None:
        raise RuntimeError(f"No matching event found for {home_code} vs {away_code} in odds API feed.")

    # Choose bookmaker
    bm = _choose_bookmaker(match_event.get("bookmakers", []))
    markets = {m.get("key"): m for m in bm.get("markets", [])}

    # Extract market data
    close_spread_home = None
    close_total = None
    close_ml_home = None
    close_ml_away = None
    
    # Spreads
    if "spreads" in markets:
        for o in markets["spreads"].get("outcomes", []):
            if _norm(o.get("name", "")) == target_home:
                close_spread_home = float(o.get("point"))
                break
    
    # Totals
    if "totals" in markets:
        outs = markets["totals"].get("outcomes", [])
        if outs:
            close_total = float(outs[0].get("point"))
    
    # Moneylines (h2h)
    if "h2h" in markets:
        for o in markets["h2h"].get("outcomes", []):
            n = _norm(o.get("name", ""))
            if n == target_home:
                close_ml_home = float(o.get("price"))
            elif n == target_away:
                close_ml_away = float(o.get("price"))

    # Fallback for missing spreads
    if close_spread_home is None:
        sp = markets.get("spreads")
        if sp and len(sp.get("outcomes", [])) >= 2:
            mapping = {_norm(o.get("name")): float(o.get("point")) for o in sp["outcomes"]}
            close_spread_home = mapping.get(target_home) or -list(mapping.values())[0]
    
    # Fallback for missing moneylines
    if close_ml_home is None or close_ml_away is None:
        h = next((o for o in bm.get("markets", []) if o.get("key") == "h2h"), None)
        if h:
            for o in h.get("outcomes", []):
                n = _norm(o.get("name", ""))
                if n == target_home:
                    close_ml_home = float(o.get("price"))
                elif n == target_away:
                    close_ml_away = float(o.get("price"))

    if close_spread_home is None or close_total is None or close_ml_home is None or close_ml_away is None:
        raise RuntimeError("Failed to extract complete market data from API event. Consider passing market inputs manually.")

    return float(close_spread_home), float(close_total), float(close_ml_home), float(close_ml_away)


def fetch_upcoming_games_from_espn(days_ahead: int = 3) -> List[Dict[str, Any]]:
    """Fetch upcoming NFL games from ESPN site API for the next `days_ahead` days.

    Returns a list of dicts with keys: 'home_code','away_code','start_time' (ISO str), 'home_name','away_name'.
    """
    if requests is None:
        raise RuntimeError("requests is required for fetching ESPN scoreboard. Install it via 'pip install requests'.")

    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    params = {"dates": "", "limit": 300}

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch ESPN scoreboard: {e}")

    data = resp.json()
    games = []
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=int(days_ahead))

    for ev in data.get("events", []):
        dt = ev.get("date")
        if dt is None:
            continue
        try:
            start = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if start < now or start > cutoff:
            continue
        competitions = ev.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        if len(competitors) != 2:
            continue
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if home is None or away is None:
            continue
        # Use team abbreviations if present
        home_team = home.get("team", {})
        away_team = away.get("team", {})
        home_abbr = home_team.get("abbreviation") or home_team.get("shortDisplayName") or home_team.get("displayName")
        away_abbr = away_team.get("abbreviation") or away_team.get("shortDisplayName") or away_team.get("displayName")
        games.append({
            "home_code": home_abbr,
            "away_code": away_abbr,
            "start_time": start.isoformat(),
            "home_name": home_team.get("displayName"),
            "away_name": away_team.get("displayName"),
        })

    return games


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
        out = df.sort_values(["team", "week", "game_id"]).copy()
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
        g = games[["game_id", "week", "home_team", "away_team", "home_score", "away_score", "neutral_site (0/1)"]].copy()
        g["week"] = pd.to_numeric(g["week"], errors="coerce").astype(int)
        g["neutral_site (0/1)"] = pd.to_numeric(g["neutral_site (0/1)"], errors="coerce").fillna(0).astype(int)
        g["margin_home"] = g["home_score"] - g["away_score"]
        g["total_points"] = g["home_score"] + g["away_score"]
        g["home_win"] = (g["margin_home"] > 0).astype(int)

        # Attach week to team_games
        tg = team_games.merge(g[["game_id", "week"]], on="game_id", how="left", validate="many_to_one")
        tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)

        feats = self._candidate_features(tg)
        tg_roll = self._add_rolling_features(tg, feats)
        pre_cols = [f"{c}_pre{self.window}" for c in feats]

        home_feat = tg_roll[tg_roll["is_home (0/1)"] == 1][["game_id", "team"] + pre_cols].rename(columns={"team": "home_team"})
        away_feat = tg_roll[tg_roll["is_home (0/1)"] == 0][["game_id", "team"] + pre_cols].rename(columns={"team": "away_team"})

        gf = g.merge(home_feat, on=["game_id", "home_team"], how="left").merge(
            away_feat, on=["game_id", "away_team"], how="left", suffixes=("_home", "_away")
        )

        # Fundamentals delta features (home - away)
        X_fund = pd.DataFrame(index=gf.index)
        for c in feats:
            X_fund[f"delta_{c}_pre{self.window}"] = (
                gf[f"{c}_pre{self.window}_home"] - gf[f"{c}_pre{self.window}_away"]
            )
        X_fund["neutral_site"] = gf["neutral_site (0/1)"]

        # Market features from odds
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
        X_market = gf[["close_spread_home","close_total","open_spread_home","open_total","imp_p_home_novig"]].copy()

        # Hybrid matrix
        X = pd.concat([X_fund, X_market], axis=1)
        self._X_cols = list(X.columns)

        # Time-respecting split
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
        y_win_train = gf.loc[train_mask, "home_win"]

        ridge_params = {"alpha": 10.0, "random_state": 0}
        m_margin = Ridge(**ridge_params).fit(X_train, y_margin_train)
        m_total = Ridge(**ridge_params).fit(X_train, y_total_train)

        # Margin volatility for prob mapping
        sigma = float(y_margin_train.std(ddof=0))
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
            "n_features": X_train.shape[1],
            "margin_MAE_test": float(np.mean(np.abs(y_margin_test - pred_margin))),
            "total_MAE_test": float(np.mean(np.abs(y_total_test - pred_total))),
            "sigma_margin_train": sigma,
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
            self._tg = self._prepare_team_games_with_week()

        A = self._artifacts
        tg = self._tg

        def last_n_means(team_code: str, n: int) -> pd.Series:
            hist = tg[(tg["team"] == team_code) & (tg["week"] < as_of_week)].sort_values(["week", "game_id"]).tail(n)
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
            "close_spread_home": close_spread_home,
            "close_total": close_total,
            "open_spread_home": np.nan,
            "open_total": np.nan,
            "imp_p_home_novig": imp_home_novig,
        })

        X_row = pd.DataFrame([row]).reindex(columns=self._X_cols, fill_value=np.nan).fillna(A.means)

        pred_margin_home = A.m_margin.predict(X_row)[0]
        pred_total = A.m_total.predict(X_row)[0]

        # Away line convention: away -X means away expected margin ~ +X; line = -X
        pred_spread_away = -pred_margin_home

        # Coherent win prob from margin (normal approx)
        p_home = norm_cdf(pred_margin_home / A.sigma_margin)
        p_away = 1.0 - p_home

        # Market benchmarks
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


def _extract_market_probability(close_ml_home: float, close_ml_away: float) -> float:
    """Extract no-vig home win probability from moneylines."""
    ph = implied_prob(close_ml_home)
    pa = implied_prob(close_ml_away)
    return ph / (ph + pa)


def ensemble_predict_game(
    home: str,
    away: str,
    close_spread_home: float,
    close_total: float,
    close_ml_home: float,
    close_ml_away: float,
    windows: Optional[List[int]] = None,
    method: str = "weighted",
    train_through_week: int = 14,
    as_of_week: int = 19,
    workbook: Optional[str] = None,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Fit models across multiple windows and return ensembled prediction and diagnostics.

    Returns: (prediction_dict, report_dict)
    """
    if windows is None:
        windows = [4, 6, 8, 10, 12]
    per_window = []
    for w in windows:
        m = NFLHybridModelV0(workbook_path=workbook, window=w)
        rpt = m.fit(train_through_week=train_through_week)
        pred = m.predict_game(
            home_team=home,
            away_team=away,
            close_spread_home=close_spread_home,
            close_total=close_total,
            close_ml_home=close_ml_home,
            close_ml_away=close_ml_away,
            as_of_week=as_of_week,
        )
        per_window.append(
            {
                "window": int(w),
                "mae": float(rpt.get("margin_MAE_test", float('nan'))),
                "margin": float(pred["pred_spread_away"]),
                "total": float(pred["pred_total"]),
                "p_home": float(pred["pred_winprob_home"]),
                "sigma": float(m._artifacts.sigma_margin) if m._artifacts is not None else float('nan'),
            }
        )

    # Compute weights
    maes = [pw["mae"] for pw in per_window]
    eps = 1e-8
    if method == "mean":
        weights = [1.0 / len(per_window)] * len(per_window)
    else:
        inv = [1.0 / (m + eps) for m in maes]
        s = sum(inv)
        weights = [v / s for v in inv]

    # Aggregate predictions using weights
    ens_margin = sum(w * pw["margin"] for w, pw in zip(weights, per_window))
    ens_total = sum(w * pw["total"] for w, pw in zip(weights, per_window))
    ens_sigma = sum(w * pw["sigma"] for w, pw in zip(weights, per_window))

    ens_p_home = norm_cdf(ens_margin / (ens_sigma if ens_sigma > 0 else 14.0))

    # Market benchmarks
    market_home_p = _extract_market_probability(close_ml_home, close_ml_away)

    market_spread_away = -close_spread_home
    pred = {
        "pred_spread_away": ens_margin,
        "pred_total": ens_total,
        "pred_winprob_home": ens_p_home,
        "pred_winprob_away": 1.0 - ens_p_home,
        "market_spread_away": market_spread_away,
        "market_total": close_total,
        "market_winprob_home_novig": market_home_p,
        "market_winprob_away_novig": 1.0 - market_home_p,
        "edge_spread_points_model_minus_market": ens_margin - market_spread_away,
        "edge_total_points_model_minus_market": ens_total - close_total,
        "edge_winprob_away_points_model_minus_market": (1.0 - ens_p_home) - (1.0 - market_home_p),
    }

    # Build report
    for pw, w in zip(per_window, weights):
        pw["weight"] = w

    report = {
        "method": method,
        "windows": windows,
        "weights": weights,
        "per_window": per_window,
        "ensemble_sigma": ens_sigma,
    }

    return pred, report


def main():
    import argparse
    import os
    import sys

    p = argparse.ArgumentParser(
        description="NFL 2025 v0 Hybrid Model: predict spread/total/winprob using fundamentals + closing market inputs."
    )
    p.add_argument("--workbook", help="(ignored) Workbook path is fixed in the script")
    p.add_argument("--home", help="Home team code (e.g., CHI)")
    p.add_argument("--away", help="Away team code (e.g., GNB)")
    p.add_argument("--close_spread_home", type=float, help="Closing spread from HOME perspective (e.g., +1.5 means home is +1.5)")
    p.add_argument("--close_total", type=float, help="Closing total points (e.g., 44.5)")
    p.add_argument("--close_ml_home", type=float, help="Closing home moneyline (American odds, e.g., +105)")
    p.add_argument("--close_ml_away", type=float, help="Closing away moneyline (American odds, e.g., -125)")
    p.add_argument("--window", type=int, default=None, help="Rolling window for fundamentals form (default: 8)")
    p.add_argument("--train_through_week", type=int, default=None, help="Train through week N (default: 14)")
    p.add_argument("--as_of_week", type=int, default=None, help="Use team form from games with week < as_of_week (default: 19)")
    p.add_argument("--save_model", default=None, help="Path to save fitted artifacts (joblib). If provided, the model will be fit and then saved.")
    p.add_argument("--load_model", default=None, help="Path to load fitted artifacts (joblib). If provided, fit() is skipped.")
    p.add_argument("--json", action="store_true", help="Output JSON only (useful for piping)")

    # Market fetch options
    p.add_argument("--fetch_market", action="store_true", help="Fetch market inputs from The Odds API")
    p.add_argument("--odds_api_key", default=None, help="Odds API key for The Odds API (optional)")

    # Ensemble options
    p.add_argument("--ensemble", action="store_true", help="Run ensemble across multiple rolling windows")
    p.add_argument("--windows", nargs="+", type=int, default=None, help="List of windows to use for ensemble (e.g., 4 6 8 10)")
    p.add_argument("--ensemble_method", choices=["mean","weighted"], default="weighted", help="How to combine window predictions")

    # Upcoming games scanning
    p.add_argument("--scan_upcoming", action="store_true", help="Scan ESPN for upcoming NFL games and predict each")
    p.add_argument("--scan_days", type=int, default=3, help="Number of days ahead to scan for upcoming games (default: 3)")
    p.add_argument("--save_predictions", default=None, help="Path to save batch predictions as CSV or JSON")

    args = p.parse_args()

    def prompt_val(prompt_text: str, cast=str, default=None):
        """Prompt until a valid value is entered. If default is provided, an empty entry returns the default.

        If stdin is not a TTY (non-interactive mode) or --json is set, return default immediately when provided.
        """
        # Non-interactive: return default immediately if provided
        if default is not None and (not sys.stdin.isatty() or args.json):
            return default

        while True:
            if default is not None:
                raw = input(f"{prompt_text} [{default}]: ").strip()
                if raw == "":
                    return default
            else:
                raw = input(f"{prompt_text}: ").strip()
                if raw == "":
                    print("Value required.")
                    continue
            try:
                if cast is bool:
                    return raw.lower() in ("y", "yes", "true", "1")
                return cast(raw)
            except Exception as e:
                print(f"Invalid value ({e}); try again.")

    # Workbook path is fixed/permanent per user request
    workbook = r"C:\Users\cahil\OneDrive\Desktop\Sports Model\NFL-Model\nfl_2025_model_data_with_moneylines.xlsx"
    if args.workbook and args.workbook != workbook:
        print(f"Ignoring --workbook {args.workbook}; using fixed workbook path: {workbook}")

    # Numeric defaults; avoid prompting when running in non-interactive/json mode or scan_upcoming mode
    if args.window is not None:
        window = args.window
    else:
        window = 8 if (args.json or args.scan_upcoming) else prompt_val("Rolling window for fundamentals form", int, default=8)

    if args.train_through_week is not None:
        train_through_week = args.train_through_week
    else:
        train_through_week = 14 if (args.json or args.scan_upcoming) else prompt_val("Train through week", int, default=14)

    if args.as_of_week is not None:
        as_of_week = args.as_of_week
    else:
        as_of_week = 19 if (args.json or args.scan_upcoming) else prompt_val("As of week (use games with week < as_of_week)", int, default=19)

    # Create model instance with selected window
    model = NFLHybridModelV0(workbook_path=workbook, window=window)

    # Load or fit
    fit_report = None
    if args.load_model:
        model.load_model(args.load_model)
        fit_report = model._fit_report
    else:
        fit_report = model.fit(train_through_week=train_through_week)
        # Optionally save artifacts
        if args.save_model:
            model.save_model(args.save_model)
        else:
            maybe_save = prompt_val("Save model artifacts to path (leave blank to skip)", str, default="")
            if maybe_save:
                model.save_model(maybe_save)

    # Prediction inputs: prompt if not provided on CLI (skip prompting when scanning upcoming games)
    if args.scan_upcoming:
        home = None
        away = None
        close_spread_home = None
        close_total = None
        close_ml_home = None
        close_ml_away = None
    else:
        home = args.home or prompt_val("Home team code (e.g., CHI)", str)
        away = args.away or prompt_val("Away team code (e.g., GNB)", str)

        # Optionally fetch market data via The Odds API
        if args.fetch_market:
            api_key = args.odds_api_key or prompt_val("Odds API key (The Odds API)", str)
            try:
                close_spread_home, close_total, close_ml_home, close_ml_away = fetch_market_data_from_odds_api(home, away, api_key)
                print(f"Fetched market: spread(home)={close_spread_home}, total={close_total}, ml_home={close_ml_home}, ml_away={close_ml_away}")
            except Exception as e:
                print(f"Market fetch failed: {e}")
                # fallback to interactive entry
                close_spread_home = prompt_val("Closing spread from HOME perspective (e.g., +1.5)", float)
                close_total = prompt_val("Closing total points (e.g., 44.5)", float)
                close_ml_home = prompt_val("Closing home moneyline (e.g., +105)", float)
                close_ml_away = prompt_val("Closing away moneyline (e.g., -125)", float)
        else:
            close_spread_home = args.close_spread_home if args.close_spread_home is not None else prompt_val("Closing spread from HOME perspective (e.g., +1.5)", float)
            close_total = args.close_total if args.close_total is not None else prompt_val("Closing total points (e.g., 44.5)", float)
            close_ml_home = args.close_ml_home if args.close_ml_home is not None else prompt_val("Closing home moneyline (e.g., +105)", float)
            close_ml_away = args.close_ml_away if args.close_ml_away is not None else prompt_val("Closing away moneyline (e.g., -125)", float)

    # Use ensemble option if requested (single game flow; skip when scanning upcoming games)
    if not args.scan_upcoming:
        if args.ensemble:
            windows = args.windows if args.windows is not None else [4, 6, 8, 10, 12]
            method = args.ensemble_method
            pred, ens_report = ensemble_predict_game(
                home=home,
                away=away,
                close_spread_home=close_spread_home,
                close_total=close_total,
                close_ml_home=close_ml_home,
                close_ml_away=close_ml_away,
                windows=windows,
                method=method,
                train_through_week=train_through_week,
                as_of_week=as_of_week,
                workbook=workbook,
            )
            out = {"fit_report": fit_report, "prediction": pred, "ensemble_report": ens_report}
        else:
            pred = model.predict_game(
                home_team=home,
                away_team=away,
                close_spread_home=close_spread_home,
                close_total=close_total,
                close_ml_home=close_ml_home,
                close_ml_away=close_ml_away,
                as_of_week=as_of_week,
            )

            out = {"fit_report": fit_report, "prediction": pred}
    else:
        out = {"fit_report": fit_report}

    # If scanning upcoming games, fetch matchups and produce batch predictions
    if args.scan_upcoming:
        print(f"Scanning ESPN for upcoming games (next {args.scan_days} days)...")
        upcoming = fetch_upcoming_games_from_espn(days_ahead=args.scan_days)
        print(f"Found {len(upcoming)} upcoming games")

        # Ensemble settings for batch
        windows = args.windows if args.windows is not None else [4, 6, 8, 10, 12]
        method = args.ensemble_method

        batch = []
        for g in upcoming:
            h_code = (g.get("home_code") or "").strip()
            a_code = (g.get("away_code") or "").strip()
            # Optionally fetch market for each game
            if args.fetch_market:
                try:
                    sp, tot, mlh, mla = fetch_market_data_from_odds_api(h_code, a_code, args.odds_api_key)
                except Exception as e:
                    print(f"Market fetch failed for {a_code} at {h_code}: {e}; skipping market for this game")
                    sp = None; tot = None; mlh = None; mla = None
            else:
                sp = None; tot = None; mlh = None; mla = None

            # Predict using ensemble if requested else single-window model
            if args.ensemble:
                # For batch, re-use ensemble settings
                pred_g, rep_g = ensemble_predict_game(
                    home=h_code,
                    away=a_code,
                    close_spread_home=sp if sp is not None else 0.0,
                    close_total=tot if tot is not None else 0.0,
                    close_ml_home=mlh if mlh is not None else 0.0,
                    close_ml_away=mla if mla is not None else 0.0,
                    windows=windows,
                    method=method,
                    train_through_week=train_through_week,
                    as_of_week=as_of_week,
                    workbook=workbook,
                )
                entry = {"home": h_code, "away": a_code, "start_time": g.get("start_time"), "prediction": pred_g, "ensemble_report": rep_g}
            else:
                # Use single-window model; ensure model window is set
                model.window = window
                pred_g = model.predict_game(
                    home_team=h_code,
                    away_team=a_code,
                    close_spread_home=sp if sp is not None else 0.0,
                    close_total=tot if tot is not None else 0.0,
                    close_ml_home=mlh if mlh is not None else 0.0,
                    close_ml_away=mla if mla is not None else 0.0,
                    as_of_week=as_of_week,
                )
                entry = {"home": h_code, "away": a_code, "start_time": g.get("start_time"), "prediction": pred_g}
            batch.append(entry)

        # Optionally save
        if args.save_predictions:
            import os
            spath = args.save_predictions
            ext = os.path.splitext(spath)[1].lower()
            if ext == ".csv":
                with open(spath, "w", newline='', encoding='utf8') as fh:
                    writer = csv.writer(fh)
                    writer.writerow(["start_time", "home", "away", "pred_spread_away", "pred_total", "pred_winprob_home", "market_spread_away", "market_total"])
                    for e in batch:
                        p = e.get("prediction", {})
                        writer.writerow([
                            e.get("start_time"), e.get("home"), e.get("away"),
                            p.get("pred_spread_away"), p.get("pred_total"), p.get("pred_winprob_home"),
                            p.get("market_spread_away"), p.get("market_total")
                        ])
                print(f"Saved CSV to {spath}")
            else:
                with open(spath, "w", encoding='utf8') as fh:
                    json.dump(batch, fh, indent=2)
                print(f"Saved JSON to {spath}")

        # Print brief summary then exit
        if args.json:
            print(json.dumps({"batch_predictions": batch}, indent=2))
            return
        
        print("\n=== BATCH PREDICTIONS ===")
        for e in batch:
            p = e.get("prediction", {})
            print(
                f"{e.get('start_time')}: {e.get('away')} at {e.get('home')} | "
                f"Spread(away): {p.get('pred_spread_away'):+.2f} | "
                f"Total: {p.get('pred_total'):.2f} | "
                f"P(home): {p.get('pred_winprob_home') * 100:.1f}%"
            )
        return

    if fit_report:
        print("\n=== FIT REPORT (time-respecting holdout) ===")
        for k, v in fit_report.items():
            print(f"{k:>24}: {v}")

    # If ensemble, print per-window diagnostics
    if args.ensemble:
        print("\n=== ENSEMBLE DIAGNOSTICS ===")
        print("Window | MAE (margin) | Weight | Pred margin | Pred total | P(home)")
        for pw in out.get("ensemble_report", {}).get("per_window", []):
            print(f"  {pw['window']:>6} | {pw['mae']:.4f} | {pw.get('weight',0):.3f} | {pw['margin']:+.2f} | {pw['total']:.2f} | {pw['p_home']*100:.1f}%")
        print(f"\nEnsemble method: {out.get('ensemble_report',{}).get('method')}\nEnsemble sigma: {out.get('ensemble_report',{}).get('ensemble_sigma')}")

    print("\n=== PREDICTION ===")
    # Use values collected interactively (or from CLI)
    print(f"Matchup: {away} at {home}")

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
