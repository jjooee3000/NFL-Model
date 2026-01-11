#!/usr/bin/env python3
"""Debug postgame evaluation matching"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.pfr_scraper import PFRScraper
from models.archive.model_v2 import _TEAM_CODE_TO_NAME as CODE_TO_NAME

OUT_DIR = ROOT / "outputs"

# Load postgame results
postgame_path = OUT_DIR / "postgame_results_2026-01-10.csv"
postgame_df = pd.read_csv(postgame_path)
print("Postgame results:")
print(postgame_df)
print()

# Load predictions
pred_files = [
    OUT_DIR / "predictions_rams_panthers_2026-01-10.csv",
    OUT_DIR / "predictions_v3_rams_panthers_2026-01-10.csv",
    OUT_DIR / "predictions_playoffs_week1_2026-01-10.csv",
]

predictions = []
for f in pred_files:
    if f.exists():
        try:
            df = pd.read_csv(f)
            df['source_file'] = f.name
            predictions.append(df)
            print(f"Loaded {f.name}: {len(df)} rows, columns: {list(df.columns)[:10]}")
        except Exception as e:
            print(f"Error loading {f.name}: {e}")

if predictions:
    preds_df = pd.concat(predictions, ignore_index=True)
    print(f"\nCombined predictions: {len(preds_df)} rows")
    print(f"Columns: {list(preds_df.columns)[:15]}")
    print(f"\nSample away_team values: {preds_df['away_team'].unique()}")
    print(f"Sample home_team values: {preds_df['home_team'].unique()}")
    
    # Try matching logic
    NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
    
    for col in ['home_team','away_team']:
        if col in preds_df.columns:
            print(f"\nBefore mapping {col}: {preds_df[col].unique()}")
            preds_df[col] = preds_df[col].map(NAME_TO_CODE).fillna(preds_df[col])
            print(f"After mapping {col}: {preds_df[col].unique()}")
    
    # Create keys
    preds_df['key'] = preds_df['away_team'] + '|' + preds_df['home_team']
    print(f"\nPrediction keys: {preds_df['key'].unique()}")
    
    # Postgame keys
    postgame_df['key'] = postgame_df['away_team'] + '|' + postgame_df['home_team']
    print(f"Postgame keys: {postgame_df['key'].unique()}")
    
    # Try merge
    merged = preds_df.merge(postgame_df[['key','margin_home','total_points']], on='key', how='left')
    print(f"\nMerged result: {len(merged)} rows")
    print(f"Columns with data: {[c for c in ['key','margin_home','total_points','pred_margin_home','pred_total'] if c in merged.columns]}")
    print("\nSample merged rows:")
    print(merged[['key','pred_margin_home','margin_home','pred_total','total_points']].head(10))
