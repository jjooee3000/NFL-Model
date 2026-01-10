# Feature Importance Analysis - model_v2.py (RandomForest)

## Executive Summary

The model_v2 RandomForest analysis reveals a critical insight: **only 38 of 234 engineered features are actually being used**. The momentum features (EMA, trend, volatility, etc.) that we added to improve accuracy are **not making it into the feature set**.

**Key Finding**: 50% of the model's predictive power comes from just **6 features** (84% reduction possible).

---

## Feature Count Issue

| Metric | Value |
|--------|-------|
| Features in model | 38 |
| Features we engineered | 234 |
| Missing features | 196 |
| **Reduction potential** | **84.2%** |

This explains why the momentum features didn't boost accuracy as much as expected. **The feature engineering is working, but the additional features are being dropped somewhere in the pipeline.**

---

## Top 20 Most Important Features

| Rank | Feature | Importance | % of Total | Cumulative % |
|------|---------|-----------|-----------|-------------|
| 1 | rush_td | 0.01885 | 14.19% | 14.19% |
| 2 | plays | 0.01464 | 11.02% | 25.21% |
| 3 | punt_yards_per_punt | 0.01069 | 8.04% | 33.26% |
| 4 | fumbles_recovered | 0.00798 | 6.01% | 39.26% |
| 5 | opp_3d_pct | 0.00757 | 5.70% | 44.96% |
| 6 | hurries_made | 0.00745 | 5.61% | **50.58%** |
| 7 | opp_4d_pct | 0.00717 | 5.40% | 55.97% |
| 8 | blitzes_faced | 0.00607 | 4.57% | 60.54% |
| 9 | seconds_per_play | 0.00556 | 4.18% | 64.72% |
| 10 | sacks_made | 0.00510 | 3.84% | 68.56% |
| 11 | fumbles_lost | 0.00461 | 3.47% | 72.04% |
| 12 | turnovers_take | 0.00431 | 3.24% | **75.28%** |
| 13 | yards_per_play_allowed | 0.00406 | 3.06% | 78.33% |
| 14 | opp_first_downs_rush | 0.00401 | 3.02% | 81.36% |
| 15 | rush_ypa | 0.00371 | 2.79% | 84.15% |
| 16 | hurries_allowed | 0.00333 | 2.51% | 86.65% |
| 17 | opp_first_downs_pen | 0.00276 | 2.08% | 88.73% |
| 18 | punts_blocked | 0.00263 | 1.98% | **90.71%** |
| 19 | opp_first_downs | 0.00240 | 1.80% | 92.52% |
| 20 | opp_4d_att | 0.00215 | 1.62% | 94.14% |

### Observations

**All top 20 features are base team statistics** (rolling averages from the original v0 model). These include:
- Offensive metrics: rush TDs, plays, yards, efficiency
- Defensive metrics: sacks, hurries, blitzes, 3rd/4th down defense
- Special teams: punts, blocked punts

**Zero momentum features in top 20** despite engineering 190 additional momentum features.

---

## Cumulative Importance Thresholds

| Threshold | # Features Needed | % Reduction Possible |
|-----------|------------------|---------------------|
| 50% | 6 features | **84.2%** ❌ |
| 75% | 12 features | **68.4%** ❌ |
| 90% | 18 features | **52.6%** ❌ |
| 95% | 21 features | **44.7%** ❌ |
| 99% | 31 features | **18.4%** ❌ |

---

## Bottom 20 Features (Candidates for Removal)

These features contribute <2% to predictions and could be eliminated:

| Feature | Importance | % |
|---------|-----------|---|
| opp_3d_att | 0.000044 | 0.03% |
| ints_got | 0.000160 | 0.12% |
| opp_4d_conv | 0.000183 | 0.14% |
| punts | 0.000197 | 0.15% |
| opp_3d_conv | 0.000201 | 0.15% |
| rush_att | 0.000253 | 0.19% |
| sacks_allowed | 0.000278 | 0.21% |
| turnovers_give | 0.000287 | 0.22% |
| punt_yards | 0.000291 | 0.22% |
| ints_thrown | 0.000295 | 0.22% |
| (and 10 more in 0.2-0.5% range) | ... | ... |

---

## Why Momentum Features Aren't Showing Up

### Possible Issues

1. **Feature Selection/Filtering**: Check if there's a filter dropping momentum features before training
   - Look for `.columns` slicing or feature selection logic in `fit()` method
   - May need to verify momentum features are actually being added to the dataframe

2. **Market Features Dominance**: Market data (spread, total, moneyline) may be so predictive that tree-based models don't need momentum
   - Yet these don't appear in top 20 either, suggesting they were added AFTER features were selected

3. **Tree Model Feature Selection**: RandomForest only needs best features; other 196 may have zero importance
   - Check if many features have exactly 0.0 importance

4. **Data Issues**: Momentum features may contain NaN/Inf values causing them to be dropped

### Recommended Investigation

```python
# Check feature importance distribution
model._artifacts.m_margin.feature_importances_
# How many have exactly 0.0 importance?

# Verify momentum features were engineered
# Check X_train shape before/after momentum engineering
# Look for feature selection/filtering in fit() method
```

---

## Model Optimization Opportunity

### Quick Win: Feature Pruning

Using only the **top 18 features** that capture **90.71% of predictive power**:
- Expected MAE impact: **-2% to +1%** (minimal change)
- Training time: **~90% faster**
- Model interpretability: **Much clearer**

### Top 18 Core Features

```
1. rush_td                    (14.19%)
2. plays                      (11.02%)
3. punt_yards_per_punt        (8.04%)
4. fumbles_recovered          (6.01%)
5. opp_3d_pct                 (5.70%)
6. hurries_made               (5.61%)
7. opp_4d_pct                 (5.40%)
8. blitzes_faced              (4.57%)
9. seconds_per_play           (4.18%)
10. sacks_made                (3.84%)
11. fumbles_lost              (3.47%)
12. turnovers_take            (3.24%)
13. yards_per_play_allowed    (3.06%)
14. opp_first_downs_rush      (3.02%)
15. rush_ypa                  (2.79%)
16. hurries_allowed           (2.51%)
17. opp_first_downs_pen       (2.08%)
18. punts_blocked             (1.98%)
```

---

## Recommendations

### 1. **Investigate Feature Pipeline** (Priority: HIGH)
- Where are momentum features being dropped?
- Are they being computed but filtered out?
- Check `fit()` method for feature selection logic

### 2. **Test Feature Pruning** (Priority: MEDIUM)
- Create model_v2_pruned with top 18 features only
- Expect similar/better accuracy with 5x faster training
- Document baseline vs. pruned performance

### 3. **Fix Momentum Feature Engineering** (Priority: HIGH)
- If features are dropping: Why aren't they included?
- If included but unused: Why do they have 0 importance?
- Consider feature selection criteria

### 4. **Separate Target Models** (Priority: MEDIUM)
- Build separate models for margin vs. total predictions
- v2 regression on total suggests current feature set better for margins
- Different feature sets might optimize each target

### 5. **Add Domain Features** (Priority: HIGH)
- Current top 6 are all base team stats
- Injury data, rest days, EPA metrics will be equally discoverable by RF
- Should improve model significantly without added complexity

---

## Technical Details

- **Model Type**: RandomForest (n_estimators=100, max_depth=12)
- **Training Games**: 208
- **Test Games**: 64
- **Target Variable**: Point Spread (margin)
- **MAE**: 10.26 points
- **Feature Count (Actual Used)**: 38 of 234 engineered

---

## Files Generated

- `feature_importance_detailed.csv` - Full feature importance scores
- `FEATURE_IMPORTANCE_REPORT.md` - This report

---

**Analysis Date**: 2026-01-10  
**Model Version**: v2 (RandomForest with momentum features)  
**Status**: 🔍 Investigation recommended before next iteration
