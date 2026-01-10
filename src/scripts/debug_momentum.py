"""Debug why momentum features aren't being used in model_v2"""
from pathlib import Path
import sys

import pandas as pd
import warnings

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR
from models.model_v2 import NFLHybridModelV2

workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
model = NFLHybridModelV2(workbook_path=workbook, model_type='randomforest')

# Load data
games, team_games, odds = model.load_workbook()

# Get candidate features
feats = model._candidate_features(team_games)
print(f"Candidate features: {len(feats)}")
print(f"Features: {sorted(feats)}\n")

# Prepare data like fit() does
g = games[["game_id", "week", "home_team", "away_team", "home_score", "away_score", "neutral_site (0/1)"]].copy()
g["week"] = pd.to_numeric(g["week"], errors="coerce").astype(int)
tg = team_games.merge(g[["game_id", "week"]], on="game_id", how="left", validate="many_to_one")
tg["is_home (0/1)"] = pd.to_numeric(tg["is_home (0/1)"], errors="coerce").fillna(0).astype(int)

# Add rolling features
print("Adding rolling features...")
tg_roll = model._add_rolling_features(tg, feats)
print(f"After rolling: {tg_roll.shape}")

# Check what columns were added
roll_cols = [c for c in tg_roll.columns if "_pre" in c]
print(f"Rolling columns: {len(roll_cols)}")

# Add momentum features
print("\nAdding momentum features...")
tg_momentum = model._add_momentum_features(tg_roll, feats)
print(f"After momentum: {tg_momentum.shape}")

# Check what columns were added
momentum_cols = [c for c in tg_momentum.columns if any(x in c for x in ["_ema", "_trend", "_vol", "_season_avg", "_recent_ratio"])]
print(f"Momentum columns added: {len(momentum_cols)}")
if momentum_cols:
    print(f"Sample momentum columns: {momentum_cols[:5]}")

# Check for NaN in momentum features
for col in momentum_cols[:10]:
    nan_pct = tg_momentum[col].isna().sum() / len(tg_momentum) * 100
    print(f"  {col:45s} NaN: {nan_pct:6.1f}%")

print("\n=== FEATURE SELECTION IN FIT ===")
# Now see what happens when we prepare X and Y
g = games[["game_id", "week", "home_team", "away_team", "home_score", "away_score", "neutral_site (0/1)"]].copy()
g["week"] = pd.to_numeric(g["week"], errors="coerce").astype(int)
g["margin_home"] = g["home_score"] - g["away_score"]
g["total_points"] = g["home_score"] + g["away_score"]

# Prepare features like fit() does - THIS IS THE KEY PART
pre_cols = [f"{c}_pre{model.window}" for c in feats]
ema_cols = [f"{c}_ema{model.window}" for c in feats]
trend_cols = [f"{c}_trend{model.window}" for c in feats]
vol_cols = [f"{c}_vol{model.window}" for c in feats]
season_cols = [f"{c}_season_avg" for c in feats]
ratio_cols = [f"{c}_recent_ratio" for c in feats]

print(f"Expected columns:")
print(f"  pre_cols: {len(pre_cols)}")
print(f"  ema_cols: {len(ema_cols)}")
print(f"  trend_cols: {len(trend_cols)}")
print(f"  vol_cols: {len(vol_cols)}")
print(f"  season_cols: {len(season_cols)}")
print(f"  ratio_cols: {len(ratio_cols)}")
print(f"  Total momentum features: {len(ema_cols) + len(trend_cols) + len(vol_cols) + len(season_cols) + len(ratio_cols)}")

# Try to select features from tg_momentum
home_feat = tg_momentum[tg_momentum["is_home (0/1)"] == 1][
    ["game_id", "team"] + pre_cols + ema_cols + trend_cols + vol_cols + season_cols + ratio_cols
].rename(columns={"team": "home_team"})

print(f"\nHome features shape: {home_feat.shape}")
print(f"Home feature columns selected: {len(home_feat.columns)}")
print(f"Missing columns (KeyError expected if any): ", end="")

# Check which columns are actually in tg_momentum
available_ema = [c for c in ema_cols if c in tg_momentum.columns]
available_trend = [c for c in trend_cols if c in tg_momentum.columns]
available_vol = [c for c in vol_cols if c in tg_momentum.columns]
available_season = [c for c in season_cols if c in tg_momentum.columns]
available_ratio = [c for c in ratio_cols if c in tg_momentum.columns]

print(f"\nActually available columns in tg_momentum:")
print(f"  ema_cols: {len(available_ema)}")
print(f"  trend_cols: {len(available_trend)}")
print(f"  vol_cols: {len(available_vol)}")
print(f"  season_cols: {len(available_season)}")
print(f"  ratio_cols: {len(available_ratio)}")
print(f"  Total available momentum: {len(available_ema) + len(available_trend) + len(available_vol) + len(available_season) + len(available_ratio)}")

# The problem!
missing_ema = [c for c in ema_cols if c not in tg_momentum.columns]
if missing_ema:
    print(f"\nMISSING EMA columns: {missing_ema[:5]}")
