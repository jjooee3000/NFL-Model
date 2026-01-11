"""
Project diagnostics: environment, data, and model v3 sanity checks.
Run from repo root: `python src/scripts/diagnostics.py`
"""
from pathlib import Path
import sys
import traceback

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

print("\n=== NFL Model Diagnostics ===")
print(f"Project root: {ROOT}")

# Check Python and packages
try:
    import platform
    import pandas as pd
    import numpy as np
    import sklearn
    import openpyxl
    import joblib
    print(f"Python: {platform.python_version()}")
    print(f"pandas: {pd.__version__}")
    print(f"numpy: {np.__version__}")
    print(f"scikit-learn: {sklearn.__version__}")
    print(f"openpyxl: {openpyxl.__version__}")
    print(f"joblib: {joblib.__version__}")
except Exception as e:
    print("Package check failed:", e)

# Paths and data checks
from utils.paths import DATA_DIR, OUTPUTS_DIR, ensure_dir
wb_path = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
print(f"\nData workbook: {wb_path}")
if not wb_path.exists():
    print("! Workbook missing. Place the Excel file in data/.")
else:
    try:
        import pandas as pd
        games = pd.read_excel(wb_path, sheet_name="games")
        team_games = pd.read_excel(wb_path, sheet_name="team_games")
        odds = pd.read_excel(wb_path, sheet_name="odds")
        print(f"games rows: {len(games)} | team_games rows: {len(team_games)} | odds rows: {len(odds)}")
        # Required columns check
        required_games = {"game_id","week","home_team","away_team","home_score","away_score","neutral_site (0/1)"}
        required_team_games = {"game_id","team","is_home (0/1)"}
        required_odds = {"game_id","close_spread_home","close_total","open_spread_home","open_total","close_ml_home","close_ml_away"}
        def missing(cols, df):
            return [c for c in cols if c not in df.columns]
        mg = missing(required_games, games)
        mtg = missing(required_team_games, team_games)
        mo = missing(required_odds, odds)
        if mg or mtg or mo:
            print("! Missing columns:")
            if mg: print("  games:", mg)
            if mtg: print("  team_games:", mtg)
            if mo: print("  odds:", mo)
        else:
            print("✓ Required columns present in all sheets.")
    except Exception as e:
        print("Error reading workbook:", e)
        traceback.print_exc()

# Model v3 fit sanity
try:
    from models.model_v3 import NFLHybridModelV3
    ensure_dir(OUTPUTS_DIR)
    model = NFLHybridModelV3(workbook_path=str(wb_path), window=8, model_type="randomforest", prefer_sqlite=True)
    if wb_path.exists():
        print("\nFitting model_v3 for sanity (train through week 14)...")
        rpt = model.fit(train_through_week=14)
        print("Fit report:")
        for k, v in rpt.items():
            print(f"  {k:24s}: {v}")
        # Write diagnostics output
        out_path = OUTPUTS_DIR / "diagnostics.txt"
        with out_path.open("w", encoding="utf-8") as f:
            f.write("MODEL_V3 DIAGNOSTICS\n")
            for k, v in rpt.items():
                f.write(f"{k}: {v}\n")
        print(f"\n✓ Wrote diagnostics: {out_path}")
    else:
        print("\nSkipping model fit (workbook absent).")
except Exception as e:
    print("! Model v3 fit failed:", e)
    traceback.print_exc()

print("\n=== Diagnostics complete ===")
