"""Compare MAE: v3 (2025-only) vs v4 (2020–2025 historical)"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR
from models.model_v3 import NFLHybridModelV3
from models.model_v4 import NFLModelV4

v3_workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
v4_workbook = DATA_DIR / "nfl_model_data_historical_integrated.xlsx"

print("\n" + "="*80)
print("COMPARISON: v3 vs v4")
print("="*80 + "\n")

results = []

# v3
m3 = NFLHybridModelV3(workbook_path=v3_workbook, model_type='randomforest', prefer_sqlite=True)
rep3 = m3.fit()
results.append({
    'Version': 'V3',
    'Features': rep3['n_features'],
    'Margin MAE (test)': rep3['margin_MAE_test'],
    'Total MAE (test)': rep3['total_MAE_test'],
})

# v4
m4 = NFLModelV4(workbook_path=v4_workbook, model_type='randomforest')
rep4 = m4.fit()
results.append({
    'Version': 'V4',
    'Features': rep4['n_features'],
    'Margin MAE (test)': rep4['margin_MAE_test'],
    'Total MAE (test)': rep4['total_MAE_test'],
})

print(pd.DataFrame(results).to_string(index=False))

print("\n" + "="*80)
print("ANALYSIS")
print("="*80 + "\n")
print(f"v3 -> v4 (Margin MAE): {(results[0]['Margin MAE (test)'] - results[1]['Margin MAE (test)'])/results[0]['Margin MAE (test)']*100:+.1f}%")
print(f"v3 -> v4 (Total MAE): {(results[0]['Total MAE (test)'] - results[1]['Total MAE (test)'])/results[0]['Total MAE (test)']*100:+.1f}%")

print("\n" + "="*80)