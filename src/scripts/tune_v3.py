"""
Hyperparameter tuning for model_v3 using TimeSeriesSplit.
Outputs a markdown summary and JSON of best params for margin and total.
Run: python src/scripts/tune_v3.py [--train-week 14]
"""
from pathlib import Path
import sys
import time
import json

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, REPORTS_DIR, ensure_dir
from models.model_v3 import NFLHybridModelV3

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import make_scorer
import numpy as np
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description="Tune RandomForest hyperparameters and window for model_v3")
parser.add_argument("--train-week", type=int, default=14, help="Train through week N (default: 14)")
parser.add_argument("--windows", nargs="+", type=int, default=[6,8,10], help="Candidate rolling windows (default: 6 8 10)")
args = parser.parse_args()

workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
ensure_dir(REPORTS_DIR)

print("\n=== Tuning v3 (RandomForest) ===")
print(f"Workbook: {workbook}")
print(f"Train through week: {args.train_week}")

# Prepare data via model to get feature matrix and targets
best_overall = {
    "window": None,
    "margin_params": None,
    "total_params": None,
    "margin_mae": float("inf"),
    "total_mae": float("inf"),
}

# Reconstruct training data from internal artifacts
# Note: We can rerun the feature prep here for clarity
# Using private steps from the class isn't public; we re-derive below

for W in args.windows:
    print(f"\n--- Window {W} ---")
    m = NFLHybridModelV3(workbook_path=str(workbook), window=int(W), model_type="randomforest", prefer_sqlite=True)
    # Reload workbook and rebuild X similarly
    games, team_games, odds = m.load_workbook()

    # Targets from games table
    g = games[["game_id", "week", "home_team", "away_team", "home_score", "away_score", "neutral_site (0/1)"]].copy()
    g["week"] = pd.to_numeric(g["week"], errors="coerce").astype(int)
    g["neutral_site (0/1)"] = pd.to_numeric(g["neutral_site (0/1)"], errors="coerce").fillna(0).astype(int)
    g["margin_home"] = g["home_score"] - g["away_score"]
    g["total_points"] = g["home_score"] + g["away_score"]

    tg = team_games.merge(g[["game_id", "week"]], on="game_id", how="left", validate="many_to_one")
    tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)

    feats = m._candidate_features(tg)

    tg_roll = m._add_rolling_features(tg, feats)
    tg_momentum = m._add_momentum_features(tg_roll, feats)

    pre_cols = [f"{c}_pre{m.window}" for c in feats]
    ema_cols = [f"{c}_ema{m.window}" for c in feats]
    trend_cols = [f"{c}_trend{m.window}" for c in feats]
    vol_cols = [f"{c}_vol{m.window}" for c in feats]
    season_cols = [f"{c}_season_avg" for c in feats]
    ratio_cols = [f"{c}_recent_ratio" for c in feats]

    home_feat = tg_momentum[tg_momentum["is_home (0/1)"] == 1][["game_id", "team"] + pre_cols + ema_cols + trend_cols + vol_cols + season_cols + ratio_cols].rename(columns={"team": "home_team"})
    away_feat = tg_momentum[tg_momentum["is_home (0/1)"] == 0][["game_id", "team"] + pre_cols + ema_cols + trend_cols + vol_cols + season_cols + ratio_cols].rename(columns={"team": "away_team"})

    gf = g.merge(home_feat, on=["game_id", "home_team"], how="left").merge(away_feat, on=["game_id", "away_team"], how="left", suffixes=("_home", "_away"))

    X_fund = pd.DataFrame(index=gf.index)
    for c in feats:
        X_fund[f"delta_{c}_pre{m.window}"] = gf[f"{c}_pre{m.window}_home"] - gf[f"{c}_pre{m.window}_away"]
        X_fund[f"delta_{c}_ema{m.window}"] = gf[f"{c}_ema{m.window}_home"] - gf[f"{c}_ema{m.window}_away"]
        X_fund[f"delta_{c}_trend{m.window}"] = gf[f"{c}_trend{m.window}_home"] - gf[f"{c}_trend{m.window}_away"]
        X_fund[f"delta_{c}_vol{m.window}"] = gf[f"{c}_vol{m.window}_home"] - gf[f"{c}_vol{m.window}_away"]
        X_fund[f"delta_{c}_season_avg"] = gf[f"{c}_season_avg_home"] - gf[f"{c}_season_avg_away"]
        X_fund[f"delta_{c}_recent_ratio"] = gf[f"{c}_recent_ratio_home"] - gf[f"{c}_recent_ratio_away"]

    X_fund["neutral_site"] = gf["neutral_site (0/1)"]

    odds_use = odds[[
        "game_id", "close_spread_home", "close_total",
        "open_spread_home", "open_total",
        "close_ml_home", "close_ml_away"
    ]].copy()

    # New movement features
    odds_use["spread_move_home"] = odds_use["close_spread_home"] - odds_use["open_spread_home"]
    odds_use["total_move"] = odds_use["close_total"] - odds_use["open_total"]

    # Implied home no-vig
    imp_p_home = odds_use["close_ml_home"].apply(lambda x: 100.0 / (x + 100.0) if x > 0 else (-x) / (-x + 100.0))
    imp_p_away = odds_use["close_ml_away"].apply(lambda x: 100.0 / (x + 100.0) if x > 0 else (-x) / (-x + 100.0))
    vig_sum = imp_p_home + imp_p_away
    odds_use["imp_p_home_novig"] = imp_p_home / vig_sum

    gf = gf.merge(odds_use[[
        "game_id",
        "close_spread_home", "close_total",
        "open_spread_home", "open_total",
        "imp_p_home_novig",
        "spread_move_home", "total_move"
    ]], on="game_id", how="left")

    X_market = gf[[
        "close_spread_home", "close_total",
        "open_spread_home", "open_total",
        "imp_p_home_novig",
        "spread_move_home", "total_move"
    ]].copy()

    X = pd.concat([X_fund, X_market], axis=1)

    # Split
    train_mask = gf["week"] <= int(args.train_week)
    test_mask = gf["week"] >= int(args.train_week) + 1

    X_train = X.loc[train_mask].copy()
    X_test = X.loc[test_mask].copy()
    means = X_train.mean(numeric_only=True)
    X_train.fillna(means, inplace=True)
    X_test.fillna(means, inplace=True)

    y_margin_train = gf.loc[train_mask, "margin_home"]
    y_total_train = gf.loc[train_mask, "total_points"]

    # Scoring
    mae_scorer = make_scorer(lambda y_true, y_pred: np.mean(np.abs(y_true - y_pred)), greater_is_better=False)

    tscv = TimeSeriesSplit(n_splits=4)
    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [10, 12, 16],
        "min_samples_split": [2, 5],
        "min_samples_leaf": [1, 2, 3],
        "max_features": ["sqrt", 0.5, 0.8],
    }

    print("\nTuning margin model...")
    start = time.perf_counter()
    rf_margin = RandomForestRegressor(random_state=42, n_jobs=-1)
    grid_margin = GridSearchCV(rf_margin, param_grid, cv=tscv, scoring=mae_scorer, n_jobs=-1)
    grid_margin.fit(X_train, y_margin_train)
    margin_time = time.perf_counter() - start

    print("Tuning total model...")
    start = time.perf_counter()
    rf_total = RandomForestRegressor(random_state=42, n_jobs=-1)
    grid_total = GridSearchCV(rf_total, param_grid, cv=tscv, scoring=mae_scorer, n_jobs=-1)
    grid_total.fit(X_train, y_total_train)
    total_time = time.perf_counter() - start

    best_margin = grid_margin.best_params_
    best_total = grid_total.best_params_

    # Fit with best and compute holdout MAE
    rf_margin_best = RandomForestRegressor(**best_margin)
    rf_total_best = RandomForestRegressor(**best_total)
    rf_margin_best.fit(X_train, y_margin_train)
    rf_total_best.fit(X_train, y_total_train)

    pred_m = rf_margin_best.predict(X_test)
    pred_t = rf_total_best.predict(X_test)

    mae_m = float(np.mean(np.abs(gf.loc[test_mask, "margin_home"] - pred_m)))
    mae_t = float(np.mean(np.abs(gf.loc[test_mask, "total_points"] - pred_t)))

    print(f"Holdout MAE (margin, W={W}): {mae_m:.3f}")
    print(f"Holdout MAE (total,  W={W}): {mae_t:.3f}")

    # Track best overall by margin MAE primarily, then total
    if mae_m < best_overall["margin_mae"]:
        best_overall.update({
            "window": int(W),
            "margin_params": best_margin,
            "total_params": best_total,
            "margin_mae": mae_m,
            "total_mae": mae_t,
        })

# Write summary files
summary_md = REPORTS_DIR / "TUNING_V3.md"
summary_json = REPORTS_DIR / "tuning_v3.json"

with summary_md.open("w", encoding="utf-8") as f:
    f.write("# model_v3 RandomForest Tuning (TimeSeriesSplit)\n\n")
    f.write(f"Train through week: {args.train_week}\n\n")
    f.write("## Best Overall\n")
    f.write(f"- window: {best_overall['window']}\n")
    f.write(f"- margin MAE: {best_overall['margin_mae']:.3f}\n")
    f.write(f"- total MAE:  {best_overall['total_mae']:.3f}\n\n")
    f.write("### Margin Params\n")
    for k, v in (best_overall["margin_params"] or {}).items():
        f.write(f"- {k}: {v}\n")
    f.write("\n### Total Params\n")
    for k, v in (best_overall["total_params"] or {}).items():
        f.write(f"- {k}: {v}\n")

with summary_json.open("w", encoding="utf-8") as f:
    json.dump(best_overall, f, indent=2)

print(f"\n✓ Wrote tuning summary: {summary_md}")
print(f"✓ Wrote tuning params JSON: {summary_json}")
