"""
Feature Analysis for v4: Debug underperformance vs v3.

v4 has 55 features (team-season diffs + rolling momentum) but worse margin MAE (11.14 vs v3's 9.77).
This script performs permutation importance analysis to identify which features help/hurt.

Usage:
    python src/scripts/analysis/analyze_v4_features.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error
import json
from models.model_v4 import NFLModelV4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def analyze_v4_features():
    """Analyze v4 feature importance and test feature selection."""
    print("\n" + "=" * 80)
    print("V4 FEATURE ANALYSIS")
    print("=" * 80)
    
    # Load and prepare data
    print("\n1. Loading and preparing data...")
    m = NFLModelV4(sqlite_path=PROJECT_ROOT / "data" / "nfl_model.db")
    games, stats, gamelogs = m.load_data()
    X, y_margin, y_total = m.build_features(games, stats, gamelogs)
    
    # Get seasons BEFORE filtering
    seasons_all = games.loc[X.index, "season"].values
    
    # Filter valid targets
    valid = (~pd.isna(y_margin)) & (~pd.isna(y_total))
    X = X[valid.values].reset_index(drop=True)
    y_margin = y_margin[valid.values].reset_index(drop=True)
    y_total = y_total[valid.values].reset_index(drop=True)
    seasons = seasons_all[valid.values]
    
    # Train/test split
    train_idx = seasons <= 2024
    test_idx = seasons == 2025
    X_train, X_test = X[train_idx], X[test_idx]
    y_margin_train, y_margin_test = y_margin[train_idx], y_margin[test_idx]
    
    print(f"  Train: {len(X_train)} games (2020-2024)")
    print(f"  Test: {len(X_test)} games (2025)")
    print(f"  Features: {X.shape[1]} total")
    
    # Train model
    print("\n2. Training model...")
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_margin_train)
    
    # Baseline test MAE
    baseline_pred = model.predict(X_test)
    baseline_mae = mean_absolute_error(y_margin_test, baseline_pred)
    print(f"  Baseline test MAE (all {X.shape[1]} features): {baseline_mae:.3f}")
    
    # Permutation importance
    print("\n3. Computing permutation importance (this may take a minute)...")
    perm_result = permutation_importance(
        model, X_test, y_margin_test,
        n_repeats=5,
        random_state=42,
        n_jobs=-1,
        scoring='neg_mean_absolute_error'
    )
    
    # Build feature importance dataframe
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': perm_result.importances_mean,
        'std': perm_result.importances_std
    }).sort_values('importance', ascending=False)
    
    print("\n  Top 20 features:")
    print(feature_importance.head(20)[['feature', 'importance']].to_string(index=False))
    
    print("\n  Bottom 10 features (negative importance = hurt performance):")
    print(feature_importance.tail(10)[['feature', 'importance']].to_string(index=False))
    
    # Test feature selection
    print("\n4. Testing feature selection...")
    results = []
    
    for n_features in [10, 15, 20, 25, 30, 40, 55]:
        top_features = feature_importance.head(n_features)['feature'].tolist()
        X_train_sel = X_train[top_features]
        X_test_sel = X_test[top_features]
        
        m_sel = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
        m_sel.fit(X_train_sel, y_margin_train)
        pred_sel = m_sel.predict(X_test_sel)
        mae_sel = mean_absolute_error(y_margin_test, pred_sel)
        
        improvement = ((baseline_mae - mae_sel) / baseline_mae) * 100
        results.append({
            'n_features': n_features,
            'mae': mae_sel,
            'improvement_%': improvement
        })
        
        print(f"  {n_features:2d} features -> MAE: {mae_sel:.3f} ({improvement:+.1f}% vs baseline)")
    
    # Find best configuration
    best = min(results, key=lambda x: x['mae'])
    print(f"\n  BEST: {best['n_features']} features -> MAE: {best['mae']:.3f}")
    
    # Compare with v3
    print("\n5. Comparison with v3:")
    print(f"  v3 margin MAE (test): 9.77")
    print(f"  v4 baseline (55 features): {baseline_mae:.3f}")
    print(f"  v4 best selection: {best['mae']:.3f}")
    v4_best_vs_v3 = ((9.77 - best['mae']) / 9.77) * 100
    print(f"  Gap: {v4_best_vs_v3:+.1f}% (positive = worse than v3)")
    
    # Save results
    output = {
        'baseline_mae': float(baseline_mae),
        'baseline_features': 55,
        'best_mae': float(best['mae']),
        'best_n_features': int(best['n_features']),
        'improvement_percent': float(best['improvement_%']),
        'top_20_features': feature_importance.head(20)[['feature', 'importance']].to_dict('records'),
        'bottom_10_features': feature_importance.tail(10)[['feature', 'importance']].to_dict('records'),
        'selection_results': results
    }
    
    output_file = OUTPUT_DIR / "v4_feature_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    # Recommendations
    print("\n6. RECOMMENDATIONS:")
    if best['mae'] < baseline_mae:
        print(f"  ✓ Feature selection helps! Reducing to {best['n_features']} features")
        print(f"    improves MAE by {best['improvement_%']:.1f}%")
        print(f"  → Next: Retrain v4 with only top {best['n_features']} features")
    else:
        print(f"  ✗ Feature selection doesn't help (all features needed)")
    
    if best['mae'] < 9.77:
        print(f"  ✓ v4 can beat v3 with {best['n_features']} features!")
        print(f"  → Update model_v4.py to use feature selection")
    else:
        print(f"  ✗ v4 still underperforms v3 even with selection")
        print(f"  → Issue: Team-season diffs may not capture game-level variation")
        print(f"  → Consider: Use v3 as production model; archive v4 as experimental")
    
    return feature_importance


if __name__ == "__main__":
    feature_importance = analyze_v4_features()
