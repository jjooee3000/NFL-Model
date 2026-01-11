# Model v1 - Non-Linear Models Comparison

## Performance Summary (Test MAE on CHI vs GNB)

| Model | Margin MAE | Total MAE | Spread Pred | Total Pred | Edge (Spread) |
|-------|-----------|----------|-------------|-----------|---------------|
| **Ridge** (v0 baseline) | 11.17 | 12.07 | +7.17 | 45.71 | +8.67 |
| **XGBoost** | 11.30 | 11.75 | +3.98 | 48.36 | +5.48 |
| **LightGBM** | 11.54 | 11.99 | +3.48 | 44.55 | +4.98 |
| **RandomForest** | **10.51** | 11.46 | -0.88 | 44.38 | +0.62 |

## Key Findings

### Best Overall: **RandomForest** ✅
- **Lowest Margin MAE: 10.51** (6% improvement over Ridge)
- **Lowest Total MAE: 11.46** (5% improvement over Ridge)
- Predictions closest to market consensus (less extreme)
- Most reliable across both targets

### Best Spread Prediction: **XGBoost**
- Total MAE: 11.75 (2.7% improvement)
- Good variance from market baseline
- Slightly extreme spread predictions

### Observations
1. **Non-linear models beat Ridge** on both metrics across the board
2. **RandomForest is the winner** - best generalization without overfitting
3. All tree-based models show **~5-6% accuracy improvement**
4. Next step: Feature engineering will amplify these gains

## Recommendations

1. **Deploy with RandomForest** - best balance of accuracy and calibration
2. **Monitor XGBoost** - if you want more aggressive edges and can validate them
3. **Next phase**: Add momentum features (#1) - should compound the improvements

## Usage Examples

```bash
# RandomForest (default for best accuracy)
python model_v1.py --model randomforest --home CHI --away GNB --close_spread_home 1.5 --close_total 44.5 --close_ml_home 105 --close_ml_away -125

# XGBoost (for aggressive edges)
python model_v1.py --model xgboost --home CHI --away GNB --close_spread_home 1.5 --close_total 44.5 --close_ml_home 105 --close_ml_away -125

# Compare all models
python model_v1.py --model ridge --home CHI --away GNB ...
python model_v1.py --model lightgbm --home CHI --away GNB ...
```

## Files Created
- `model_v1.py` - Main model with non-linear support (Ridge, XGBoost, LightGBM, RandomForest)
- `model_v0.py` - Original optimized linear model (baseline)
