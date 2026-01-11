# v2 vs v3 Variants (Holdout Accuracy & Efficiency)

## Summary
- v3 variants aim to fix v2’s momentum bug and expand features; this compares them head-to-head.
- Metrics are on the same train/holdout split (train through week N, test on N+). Lower MAE is better.

## Accuracy (lower is better)
- v3_default: Margin MAE = 9.914 (vs v2: +3.4%), Total MAE = 10.872 (vs v2: +11.4%)
- v3_tuned: Margin MAE = 9.914 (vs v2: +3.4%), Total MAE = 10.872 (vs v2: +11.4%)

What this means:
- MAE measures average error; lower is closer to actual game results.
- A positive % vs v2 means the v3 variant improved over v2.

## Efficiency (training time & features)
- Training time (v2): 5.07s | Features: 234
- Training time (v3_default): 5.16s | Features: 248 | Window: 8 | Stacking: off | Tuned params: no
- Training time (v3_tuned): 5.09s | Features: 248 | Window: 8 | Stacking: off | Tuned params: no

Notes:
- All models were trained on the same weeks to avoid lookahead bias.
- v3 can optionally run time-series hyperparameter tuning and stacking for extra accuracy.
