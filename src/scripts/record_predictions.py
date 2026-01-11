"""
Generate and log v3 holdout predictions to outputs/prediction_log.csv, then optionally rerun tuning.

Usage:
  python src/scripts/record_predictions.py --train-week 14 --variant default
  python src/scripts/record_predictions.py --train-week 14 --variant tuned --use-best-params --stacking
  python src/scripts/record_predictions.py --train-week 14 --variant tuned --tune-v3 --stacking --run-tuning
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, OUTPUTS_DIR, REPORTS_DIR, ensure_dir  # noqa: E402
from models.model_v3 import NFLHybridModelV3  # noqa: E402


DEFAULT_WORKBOOK = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
PREDICTION_LOG = OUTPUTS_DIR / "prediction_log.csv"


def load_best_params() -> tuple[int, dict | None, dict | None]:
    params_path = REPORTS_DIR / "tuning_v3.json"
    if not params_path.exists():
        return 8, None, None
    with params_path.open("r", encoding="utf-8") as f:
        best = json.load(f)
    window = int(best.get("window", 8))
    return window, best.get("margin_params"), best.get("total_params")


def append_predictions(df: pd.DataFrame, log_path: Path) -> None:
    ensure_dir(log_path.parent)
    mode = "a" if log_path.exists() else "w"
    header = not log_path.exists()
    df.to_csv(log_path, mode=mode, index=False, header=header)


def run_tuning() -> None:
    script_path = ROOT / "src" / "scripts" / "tune_v3.py"
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Tuning script failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train v3, log holdout predictions, optional tuning")
    parser.add_argument("--train-week", type=int, default=14, help="Train through week N (default: 14)")
    parser.add_argument("--variant", choices=["default", "tuned"], default="default", help="Model variant to log")
    parser.add_argument("--use-best-params", action="store_true", help="Load best params/window from reports/tuning_v3.json")
    parser.add_argument("--tune-v3", action="store_true", help="Run GridSearchCV before predicting (randomforest only)")
    parser.add_argument("--stacking", action="store_true", help="Use RF+GBDT stacking")
    parser.add_argument("--workbook", type=str, default=str(DEFAULT_WORKBOOK), help="Workbook path")
    parser.add_argument("--run-tuning", action="store_true", help="After logging predictions, rerun tuning script")
    args = parser.parse_args()

    train_week = int(args.train_week)
    workbook = Path(args.workbook)
    window = 8
    rf_params_margin = None
    rf_params_total = None

    if args.use_best_params:
        window, rf_params_margin, rf_params_total = load_best_params()
        print(f"Loaded tuned params from reports/tuning_v3.json (window={window})")

    model = NFLHybridModelV3(workbook_path=str(workbook), window=window, model_type="randomforest")

    params_source = "default"
    if args.use_best_params:
        params_source = "best_file"
    elif args.tune_v3:
        params_source = "grid_search"

    print("\n=== Training and logging v3 predictions ===")
    print(f"Workbook: {workbook}")
    print(f"Train through week: {train_week}")
    print(f"Variant: {args.variant}")
    print(f"Stacking: {'on' if args.stacking else 'off'}")
    print(f"Params source: {params_source}")

    report = model.fit(
        train_through_week=train_week,
        tune_hyperparams=args.tune_v3,
        rf_params_margin=rf_params_margin,
        rf_params_total=rf_params_total,
        stack_models=args.stacking,
        return_predictions=True,
    )

    preds = report.get("predictions")
    if preds is None or preds.empty:
        print("No holdout games to log (no games beyond train_week).")
        return

    run_ts = datetime.utcnow().isoformat() + "Z"
    preds = preds.copy()
    preds["run_timestamp_utc"] = run_ts
    preds["model_variant"] = args.variant
    preds["params_source"] = params_source
    preds["stacking"] = bool(args.stacking)
    preds["rf_params_loaded"] = bool(rf_params_margin or rf_params_total)

    ts_safe = run_ts.replace(":", "-")
    snapshot_path = OUTPUTS_DIR / f"predictions_v3_{args.variant}_week{train_week}_{ts_safe}.csv"

    print(f"Writing snapshot: {snapshot_path}")
    ensure_dir(snapshot_path.parent)
    preds.to_csv(snapshot_path, index=False)

    print(f"Appending to log: {PREDICTION_LOG}")
    append_predictions(preds, PREDICTION_LOG)

    if args.run_tuning:
        print("\n--- Running tuning after logging ---")
        run_tuning()

    print("\nDone.")


if __name__ == "__main__":
    main()
