"""
Feature Analysis for v4: Debug underperformance vs v3.

v4 has 82 features (team-season diffs + rolling momentum) but worse margin MAE (11.14 vs v3's 9.77).
This script performs permutation importance analysis to identify which features help/hurt.

Usage:
    python src/scripts/analysis/analyze_v4_features_new.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
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
    
    print(f"  DEBUG: X shape after build_features: {X.shape}")
    print(f"  DEBUG: X.columns count: {len(X.columns)}")
    
    # Get seasons BEFORE filtering
    seasons_all = games.loc[X.index, "season"].values
    
    # Filter valid targets
    valid = (~pd.isna(y_margin)) & (~pd.isna(y_total))
    X = X[valid.values].reset_index(drop=True)
    y_margin = y_margin[valid.values].reset_index(drop=True)
    y_total = y_total[valid.values].reset_index(drop=True)
    seasons = seasons_all[valid.values]
    
    print(f"  DEBUG: X shape after filtering: {X.shape}")
    print(f"  DEBUG: X.columns count after filtering: {len(X.columns)}")
    
    n_features = X.shape[1]
    n_games = X.shape[0]
    
    # Train/test split
    train_idx = seasons <= 2024
    test_idx = seasons == 2025
    X_train, X_test = X[train_idx], X[test_idx]
    y_margin_train, y_margin_test = y_margin[train_idx], y_margin[test_idx]
    
    print(f"  Games loaded: {n_games} total")
    print(f"    Train (2020-2024): {len(X_train)} games")
    print(f"    Test (2025): {len(X_test)} games")
    print(f"  Features: {n_features} total")
    
    # Train model
    print("\n2. Training baseline model...")
    model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_margin_train)
    
    # Baseline test MAE
    baseline_pred = model.predict(X_test)
    baseline_mae = mean_absolute_error(y_margin_test, baseline_pred)
    print(f"  [OK] Model trained ({n_features} features)")
    print(f"  Baseline test MAE: {baseline_mae:.3f}")
    
    # Permutation importance
    print(f"\n3. Computing permutation importance ({n_features} features x 5 repeats)...")
    print("  This will take 2-3 minutes...")
    perm_result = permutation_importance(
        model, X_test, y_margin_test,
        n_repeats=5,
        random_state=42,
        n_jobs=-1,
        scoring='neg_mean_absolute_error'
    )
    print("  [OK] Importance computed")
    
    # Build feature importance dataframe
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': perm_result.importances_mean,
        'std': perm_result.importances_std
    }).sort_values('importance', ascending=False)
    
    print("\n  TOP 15 Features (help prediction):")
    for idx, row in feature_importance.head(15).iterrows():
        print(f"    {row['feature']:40s} {row['importance']:+.4f} ± {row['std']:.4f}")
    
    print("\n  BOTTOM 10 Features (hurt prediction):")
    for idx, row in feature_importance.tail(10).iterrows():
        print(f"    {row['feature']:40s} {row['importance']:+.4f} ± {row['std']:.4f}")
    
    # Test feature selection
    print(f"\n4. Testing feature selection (various subset sizes)...")
    results = []
    
    for n_keep in [10, 15, 20, 25, 30, 40, 50, 82]:
        top_features = feature_importance.head(n_keep)['feature'].tolist()
        X_train_sel = X_train[top_features]
        X_test_sel = X_test[top_features]
        
        m_sel = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
        m_sel.fit(X_train_sel, y_margin_train)
        pred_sel = m_sel.predict(X_test_sel)
        mae_sel = mean_absolute_error(y_margin_test, pred_sel)
        
        improvement = ((baseline_mae - mae_sel) / baseline_mae) * 100
        results.append({
            'n_features': n_keep,
            'mae': mae_sel,
            'improvement_%': improvement
        })
        
        marker = "[*]" if mae_sel < baseline_mae else "[ ]"
        print(f"  {marker} {n_keep:2d} features -> MAE: {mae_sel:.3f} ({improvement:+.1f}% vs baseline)")
    
    # Find best configuration
    best = min(results, key=lambda x: x['mae'])
    print(f"\n  BEST CONFIG: {best['n_features']} features → MAE: {best['mae']:.3f}")
    
    # Compare with v3
    print(f"\n5. COMPARISON WITH V3:")
    print(f"  v3 margin MAE (test 2025): 9.77")
    print(f"  v4 baseline ({n_features} features): {baseline_mae:.3f}")
    print(f"  v4 best selection: {best['mae']:.3f}")
    
    gap_pct = ((9.77 - best['mae']) / 9.77) * 100
    if best['mae'] < 9.77:
        print(f"  [GOOD] v4 beats v3 by {-gap_pct:.1f}%")
    else:
        print(f"  [BAD] v4 lags v3 by {gap_pct:.1f}%")
    
    # Save results
    output = {
        'analysis': 'v4_feature_importance',
        'n_features_total': n_features,
        'n_games_train': len(X_train),
        'n_games_test': len(X_test),
        'baseline_mae': float(baseline_mae),
        'best_mae': float(best['mae']),
        'best_n_features': int(best['n_features']),
        'improvement_percent': float(best['improvement_%']),
        'top_15_features': feature_importance.head(15)[['feature', 'importance', 'std']].to_dict('records'),
        'bottom_10_features': feature_importance.tail(10)[['feature', 'importance', 'std']].to_dict('records'),
        'selection_results': results
    }
    
    output_file = OUTPUT_DIR / "v4_feature_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {output_file}")
    
    # Recommendations
    print(f"\n6. RECOMMENDATIONS:")
    if best['mae'] < baseline_mae:
        print(f"  [GOOD] Feature selection helps!")
        print(f"    -> Reducing from {n_features} to {best['n_features']} features")
        print(f"    -> Improves MAE by {best['improvement_%']:.1f}%")
        print(f"  -> Next: Retrain v4 with only top {best['n_features']} features")
    else:
        print(f"  [BAD] All {n_features} features needed (no selection benefit)")
    
    if best['mae'] < 9.77:
        print(f"  [GOOD] v4 CAN beat v3!")
        print(f"    -> Use {best['n_features']} features")
        print(f"    -> Margin MAE: {best['mae']:.3f}")
    else:
        print(f"  [BAD] v4 still underperforms v3 even with optimal selection")
        print(f"  Analysis:")
        if gap_pct > 5:
            print(f"    - Gap is large ({gap_pct:.1f}%)")
            print(f"    - Issue: Team-season diffs inadequate for game-level prediction")
            print(f"    - Team-season aggregation loses per-game variation")
        else:
            print(f"    - Gap is small ({gap_pct:.1f}%)")
            print(f"    - Could still be viable with hyperparameter tuning")
    
    return feature_importance


if __name__ == "__main__":
    feature_importance = analyze_v4_features()
