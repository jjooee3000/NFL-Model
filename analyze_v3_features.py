"""
Feature importance analysis for model_v3
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from model_v3 import NFLHybridModelV3

workbook = r"C:\Users\cahil\OneDrive\Desktop\Sports Model\NFL-Model\nfl_2025_model_data_with_moneylines.xlsx"
model = NFLHybridModelV3(workbook_path=workbook, model_type='randomforest')
model.fit()

# Extract feature importances
margin_model = model._artifacts.m_margin
feature_names = model._artifacts.features
importances = margin_model.feature_importances_

print(f"\n{'='*80}")
print(f"MODEL_V3 FEATURE IMPORTANCE ANALYSIS")
print(f"{'='*80}\n")

print(f"Total features: {len(feature_names)}")
print(f"Total importances: {len(importances)}")

if len(feature_names) != len(importances):
    min_len = min(len(feature_names), len(importances))
    feature_names = feature_names[:min_len]
    importances = importances[:min_len]

# Create importance dataframe
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': importances,
    'importance_pct': importances / importances.sum() * 100
}).sort_values('importance', ascending=False)

print(f"\nTotal importance sum: {importances.sum():.6f}")
print(f"Average importance per feature: {importances.mean():.6f}")

# Top 25 features
print(f"\n{'='*80}")
print(f"TOP 25 MOST IMPORTANT FEATURES")
print(f"{'='*80}\n")
for idx, row in importance_df.head(25).iterrows():
    feat_type = ""
    if "_ema" in row['feature']:
        feat_type = "[EMA]"
    elif "_trend" in row['feature']:
        feat_type = "[TREND]"
    elif "_vol" in row['feature']:
        feat_type = "[VOL]"
    elif "_season_avg" in row['feature']:
        feat_type = "[SEASON]"
    elif "_recent_ratio" in row['feature']:
        feat_type = "[RATIO]"
    elif "_pre" in row['feature']:
        feat_type = "[BASE]"
    
    print(f"{row['feature']:45s} {feat_type:8s} | {row['importance']:10.6f} | {row['importance_pct']:6.2f}%")

# Feature type breakdown
print(f"\n{'='*80}")
print(f"FEATURE TYPE BREAKDOWN")
print(f"{'='*80}\n")

feature_types = {
    'base_rolling': importance_df[importance_df['feature'].str.contains('_pre', na=False)],
    'ema_momentum': importance_df[importance_df['feature'].str.contains('_ema', na=False)],
    'trend_momentum': importance_df[importance_df['feature'].str.contains('_trend', na=False)],
    'volatility': importance_df[importance_df['feature'].str.contains('_vol', na=False)],
    'season_avg': importance_df[importance_df['feature'].str.contains('_season_avg', na=False)],
    'recent_ratio': importance_df[importance_df['feature'].str.contains('_recent_ratio', na=False)],
    'market': importance_df[importance_df['feature'].str.contains('spread|total|imp_p', na=False)],
    'other': importance_df[~importance_df['feature'].str.contains('_pre|_ema|_trend|_vol|_season_avg|_recent_ratio|spread|total|imp_p|neutral', na=False)],
}

for ftype, df in feature_types.items():
    if len(df) > 0:
        total_imp = df['importance'].sum()
        pct = total_imp / importances.sum() * 100
        avg_imp = df['importance'].mean()
        print(f"{ftype:25s} | Count: {len(df):3d} | Total Imp: {total_imp:10.6f} | Pct: {pct:6.2f}% | Avg: {avg_imp:10.6f}")

# Cumulative importance
print(f"\n{'='*80}")
print(f"CUMULATIVE IMPORTANCE THRESHOLDS")
print(f"{'='*80}\n")

importance_df['cumsum_pct'] = importance_df['importance'].cumsum() / importances.sum() * 100

for threshold in [50, 75, 90, 95, 99]:
    n_features = (importance_df['cumsum_pct'] <= threshold).sum() + 1
    pct_reduction = (1 - n_features / len(feature_names)) * 100
    print(f"{threshold}% captured by {n_features:3d} features ({pct_reduction:5.1f}% reduction possible)")

# Check if momentum features are now being used
momentum_cols = importance_df[importance_df['feature'].str.contains('_ema|_trend|_vol|_season_avg|_recent_ratio', na=False)]
print(f"\n{'='*80}")
print(f"MOMENTUM FEATURES STATUS")
print(f"{'='*80}\n")
print(f"Total momentum features: {len(momentum_cols)}")
print(f"Momentum importance: {momentum_cols['importance'].sum():.6f} ({momentum_cols['importance'].sum()/importances.sum()*100:.1f}%)")
print(f"Status: {'WORKING' if len(momentum_cols) > 50 else 'NOT WORKING - still missing!'}")

importance_df.to_csv('feature_importance_v3.csv', index=False)
print(f"\nSaved: feature_importance_v3.csv")
