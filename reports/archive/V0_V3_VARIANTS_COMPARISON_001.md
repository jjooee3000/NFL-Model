# v0 vs v3 Comparison — Run 001 (train_week=14, 2026-01-10)

Summary
- Both v3 variants beat v0 on the holdout set.
- v3_default is best here; v3_tuned_stacked is slightly worse but still ahead of v0.

Accuracy (lower MAE is better)
- v0_baseline: margin MAE 11.254, total MAE 13.849
- v3_default: margin MAE 9.914 (≈11.9% better vs v0), total MAE 10.872 (≈21.5% better vs v0)
- v3_tuned_stacked: margin MAE 10.281 (≈8.6% better vs v0), total MAE 11.312 (≈18.3% better vs v0)

Efficiency
- Training time v0: 2.78s
- Training time v3_default: 4.47s | Features: 248 | Window: 8 | Stacking: off
- Training time v3_tuned_stacked: 6.87s | Features: 248 | Window: 8 | Stacking: on (tuned params loaded from reports/tuning_v3.json)

Plain terms
- MAE is the average miss in points; lower means predictions are closer to actual scores.
- v3 uses more signals (momentum + market line moves). In this run, the default v3 edged out the tuned+stacked variant, but both were better than v0.

Reproduce
- From repo root: `python src/scripts/compare_v0_v3.py --train-week 14 --use-best-params --use-stacking`
