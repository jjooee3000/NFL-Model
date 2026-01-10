"""
Feature importance analysis for NFL model
Identifies which of the 234 features drive predictions most
"""
from pathlib import Path
import sys

import pandas as pd
import numpy as np
import joblib

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, OUTPUTS_DIR, ensure_dir
from models.model_v2 import NFLHybridModelV2

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

def analyze_feature_importance():
    """Analyze which features matter most in the v2 model."""
    workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
    ensure_dir(OUTPUTS_DIR)
    
    print("=" * 80)
    print("FEATURE IMPORTANCE ANALYSIS - model_v2.py (RandomForest)")
    print("=" * 80)
    
    # Load and train model
    model = NFLHybridModelV2(workbook_path=workbook, model_type='randomforest')
    model.fit()
    
    # Extract feature importances from margin model
    margin_model = model._artifacts.m_margin  # RandomForest for margin predictions
    feature_names = model._artifacts.features
    importances = margin_model.feature_importances_
    
    # Ensure arrays match
    if len(feature_names) != len(importances):
        print(f"Warning: {len(feature_names)} features but {len(importances)} importances")
        # Trim to match
        min_len = min(len(feature_names), len(importances))
        feature_names = feature_names[:min_len]
        importances = importances[:min_len]
    
    # Create importance dataframe
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances,
        'importance_pct': importances / importances.sum() * 100
    }).sort_values('importance', ascending=False)
    
    print(f"\nTotal features: {len(feature_names)}")
    print(f"Total importance sum: {importances.sum():.6f}")
    print(f"Average importance per feature: {importances.mean():.6f}")
    
    # Top 20 features
    print("\n" + "=" * 80)
    print("TOP 20 MOST IMPORTANT FEATURES")
    print("=" * 80)
    for idx, row in importance_df.head(20).iterrows():
        print(f"{row['feature']:40s} | {row['importance']:10.6f} | {row['importance_pct']:6.2f}%")
    
    # Feature type breakdown
    print("\n" + "=" * 80)
    print("FEATURE TYPE BREAKDOWN")
    print("=" * 80)
    
    feature_types = {
        'raw_rolling': importance_df[importance_df['feature'].str.contains('_roll_', na=False)],
        'ema': importance_df[importance_df['feature'].str.contains('_ema_', na=False)],
        'trend': importance_df[importance_df['feature'].str.contains('_trend_', na=False)],
        'volatility': importance_df[importance_df['feature'].str.contains('_volatility_', na=False)],
        'season_to_date': importance_df[importance_df['feature'].str.contains('_std_', na=False)],
        'recent_season_ratio': importance_df[importance_df['feature'].str.contains('_ratio_', na=False)],
        'neutral_site': importance_df[importance_df['feature'].str.contains('neutral_site', na=False)],
        'moneyline': importance_df[importance_df['feature'].str.contains('moneyline', na=False)],
        'total_line': importance_df[importance_df['feature'].str.contains('total_line', na=False)],
        'spread': importance_df[importance_df['feature'].str.contains('spread', na=False)],
    }
    
    for ftype, df in feature_types.items():
        if len(df) > 0:
            total_imp = df['importance'].sum()
            pct = total_imp / importances.sum() * 100
            avg_imp = df['importance'].mean()
            print(f"{ftype:25s} | Count: {len(df):3d} | Total Imp: {total_imp:10.6f} | Pct: {pct:6.2f}% | Avg: {avg_imp:10.6f}")
    
    # Bottom 20 features (least important)
    print("\n" + "=" * 80)
    print("BOTTOM 20 LEAST IMPORTANT FEATURES (Candidates for Removal)")
    print("=" * 80)
    for idx, row in importance_df.tail(20).iterrows():
        print(f"{row['feature']:40s} | {row['importance']:10.6f} | {row['importance_pct']:6.2f}%")
    
    # Cumulative importance analysis
    print("\n" + "=" * 80)
    print("CUMULATIVE IMPORTANCE THRESHOLDS")
    print("=" * 80)
    
    importance_df['cumsum'] = importance_df['importance'].cumsum()
    importance_df['cumsum_pct'] = importance_df['cumsum'] / importances.sum() * 100
    
    for threshold in [50, 75, 90, 95, 99]:
        n_features = (importance_df['cumsum_pct'] <= threshold).sum() + 1
        pct_reduction = (1 - n_features / len(feature_names)) * 100
        print(f"{threshold}% of importance captured by {n_features:3d} features ({pct_reduction:5.1f}% reduction)")
    
    # Visualizations
    if MATPLOTLIB_AVAILABLE:
        try:
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # Plot 1: Top 30 features
            ax1 = axes[0, 0]
            top_30 = importance_df.head(30)
            ax1.barh(range(len(top_30)), top_30['importance'])
            ax1.set_yticks(range(len(top_30)))
            ax1.set_yticklabels(top_30['feature'], fontsize=8)
            ax1.set_xlabel('Importance Score')
            ax1.set_title('Top 30 Most Important Features')
            ax1.invert_yaxis()
            
            # Plot 2: Feature type distribution
            ax2 = axes[0, 1]
            type_importance = {}
            for ftype, df in feature_types.items():
                if len(df) > 0:
                    type_importance[ftype] = df['importance'].sum()
            
            ax2.bar(range(len(type_importance)), list(type_importance.values()))
            ax2.set_xticks(range(len(type_importance)))
            ax2.set_xticklabels(list(type_importance.keys()), rotation=45, ha='right')
            ax2.set_ylabel('Total Importance')
            ax2.set_title('Feature Type Contribution to Predictions')
            
            # Plot 3: Cumulative importance curve
            ax3 = axes[1, 0]
            ax3.plot(range(len(importance_df)), importance_df['cumsum_pct'], linewidth=2)
            ax3.axhline(y=90, color='r', linestyle='--', label='90% threshold')
            ax3.axhline(y=95, color='orange', linestyle='--', label='95% threshold')
            ax3.set_xlabel('Number of Features (ranked by importance)')
            ax3.set_ylabel('Cumulative Importance %')
            ax3.set_title('Cumulative Feature Importance')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # Plot 4: Importance distribution
            ax4 = axes[1, 1]
            ax4.hist(importances, bins=50, edgecolor='black', alpha=0.7)
            ax4.set_xlabel('Importance Score')
            ax4.set_ylabel('Number of Features')
            ax4.set_title('Distribution of Feature Importance Scores')
            ax4.axvline(importances.mean(), color='r', linestyle='--', label=f'Mean: {importances.mean():.6f}')
            ax4.legend()
            
            plt.tight_layout()
            fig_path = OUTPUTS_DIR / "feature_importance_analysis.png"
            plt.savefig(fig_path, dpi=150, bbox_inches='tight')
            print(f"\n✓ Saved visualization: {fig_path}")
            
        except Exception as e:
            print(f"\nNote: Could not generate plots ({e})")
    else:
        print("\n(matplotlib not available - skipping visualizations)")
    
    # Save detailed analysis to CSV
    out_csv = OUTPUTS_DIR / "feature_importance_detailed.csv"
    importance_df.to_csv(out_csv, index=False)
    print(f"✓ Saved detailed analysis: {out_csv}")
    
    return importance_df

if __name__ == "__main__":
    importance_df = analyze_feature_importance()
