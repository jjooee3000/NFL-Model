# NFL Model Project: Comprehensive Inventory & Refactor Plan

**Date:** January 10, 2026  
**Status:** Post-v4 momentum feature integration; playoff predictions generated

---

## 📊 PROJECT OVERVIEW

### Mission
Build an accurate NFL game outcome prediction model using historical data (PFR), team stats, weather, and advanced features. Currently predicting playoff games with v3 model; v4 prototype using team-season diffs.

### Active Models
- **v3 (Production)**: RandomForest with momentum features (fixed bugs), handles margin + total
- **v4 (Experimental)**: Team-season PFR diffs + rolling momentum from gamelogs; underperforms v3 on margin MAE

### Key Data Sources
- **Excel workbook**: [data/nfl_2025_model_data_with_moneylines.xlsx](data/nfl_2025_model_data_with_moneylines.xlsx) (2025 live data)
- **Historical integrated**: [data/nfl_model_data_historical_integrated.xlsx](data/nfl_model_data_historical_integrated.xlsx) (2020–2025)
- **SQLite DB**: [data/nfl_model.db](data/nfl_model.db) (1690 merged games + PFR stats)
- **PFR CSVs**: [data/pfr_historical/](data/pfr_historical/) (team stats, gamelogs, advanced stats, situational)

---

## 🗂️ PROJECT STRUCTURE

### `src/models/`
| File | Status | Role | Lines | Notes |
|------|--------|------|-------|-------|
| `model_v0.py` | Archive candidate | Baseline; direct feature scaling, no momentum | ~1100 | Move to `archive/` |
| `model_v1.py` | Archive candidate | Attempted momentum; has momentum bug | ~800 | Move to `archive/` |
| `model_v2.py` | Archive candidate | v1 bugfix, 2 feature sets | ~550 | Move to `archive/` |
| `model_v3.py` | 🟢 **PRODUCTION** | Momentum corrected (per-week EMA calc); weather features | ~650 | Current prediction model |
| `model_v4.py` | 🟡 Experimental | Team-season diffs + rolling momentum; SQLite loader | ~180 | v3 margin MAE: 9.77, v4 margin MAE: 11.14 |
| `README.md` | Documentation | Versioning policy; archiving guide | ~50 | Needs update for v4 |
| `archive/` | *(not created yet)* | Will hold v0, v1, v2 | — | Create and move old versions |

**Recommendation**: Archive v0–v2 now to reduce clutter; update README to reflect v3 as current production, v4 as experimental.

### `src/scripts/`
| File | Purpose | Status | Dependencies | Last Run |
|------|---------|--------|--------------|----------|
| **Data Integration** |
| `backfill_historical_data.py` | PFR scrape & historical workbook build | ✅ Complete | pfr_scraper, BeautifulSoup | Session start |
| `integrate_pfr_data.py` | Merge PFR into main workbook | ✅ Complete | pandas | Session start |
| `migrate_to_sqlite.py` | Excel → SQLite consolidation | ✅ Complete | sqlite3, pandas | Session start |
| `index_pfr_data_sources.py` | PFR URL catalog builder | ✅ Complete | requests | — |
| `set_prediction_targets.py` | Mark games for prediction | ✅ Complete | pandas | Session start |
| **Training & Comparison** |
| `compare_all_versions.py` | v0–v4 MAE comparison | ✅ Works | All models | Last confirmed |
| `compare_v4_vs_v3.py` | Focused v3 vs v4 | ✅ Works | model_v3, model_v4 | Session start |
| `compare_v2_v3.py` | v2 vs v3 baseline | ✅ Works | model_v2, model_v3 | — |
| `compare_v0_v3.py` | v0 vs v3 + tuning opt | ✅ Works | model_v0, model_v3 | — |
| `compare_weather_impact.py` | Weather feature value | 🔴 **Fixed** (outdoor-only NaN bug) | model_v2, model_v3 | Session end (pending) |
| `tune_v3.py` | v3 hyperparameter grid search | ✅ Complete | GridSearchCV, v3 | — |
| `tune_v4_hyperparameters.py` | v4 hyperparameter grid search | ⏳ Running (720 CV fits) | GridSearchCV, v4 | In progress |
| **Prediction & Analysis** |
| `predict_upcoming.py` | Predict games; supports `--playoffs` flag | ✅ Enhanced | model_v3, pandas | Session (5 playoff games) |
| `analyze_features.py` | v2 feature importance | ✅ Works | model_v2 | — |
| `analyze_v3_features.py` | v3 feature importance | ✅ Works | model_v3 | — |
| `record_predictions.py` | Log holdout predictions | ✅ Works | model_v3 | — |
| `run_ensemble_oneoff.py` | One-off ensemble prediction | ✅ Works | Multiple models | — |
| `check_features.py` | Sanity check team_games columns | ✅ Works | pandas | — |
| `inspect_odds_feed.py` | Debug odds data | ✅ Works | pandas | — |
| `debug_momentum.py` | Trace momentum calc | ✅ Works | model_v3 | — |
| `diagnostics.py` | Environment & data health check | ✅ Works | All deps | — |

**Size Analysis**: ~20 scripts; largest (backfill, model files) ~600–1100 LOC; avg ~250 LOC.  
**Maintenance burden**: High due to script count; many comparison/analysis scripts (consolidation opportunity).

### `src/utils/`
| File | Role | Lines |
|------|------|-------|
| `paths.py` | Central path definitions (DATA_DIR, REPORTS_DIR, etc.) | ~30 |
| `__init__.py` | Minimal | ~5 |
| `__pycache__/` | Runtime cache | — |

**Note**: Missing utilities for common tasks (e.g., feature engineering, model evaluation metrics, logging).

### `data/`
| Item | Type | Size | Notes |
|------|------|------|-------|
| `nfl_2025_model_data_with_moneylines.xlsx` | Excel | ~5 MB | 2025 live data; 13 sheets |
| `nfl_model_data_historical_integrated.xlsx` | Excel | ~8 MB | 2020–2025 merged; 19 sheets |
| `nfl_model.db` | SQLite | ~15 MB | 1690 merged games + PFR stats |
| `pfr_historical/` | CSV directory | ~50 MB | 2020–2024 scraped data (team stats, gamelogs, etc.) |

**Redundancy**: Data exists in Excel, SQLite, and CSV formats. SQLite should be source-of-truth; CSV scrapes are intermediate.

### `outputs/`
| File | Type | Purpose | Count |
|------|------|---------|-------|
| `prediction_log.csv` | CSV | Accumulated predictions (all variants, all weeks) | 42 rows (session) |
| `predictions_playoffs_week1_2026-01-10.csv` | CSV | Week 1 playoff-only run (3 variants) | 15 rows |
| `*.txt` | Text | Diagnostics, debug output | Various |
| `*.json` | JSON | Upcoming predictions, tuning results | Various |
| `*.csv` | CSV | Feature importance, analysis outputs | Various |

**Cleanup needed**: Old outputs from prior sessions; archive or organize by date.

### `reports/`
| File | Status | Content |
|------|--------|---------|
| `FEATURE_IMPORTANCE_REPORT.md` | ✅ | v2/v3 feature rankings |
| `INVESTIGATION_COMPLETE.md` | ✅ | Momentum bug root cause analysis |
| `MODEL_V1_COMPARISON.md` | ✅ | v1 vs later versions |
| `TUNING_V3.md` | ✅ | v3 hyperparameter search results |
| `V0_V1_V2_COMPARISON.md` | ✅ | Early model evolution |
| `V0_V3_COMPARISON.md` | ✅ | Baseline vs production |
| `WEATHER_INTEGRATION.md` | ✅ | Weather feature methodology |
| `WEATHER_IMPACT_ANALYSIS.md` | ⏳ | Pending (after weather script run) |
| `V0_V3_VARIANTS_COMPARISON_*.md` | ✅ | Variant tuning results |
| `v4_tuning.json` | ⏳ | GridSearchCV results (in progress) |

**Issue**: Too many reports; need consolidation into a unified `MODEL_DEVELOPMENT_HISTORY.md`.

### Root-level Files
| File | Role |
|------|------|
| `requirements.txt` | Dependencies (pandas, sklearn, BeautifulSoup4, lxml, etc.) |
| `README.md` | Project overview & quick-start |
| `COMMIT_INSTRUCTIONS.md` | Git commit best practices |
| `COMMIT_INSTRUCTIONS_ARCHIVE.md` | Archiving guidelines |
| `archive_old_models.py` | Script to move v0–v2 to `archive/` |

---

## 📈 CURRENT PERFORMANCE METRICS

### Model Comparison (Test MAE on 2025 data)
| Model | Margin MAE | Total MAE | Features | Status |
|-------|-----------|-----------|----------|--------|
| v0 | ~11.5 | ~11.2 | ~20 | Baseline |
| v1 | ~10.5 | ~10.5 | ~30 | Momentum bug |
| v2 | ~9.9 | ~11.0 | ~40 | Bug-fixed |
| v3 | **9.77** | **10.98** | ~50 | 🟢 Production |
| v4 | 11.14 | 10.98 | 55 | 🟡 Experimental |

**Key insight**: v3 outperforms v4 on margin despite more features (gamelogs + rolling). v4 may benefit from feature selection or different architecture.

### Current Predictions (Week 1 Playoff Games)
- **v3 Default**: 5 games predicted (margins –6.2 to +7.2)
- **v3 Tuned**: 5 games predicted (margins –5.8 to +6.1)
- **v3 Stacking**: 5 games predicted (margins –4.2 to +6.2)
- **Saved outputs**: [outputs/predictions_playoffs_week1_2026-01-10.csv](outputs/predictions_playoffs_week1_2026-01-10.csv)

---

## 🔍 TECHNICAL DEBT & ISSUES

### 1. **Model Versioning Clutter**
- **Issue**: v0–v3 all in `src/models/`; v4 added; no archive yet
- **Impact**: Confusing which is active; large directory
- **Fix**: Archive v0–v2 now; keep v3 + v4 with clear README
- **Effort**: ~5 min (move files + update imports in comparison scripts)

### 2. **Data Redundancy**
- **Issue**: Same data in Excel workbooks, SQLite, CSV files
- **Impact**: Sync issues; confusion about source-of-truth
- **Fix**: 
  - Designate SQLite as primary (already done)
  - Remove or archive CSV files after confirmation
  - Update all loaders to use SQLite (v3 still uses Excel)
- **Effort**: ~2 hours (refactor v3 loader, test)

### 3. **v4 Underperformance**
- **Issue**: v4 margin MAE 11.14 vs v3 9.77 (despite more features)
- **Root cause**: Team-season diffs may not capture per-game momentum; gamelogs rolling features duplicative
- **Fix options**:
  - (a) Feature selection: remove low-importance features
  - (b) Architecture: use per-game momentum from gamelogs instead of season diffs
  - (c) Hybrid: keep v3 as-is; use v4 for specific sub-populations (e.g., high-variance games)
- **Effort**: ~4 hours (grid search done; now implement fix + re-test)

### 4. **Script Explosion**
- **Issue**: 20+ scripts in `src/scripts/`; many are comparison/analysis (not core)
- **Impact**: Hard to maintain; unclear which are essential
- **Fix**: Create `src/scripts/analysis/` subdirectory for non-essential scripts (compare_*, analyze_*, tune_*, debug_*)
- **Effort**: ~1 hour (move files + update imports)

### 5. **Weather Script Errors**
- **Issue**: `compare_weather_impact.py` fails on outdoor-only filter (NaN targets)
- **Fixed**: Moved outdoor-only patch to v2 loader; now ready to run
- **Status**: Pending execution (GridSearchCV blocking)
- **Effort**: ✅ Fixed

### 6. **Missing Abstractions**
- **Issue**: No utility classes for common operations (evaluation, feature engineering, logging)
- **Impact**: Code duplication across scripts; hard to maintain
- **Fix**: Add `src/utils/model_eval.py`, `src/utils/logger.py`, `src/utils/feature_eng.py`
- **Effort**: ~3 hours

### 7. **Prediction Workflow**
- **Issue**: `predict_upcoming.py` is v3-specific; v4 has no prediction interface
- **Impact**: Can't easily swap models; hard to test v4 in production
- **Fix**: Refactor v3 and v4 to share interface; create factory function
- **Effort**: ~2 hours

### 8. **Documentation Gaps**
- **Issue**: Many reports duplicated (V0_V3_COMPARISON.md, etc.); no single source-of-truth
- **Impact**: Outdated info; hard to find current status
- **Fix**: Consolidate into `DEVELOPMENT_LOG.md` + `MODEL_STATUS.md`
- **Effort**: ~1 hour

---

## ✅ COMPLETED WORK (This Session)

### Major Features
1. ✅ Added `--playoffs` flag to `predict_upcoming.py`
2. ✅ Generated playoff predictions for week 1 (5 games × 3 variants)
3. ✅ Enhanced v4 with rolling momentum features from PFR gamelogs
4. ✅ Fixed v4 data loading and index alignment bugs
5. ✅ Fixed `compare_weather_impact.py` outdoor-only filtering
6. ✅ Ran v3 predictions and saved to [outputs/](outputs/)

### Scripts Created/Updated
- [src/scripts/tune_v4_hyperparameters.py](src/scripts/tune_v4_hyperparameters.py) — GridSearchCV (still running)
- [src/models/model_v4.py](src/models/model_v4.py) — Momentum features + SQLite loader
- [src/scripts/predict_upcoming.py](src/scripts/predict_upcoming.py) — `--playoffs` flag

---

## 🎯 RECOMMENDED REFACTOR ROADMAP

### Phase 1: Immediate (< 1 hour)
1. **Archive old models**
   - Move v0–v2 to `src/models/archive/`
   - Update README
   - Run `archive_old_models.py` script

2. **Cleanup outputs**
   - Delete or archive old session runs
   - Organize by date (e.g., `outputs/2026-01-10/`)

### Phase 2: Short-term (2–4 hours)
1. **Consolidate comparison scripts**
   - Create `src/scripts/analysis/` subdirectory
   - Move: compare_*.py, analyze_*.py, tune_*.py, debug_*.py
   - Update imports in any runners

2. **Unify prediction interface**
   - Create `src/models/base.py` with abstract `Model` class
   - Refactor v3, v4 to inherit from `Model`
   - Add factory function for model selection

3. **Data consolidation**
   - Confirm SQLite is complete and accurate
   - Update v3 to load from SQLite (fallback to Excel)
   - Archive CSV files

### Phase 3: Medium-term (4–8 hours)
1. **Add utility abstractions**
   - `src/utils/model_eval.py` — evaluation metrics, cross-validation
   - `src/utils/feature_eng.py` — momentum, rolling features
   - `src/utils/logger.py` — structured logging for predictions + model runs

2. **Fix v4 underperformance**
   - Implement feature selection (permutation importance)
   - Test alternative architectures (GradientBoosting, neural net)
   - Consider hybrid approach (v3 default, v4 for specific cases)

3. **Unify documentation**
   - Create `DEVELOPMENT_LOG.md` (chronological history)
   - Create `MODEL_STATUS.md` (current performance, recommendations)
   - Archive individual report files

### Phase 4: Long-term (8+ hours)
1. **CI/CD pipeline**
   - Add `pytest` for model tests
   - Add `black`, `flake8` for code quality
   - Create `Makefile` for common tasks (train, predict, compare, lint)

2. **Advanced features**
   - Weather impact integration (once working)
   - Ensemble methods (voting, stacking)
   - Hyperparameter tuning automation (Optuna)
   - Model monitoring (prediction accuracy over time)

3. **Deployment**
   - Create API wrapper (Flask/FastAPI) for predictions
   - Database schema versioning
   - Automated data refresh (PFR scraping on schedule)

---

## 📋 TODO CHECKLIST

### Immediate (Next 30 minutes)
- [ ] Wait for v4 tuning to complete; analyze results
- [ ] Run `compare_weather_impact.py` with fixed outdoor-only logic
- [ ] Archive v0–v2 to `src/models/archive/`

### Short-term (Next 2 hours)
- [ ] Consolidate comparison scripts into `src/scripts/analysis/`
- [ ] Create `src/models/base.py` with abstract interface
- [ ] Refactor v3, v4 loaders to use SQLite as primary source
- [ ] Update `src/models/README.md` to reflect current structure

### Medium-term (Next 4 hours)
- [ ] Implement feature selection for v4
- [ ] Create `src/utils/model_eval.py` and `src/utils/feature_eng.py`
- [ ] Consolidate reports into `DEVELOPMENT_LOG.md`
- [ ] Test v4 improvements and update comparison

### Stretch (If time permits)
- [ ] Create `Makefile` for common commands
- [ ] Add pytest suite for models
- [ ] Implement Optuna-based hyperparameter tuning

---

## 🔗 Key Files Summary

**Models**: [src/models/](src/models/) (v0–v4, currently all in main dir)  
**Scripts**: [src/scripts/](src/scripts/) (20+ scripts, should split)  
**Data**: [data/](data/) (Excel, SQLite, CSVs—redundant)  
**Outputs**: [outputs/](outputs/) (predictions, analysis results)  
**Reports**: [reports/](reports/) (consolidated history, needs tidying)  
**Utilities**: [src/utils/](src/utils/) (minimal, should expand)

---

## 🚀 SUCCESS METRICS

After refactor, project should satisfy:
- [ ] Single clear "active" model version (v3 or v4)
- [ ] Clear directory structure (models/, scripts/core, scripts/analysis, utils/)
- [ ] Single source-of-truth for data (SQLite)
- [ ] Unified documentation (1–2 key files instead of 10)
- [ ] No code duplication; shared utilities for common tasks
- [ ] All predictions run with consistent interface
- [ ] <5 second model import time (no circular deps)
- [ ] <1 minute end-to-end prediction for upcoming games

---

**Next Step**: Archive models, then tackle short-term refactoring to consolidate scripts and unify data sources.
