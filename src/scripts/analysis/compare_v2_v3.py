"""
Compare v2 (momentum bugged) vs v3 variants (default/tuned/stacked).
Run: python src/scripts/compare_v2_v3.py [--train-week 14] [--tune-v3] [--use-stacking] [--use-best-params]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys
import warnings

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.paths import DATA_DIR, REPORTS_DIR, ensure_dir  # noqa: E402
from models.archive.model_v2 import NFLHybridModelV2 as V2Model  # noqa: E402
from models.model_v3 import NFLHybridModelV3 as V3Model  # noqa: E402


def fmt_improve(base: float, new: float) -> float:
    return (base - new) / base * 100.0 if base and base == base else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare v2 vs v3 variants on holdout accuracy and runtime")
    parser.add_argument("--train-week", type=int, default=14, help="Train through week N (default: 14)")
    parser.add_argument("--tune-v3", action="store_true", help="Enable v3 time-series hyperparameter tuning")
    parser.add_argument("--use-stacking", action="store_true", help="Use RF+GBDT stacking for the tuned v3 variant")
    parser.add_argument(
        "--use-best-params",
        action="store_true",
        help="Load best params/window from reports/tuning_v3.json for tuned v3 variant",
    )
    args = parser.parse_args()

    workbook = DATA_DIR / "nfl_2025_model_data_with_moneylines.xlsx"
    ensure_dir(REPORTS_DIR)

    print("\n=== Comparing v2 vs v3 variants ===")
    print(f"Workbook: {workbook}")
    print(f"Train through week: {args.train_week}")

    # v2 baseline (random forest with momentum bug)
    v2 = V2Model(workbook_path=str(workbook), window=8, model_type="randomforest")
    start = time.perf_counter()
    v2_report = v2.fit(train_through_week=args.train_week)
    v2_time = time.perf_counter() - start

    rf_params_margin = None
    rf_params_total = None
    v3_window = 8

    if args.use_best_params:
        params_path = REPORTS_DIR / "tuning_v3.json"
        if params_path.exists():
            with params_path.open("r", encoding="utf-8") as f:
                best = json.load(f)
            v3_window = int(best.get("window", v3_window))
            rf_params_margin = best.get("margin_params")
            rf_params_total = best.get("total_params")
            print(f"Using tuned params and window from {params_path}: window={v3_window}")
        else:
            print(f"No tuned params file found at {params_path}; proceeding with defaults.")

    variants = []

    # v3 default
    v3_default = V3Model(workbook_path=str(workbook), window=8, model_type="randomforest")
    start = time.perf_counter()
    v3_default_report = v3_default.fit(
        train_through_week=args.train_week,
        tune_hyperparams=False,
        stack_models=False,
    )
    v3_default_time = time.perf_counter() - start
    variants.append(("v3_default", v3_default_report, v3_default_time, 8, False, False))

    # v3 tuned/stacked variant (current best)
    v3_tuned = V3Model(workbook_path=str(workbook), window=v3_window, model_type="randomforest")
    start = time.perf_counter()
    v3_tuned_report = v3_tuned.fit(
        train_through_week=args.train_week,
        tune_hyperparams=args.tune_v3,
        rf_params_margin=rf_params_margin,
        rf_params_total=rf_params_total,
        stack_models=args.use_stacking,
    )
    v3_tuned_time = time.perf_counter() - start
    variants.append(("v3_tuned", v3_tuned_report, v3_tuned_time, v3_window, args.use_stacking, bool(rf_params_margin or rf_params_total)))

    print("\nv2 report:")
    for k, v in v2_report.items():
        print(f"  {k:24s}: {v}")
    print(f"  train_time_sec            : {v2_time:.2f}")

    print("\nVariants:")
    for name, rep, tsec, win, stk, tuned_params in variants:
        print(f"\n{name}:")
        for k, v in rep.items():
            print(f"  {k:24s}: {v}")
        print(f"  train_time_sec            : {tsec:.2f}")
        print(f"  window                    : {win}")
        print(f"  stacking                  : {'on' if stk else 'off'}")
        print(f"  tuned_params_loaded       : {'yes' if tuned_params else 'no'}")

    v2_mae_margin = float(v2_report.get("margin_MAE_test", float("nan")))
    v2_mae_total = float(v2_report.get("total_MAE_test", float("nan")))

    rows = []
    for name, rep, tsec, win, stk, tuned_params in variants:
        rows.append({
            "name": name,
            "margin_mae": float(rep.get("margin_MAE_test", float("nan"))),
            "total_mae": float(rep.get("total_MAE_test", float("nan"))),
            "features": int(rep.get("n_features", 0)),
            "train_time": float(tsec),
            "window": int(win),
            "stacking": bool(stk),
            "tuned_params": bool(tuned_params),
        })

    report_path = REPORTS_DIR / "V2_V3_VARIANTS_COMPARISON.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# v2 vs v3 Variants (Holdout Accuracy & Efficiency)\n\n")
        f.write("## Summary\n")
        f.write("- v3 variants aim to fix v2’s momentum bug and expand features; this compares them head-to-head.\n")
        f.write("- Metrics are on the same train/holdout split (train through week N, test on N+). Lower MAE is better.\n\n")

        f.write("## Accuracy (lower is better)\n")
        for row in rows:
            imp_m = fmt_improve(v2_mae_margin, row["margin_mae"])
            imp_t = fmt_improve(v2_mae_total, row["total_mae"])
            f.write(
                f"- {row['name']}: Margin MAE = {row['margin_mae']:.3f} (vs v2: {imp_m:+.1f}%), "
                f"Total MAE = {row['total_mae']:.3f} (vs v2: {imp_t:+.1f}%)\n"
            )
        f.write("\n")
        f.write("What this means:\n")
        f.write("- MAE measures average error; lower is closer to actual game results.\n")
        f.write("- A positive % vs v2 means the v3 variant improved over v2.\n\n")

        f.write("## Efficiency (training time & features)\n")
        f.write(f"- Training time (v2): {v2_time:.2f}s | Features: {v2_report.get('n_features', 'n/a')}\n")
        for row in rows:
            f.write(
                f"- Training time ({row['name']}): {row['train_time']:.2f}s | Features: {row['features']} | "
                f"Window: {row['window']} | Stacking: {'on' if row['stacking'] else 'off'} | "
                f"Tuned params: {'yes' if row['tuned_params'] else 'no'}\n"
            )
        f.write("\nNotes:\n")
        f.write("- All models were trained on the same weeks to avoid lookahead bias.\n")
        f.write("- v3 can optionally run time-series hyperparameter tuning and stacking for extra accuracy.\n")

    print(f"\nWrote comparison report: {report_path}")


if __name__ == "__main__":
    main()
