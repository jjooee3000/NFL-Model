# v0 vs v3 Comparison (Holdout Accuracy & Efficiency)

## Summary
- v3 (both variants) beat v0 on the holdout set for both margin and total MAE.
- In this run, the tuned/stacked v3 is slightly worse than the default v3, but both variants outperform v0.

## Accuracy (lower is better)
- v3_default: Margin MAE = 9.914 (vs v0: +11.9%), Total MAE = 10.872 (vs v0: +21.5%)
- v3_tuned: Margin MAE = 10.281 (vs v0: +8.6%), Total MAE = 11.312 (vs v0: +18.3%)

What this means in plain terms:
- MAE measures average error size. A lower number means the model’s predictions are closer to the actual results.
- v3 variants have lower MAE, meaning they are better at predicting both the margin (spread) and total points than v0.

## Efficiency (training time & features)
- Training time (v0): 2.78s
- Training time (v3_default): 4.47s | Features: 248 | Window: 8 | Stacking: off
- Training time (v3_tuned): 6.87s | Features: 248 | Window: 8 | Stacking: on

In plain terms:
- v3 looks at more information (more features), including team momentum and market line movement.
- The tuned/stacked variant takes longer; in this run it was slightly worse than the default v3, though both beat v0.

## Notes
- Both models trained on the same weeks and were tested on later games to avoid lookahead bias.
- v3 can optionally run time-series hyperparameter tuning and stacking, which improve accuracy at a cost of extra time.
