# v0 vs v3 Comparison (Holdout Accuracy & Efficiency)

## Summary
- v3 predicts game margins and totals more accurately than v0 on the holdout set.
- v3 uses more advanced momentum features and market line movements; training takes longer than v0.

## Accuracy (lower is better)
- Margin MAE: v0 = 11.254, v3 = 10.281 (improvement: +8.6%)
- Total MAE:  v0 = 13.849, v3 = 11.312 (improvement: +18.3%)

What this means in plain terms:
- MAE measures average error size. A lower number means the model’s predictions are closer to the actual results.
- v3’s lower MAE means it is better at predicting both the margin (spread) and total points than v0.

## Efficiency (training time & features)
- Training time: v0 = 3.26s, v3 = 7.53s
- Features used: v0 = 168, v3 = 248
- v3 window: 8
- v3 stacking: on

In plain terms:
- v3 looks at more information (more features), including team momentum and market line movement.
- That extra information makes v3 slower to train, but it improves prediction quality.

## Notes
- Both models trained on the same weeks and were tested on later games to avoid lookahead bias.
- v3 can optionally run time-series hyperparameter tuning (disabled by default here) which may further improve accuracy at a cost of extra time.
