from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR
from models.model_v0 import fetch_market_data_from_odds_api, ensemble_predict_game

API_KEY = "e4fe23404e83e54cae3a61eff5772094"
HOME = "CHI"
AWAY = "GNB"

try:
    spread, total, ml_home, ml_away = fetch_market_data_from_odds_api(HOME, AWAY, API_KEY)
    print(f"Fetched market: spread(home)={spread}, total={total}, ml_home={ml_home}, ml_away={ml_away}")
except Exception as e:
    raise SystemExit(f"Market fetch failed: {e}")

pred, report = ensemble_predict_game(
    home=HOME,
    away=AWAY,
    close_spread_home=spread,
    close_total=total,
    close_ml_home=ml_home,
    close_ml_away=ml_away,
    windows=[4,6,8,10,12],
    method="weighted",
    train_through_week=14,
    as_of_week=19,
    workbook=DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx",
)

out = {"prediction": pred, "ensemble_report": report}
print(json.dumps(out, indent=2))
