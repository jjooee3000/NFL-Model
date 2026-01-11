"""
Train/Evaluate using new features (EPA, scoring, snaps, Elo, odds).

- Builds features via src/utils/feature_builder.py
- Trains XGBoost with GPU acceleration when available (fallback to CPU)
- Reports MAE via time-series split
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.feature_builder import build_features, FeatureConfig


def build_dataset() -> pd.DataFrame:
    cfg = FeatureConfig(windows=[3,5,8])
    df = build_features(cfg)
    # Drop obvious non-feature columns
    drop_cols = {'season','week','home_team','away_team','game_id'}
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    y = df['margin']
    # Remove rows with NaNs (initial periods); simple impute could be added later
    valid = X.columns[X.dtypes.apply(lambda t: t.kind in 'biufc')]
    X = X[valid].fillna(0.0)
    return X, y, df


def train_eval(X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> float:
    try:
        from xgboost import XGBRegressor
    except ImportError:
        raise RuntimeError('xgboost not installed')
    # Prefer GPU if available
    params_gpu = dict(
        n_estimators=600,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        tree_method='hist',
        device='cuda',
    )
    params_cpu = dict(
        n_estimators=600,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        tree_method='hist',
    )
    # Time series split on index order
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_absolute_error
    tscv = TimeSeriesSplit(n_splits=n_splits)
    maes = []
    # Try GPU first; fallback if error
    for use_gpu in [True, False]:
        params = params_gpu if use_gpu else params_cpu
        try:
            model = XGBRegressor(**params)
            for train_idx, test_idx in tscv.split(X):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                maes.append(mean_absolute_error(y_test, preds))
            print(f"Model: XGBRegressor ({'GPU' if use_gpu else 'CPU'}) | MAE: {np.mean(maes):.3f}")
            return float(np.mean(maes))
        except Exception as e:
            print(f"GPU {'enabled' if use_gpu else 'disabled'} run error: {e}")
            if use_gpu:
                maes = []  # reset for CPU run
                continue
            else:
                raise


def main():
    X, y, df = build_dataset()
    print(f"Dataset: {len(df)} games | Features: {X.shape[1]}")
    mae = train_eval(X, y, n_splits=5)
    # Save a quick summary report
    out = ROOT / 'reports' / 'FEATURE_EVAL_NEW_SOURCES.md'
    out.write_text(f"New Feature Evaluation\n\nGames: {len(df)}\nFeatures: {X.shape[1]}\nMAE: {mae:.3f}\n")
    print(f"Report written: {out}")


if __name__ == '__main__':
    main()
