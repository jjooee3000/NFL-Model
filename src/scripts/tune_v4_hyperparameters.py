"""
Tune v4 model hyperparameters to improve margin MAE.

Uses GridSearchCV to test parameter combinations and selects
the best configuration.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_absolute_error
from models.model_v4 import NFLModelV4
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / 'data' / 'nfl_model.db'
TUNING_OUTPUT = PROJECT_ROOT / 'outputs' / 'v4_tuning.json'


def tune_v4_margin(sqlite_path=DB_PATH):
    """Tune v4 RandomForest for margin prediction."""
    logger.info("Loading data...")
    m = NFLModelV4(sqlite_path=sqlite_path)
    games, stats, gamelogs = m.load_data()
    X, y_margin, y_total = m.build_features(games, stats, gamelogs)
    
    # Filter valid targets
    valid = (~pd.isna(y_margin)) & (~pd.isna(y_total))
    X = X[valid.values]
    y_margin = y_margin[valid.values]
    
    # Train/test split
    seasons = games.loc[X.index, "season"].values
    train_idx = seasons <= 2024
    test_idx = seasons == 2025
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y_margin[train_idx], y_margin[test_idx]
    
    logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
    logger.info(f"Testing hyperparameter combinations...")
    
    # Grid of hyperparameters
    param_grid = {
        'n_estimators': [100, 150, 200, 250],
        'max_depth': [8, 10, 12, 15],
        'min_samples_split': [3, 5, 8],
        'min_samples_leaf': [1, 2, 4],
    }
    
    # GridSearchCV for margin
    grid = GridSearchCV(
        RandomForestRegressor(random_state=42, n_jobs=-1),
        param_grid,
        cv=5,
        scoring='neg_mean_absolute_error',
        verbose=1,
        n_jobs=1  # let RF handle parallelization internally
    )
    
    logger.info("Running GridSearchCV...")
    grid.fit(X_train, y_train)
    
    best_params = grid.best_params_
    logger.info(f"Best params: {best_params}")
    logger.info(f"Best CV MAE: {-grid.best_score_:.3f}")
    
    # Evaluate on test
    best_model = grid.best_estimator_
    test_pred = best_model.predict(X_test)
    test_mae = mean_absolute_error(y_test, test_pred)
    train_pred = best_model.predict(X_train)
    train_mae = mean_absolute_error(y_train, train_pred)
    
    logger.info(f"Test MAE: {test_mae:.3f}")
    logger.info(f"Train MAE: {train_mae:.3f}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': X.columns,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info(f"Top 10 features:")
    print(importance.head(10).to_string(index=False))
    
    result = {
        'best_params': best_params,
        'cv_mae': float(-grid.best_score_),
        'test_mae': float(test_mae),
        'train_mae': float(train_mae),
        'n_features': len(X.columns),
        'top_10_features': importance.head(10)[['feature', 'importance']].to_dict(orient='records'),
    }
    
    return result


if __name__ == '__main__':
    result = tune_v4_margin()
    TUNING_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(TUNING_OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)
    logger.info(f"Tuning results saved to {TUNING_OUTPUT}")
