# Week 1 Playoff Predictions - Round 2 (2026-01-12 & 2026-01-13)

**Generated**: 2026-01-11  
**Status**: Ready for Sunday/Monday games  
**Data Source**: v3 model predictions from 2026-01-10 run  
**Note**: Model shows +12.5 pt underestimation on totals - consider adding 10-15 pt buffer

---

## Predictions Summary

### Game 1: BUF @ JAX (Sunday 1/12, 1:00 PM ET)
| Variant | Spread | Total | JAX Win % |
|---------|--------|-------|----------|
| Tuned | JAX -5.8 | 57.8 | 34% |
| Stacking | JAX -4.2 | 57.0 | 38% |
| **Average** | **JAX -5.0** | **57.4** | **36%** |

**Model Insight**: Bills favored by 5 points; predicts competitive game with decent scoring (~57 pts)

---

### Game 2: SFO @ PHI (Sunday 1/12, 4:30 PM ET)
| Variant | Spread | Total | PHI Win % |
|---------|--------|-------|----------|
| Tuned | PHI +6.1 | 44.6 | 67% |
| Stacking | PHI +6.2 | 43.9 | 67% |
| **Average** | **PHI +6.1** | **44.2** | **67%** |

**Model Insight**: Eagles strong favorites by 6 points; lower scoring game predicted (~44 pts, likely underestimated to ~54-56)

---

### Game 3: LAC @ NWE (Sunday 1/12, 8:15 PM ET)
| Variant | Spread | Total | NWE Win % |
|---------|--------|-------|----------|
| Tuned | NWE +3.6 | 46.9 | 60% |
| Stacking | NWE +4.7 | 47.3 | 63% |
| **Average** | **NWE +4.2** | **47.1** | **62%** |

**Model Insight**: Patriots slightly favored by 4 points; borderline game with modest scoring (~47 pts, likely underestimated to ~57-62)

---

### Game 4: HOU @ PIT (Monday 1/13, 8:15 PM ET)
| Variant | Spread | Total | PIT Win % |
|---------|--------|-------|----------|
| Tuned | PIT -0.9 | 41.7 | 48% |
| Stacking | PIT +0.4 | 43.9 | 51% |
| **Average** | **PIT -0.2** | **42.8** | **49%** |

**Model Insight**: Essentially a toss-up; Steelers very slight favorite; lowest scoring game predicted (~43 pts, likely underestimated to ~53-58)

---

## Key Observations

### Confidence Rankings
1. **PHI vs SFO** (High) - Eagles have 6+ pt edge, clear favorite
2. **NWE vs LAC** (Medium) - Patriots slight favorites, within margin of error
3. **JAX vs BUF** - Mixed signals; stacking suggests closer game than tuned variant
4. **PIT vs HOU** (Low) - Essentially a coin flip; predictions differ significantly

### Scoring Pattern
All games predicted with **low-to-moderate** total points:
- Range: 41.7 - 57.8 pts
- Average: 47.9 pts

**Critical**: Week 1 postgame evaluation showed +12.5 MAE on totals:
- Actual games scored 58-65 pts
- Model predicted 46-57 pts
- **Recommendation**: Add 10-15 pts to all total predictions

### Adjusted Total Estimates
If applying +12.5 pt correction from Week 1 learning:

| Game | Model | Adjusted | Range |
|------|-------|----------|-------|
| BUF @ JAX | 57.4 | 69.9 | 65-75 |
| SFO @ PHI | 44.2 | 56.7 | 52-62 |
| LAC @ NWE | 47.1 | 59.6 | 55-65 |
| HOU @ PIT | 42.8 | 55.3 | 50-60 |

---

## Comparison to Week 1 Results

**Week 1 Actual** (LAR@CAR 34-31, GNB@CHI 27-31):
- Margin errors: Excellent (1.4-2.4 pts)
- Total errors: High (+7.6 to +18.6 pts)

**This Week Predictions**:
- Margin predictions appear reasonable
- **Total predictions likely 10-15 pts LOW** - prepare to adjust

---

## Files Generated

| File | Description | Rows |
|------|-------------|------|
| `outputs/predictions_playoffs_week1_2026-01-12_13.csv` | Full predictions with both variants | 8 |

---

## Recommendation for Analysis

### Next Steps
1. **Record actual scores** for all 4 games as they complete
2. **Update** `outputs/postgame_results_2026-01-10.csv` with Week 1 Round 2 results
3. **Evaluate** total vs margin accuracy vs marginal accuracy
4. **Confirm** if +12.5 pt underestimation is systematic (if so, apply for future weeks)

### Data Incorporation Strategy
**DO NOT retrain yet** - per `POSTGAME_INCORPORATION_STRATEGY.md`:
- Only have 2 games of postgame data (insufficient)
- Wait until 6+ total games confirm bias before adjusting model
- If bias confirmed, add feature flag rather than direct retraining

---

## Prediction Performance Tracking

This file serves as baseline for Week 1 Round 2 evaluation:
- Use `evaluate_postgame_predictions.py` to compare vs actuals
- Generate MAE metrics and error analysis
- Confirm or revise hypothesis about total point underestimation

**Evaluation Date**: 2026-01-15 (after all Week 1 games complete)

