# NFL Model Performance Comparison: v0 → v1 → v2

## Test Results (CHI vs GNB Example, Week 19)

### Performance Metrics (Lower = Better)

| Metric | v0 (Ridge) | v1 (RF) | v2 (RF+Momentum) | Improvement |
|--------|-----------|---------|-----------------|-------------|
| **Margin MAE** | 11.17 | 10.51 | **10.26** | ✅ 8% better than v0 |
| **Total MAE** | 12.07 | 11.46 | 12.28 | ⚠️ Slight regression |
| **N Features** | 44 | 44 | **234** | Rich feature set |
| **Model Type** | Ridge | RandomForest | RandomForest | Non-linear |

### Prediction Outputs (CHI -1.5, Total 44.5)

| Output | v0 | v1 | v2 | Market |
|--------|----|----|----|----|
| **Spread (away)** | +7.17 | -0.88 | +0.80 | -1.50 |
| **Total** | 45.71 | 44.38 | 46.49 | 44.50 |
| **Win% Home** | 30.5% | 52.5% | 47.7% | 46.8% |
| **Win% Away** | 69.5% | 47.5% | 52.3% | 53.2% |
| **Edge (Spread)** | +8.67 | +0.62 | +2.30 | - |

---

## Key Insights

### ✅ What Worked
1. **v1 RandomForest improvement**: 6% better margin MAE than Ridge baseline
2. **v2 Momentum boost**: 2% additional improvement (8% total)
3. **Feature engineering**: 234 features (vs 44) now capture momentum, trends, volatility
4. **Predictions converging**: v2 closer to market consensus = more calibrated

### ⚠️ What to Watch
1. **Total MAE increased in v2**: Momentum features help margins but not totals
   - Suggests margin and total predictions need different feature sets
   - Consider separate tuning per target

2. **Feature fragmentation warning**: Can optimize feature building for speed
   - Not a problem for accuracy, just performance

3. **v2 still reasonable**: Edge of +2.30 on spread is realistic and defensible

---

## Momentum Features Added in v2

1. **Exponential Moving Average (EMA)**
   - Weights recent games ~2x more than older games
   - Captures hot/cold streaks better than rolling mean

2. **Trend (Linear Slope)**
   - Direction of performance change
   - Team improving vs declining

3. **Volatility**
   - Consistency measure (std dev / mean)
   - Identifies streaky vs stable teams

4. **Season-to-date Average**
   - Long-term quality baseline
   - Early season games still matter

5. **Recent/Season Ratio**
   - How much recent form differs from season average
   - Identifies regression to mean opportunities

---

## Recommendations for Next Phase

### Short-term (Easy Wins)
1. **Separate models by target**: Build distinct margin vs total models with tuned features
   - v2 margin works great, optimize total separately
   
2. **Hyperparameter tuning**: Grid search on tree depth, learning rates
   - Could squeeze another 2-3% accuracy

3. **Cross-validation**: Validate across 2023-2024 seasons
   - Ensure 2025 improvements generalize

### Medium-term (Feature Optimization)
1. **Drop low-importance features**: Identify which 234 actually matter
   - RandomForest feature_importances_ tells us what helps
   
2. **Add context features**: Rest days, travel, home field more sophisticated
   - Current model only uses neutral_site flag

3. **Market integration**: Penalize predictions far from market
   - Smart regularization: "be suspicious if you disagree with market"

---

## Usage

```bash
# v0: Ridge baseline
python model_v0.py --home CHI --away GNB --close_spread_home 1.5 --close_total 44.5 --close_ml_home 105 --close_ml_away -125

# v1: RandomForest (best v0→v1 jump)
python model_v1.py --model randomforest --home CHI --away GNB --close_spread_home 1.5 --close_total 44.5 --close_ml_home 105 --close_ml_away -125

# v2: RandomForest + Momentum Features (best overall margin prediction)
python model_v2.py --model randomforest --home CHI --away GNB --close_spread_home 1.5 --close_total 44.5 --close_ml_home 105 --close_ml_away -125

# Compare all models
for model in model_v0.py model_v1.py model_v2.py; do
  echo "Testing $model..."
  python $model --model randomforest --home CHI --away GNB --close_spread_home 1.5 --close_total 44.5 --close_ml_home 105 --close_ml_away -125
done
```

---

## Files
- `model_v0.py` - Ridge linear baseline (optimized)
- `model_v1.py` - Non-linear models (Ridge, XGBoost, LightGBM, RandomForest)
- `model_v2.py` - v1 + Momentum/Trend features (234 total features)
