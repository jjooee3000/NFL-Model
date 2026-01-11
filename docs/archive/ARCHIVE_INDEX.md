# Documentation Archive

**Last Updated**: 2026-01-11  
**Purpose**: Index of deprecated and historical documentation

---

## About This Archive

This directory contains documentation that is no longer actively maintained but preserved for historical reference. These documents may contain outdated information or refer to deprecated workflows.

**For current documentation**, see: [docs/README.md](../README.md)

---

## Archive Contents

### Completed Milestones

**[CONSOLIDATION_COMPLETE.md](CONSOLIDATION_COMPLETE.md)**
- Date: 2026-01-11
- Purpose: Consolidation of scripts and data sources
- Status: ✅ Complete
- **Superseded by**: [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)

**[CONSOLIDATION_ANALYSIS.md](CONSOLIDATION_ANALYSIS.md)**
- Date: 2026-01-11
- Purpose: Analysis of consolidation opportunities
- Status: ✅ Complete
- **Superseded by**: [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)

**[PHASE1_COMPLETE.md](PHASE1_COMPLETE.md)**
- Date: Early development
- Purpose: Phase 1 completion milestone
- Status: ✅ Complete
- **Superseded by**: [Development Progress](../development/DEVELOPMENT_PROGRESS.md)

### Planning Documents

**[INVENTORY_AND_REFACTOR_PLAN.md](INVENTORY_AND_REFACTOR_PLAN.md)**
- Date: Early development
- Purpose: Initial refactoring plan
- Status: ✅ Implemented
- **Superseded by**: [Development Progress](../development/DEVELOPMENT_PROGRESS.md)

**[COMMIT_INSTRUCTIONS_ARCHIVE.md](COMMIT_INSTRUCTIONS_ARCHIVE.md)**
- Date: Various
- Purpose: Old commit workflow instructions
- Status: 🗃️ Archived
- **Current version**: [Commit Instructions](../development/COMMIT_INSTRUCTIONS.md)

### Model Comparison Reports (Historical)

**[MODEL_V1_COMPARISON.md](MODEL_V1_COMPARISON.md)**
- Date: Early development
- Purpose: v1 model evaluation
- Status: 🗃️ Historical
- **Current**: Model v3 is production

**[V0_V1_V2_COMPARISON.md](V0_V1_V2_COMPARISON.md)**
- Date: Mid-development
- Purpose: Comparison of early model versions
- Status: 🗃️ Historical
- **Current model**: v3 (RandomForest, 275 features)

**[V0_V3_COMPARISON.md](V0_V3_COMPARISON.md)**
- Date: Recent
- Purpose: Baseline vs current model
- Status: ℹ️ Reference (may still be useful)
- **See also**: [Model Performance](../analysis/MODEL_PERFORMANCE.md)

**[V0_V3_VARIANTS_COMPARISON.md](V0_V3_VARIANTS_COMPARISON.md)**  
**[V0_V3_VARIANTS_COMPARISON_001.md](V0_V3_VARIANTS_COMPARISON_001.md)**  
**[V2_V3_VARIANTS_COMPARISON.md](V2_V3_VARIANTS_COMPARISON.md)**
- Date: Various
- Purpose: Model variant evaluations
- Status: 🗃️ Historical
- **Current**: v3 standard configuration

**[MODEL_V3_BREAKTHROUGH.md](MODEL_V3_BREAKTHROUGH.md)**
- Date: Development
- Purpose: v3 initial success documentation
- Status: ℹ️ Historical milestone
- **See also**: [Model Architecture](../architecture/MODEL_ARCHITECTURE.md)

### Feature Analysis Reports (Historical)

**[FEATURE_IMPORTANCE_REPORT.md](FEATURE_IMPORTANCE_REPORT.md)**
- Date: Earlier version
- Purpose: Feature importance analysis
- Status: 🗃️ Historical
- **Current**: Results in `outputs/feature_importance_v3.csv`

**[INVESTIGATION_COMPLETE.md](INVESTIGATION_COMPLETE.md)**
- Date: Development
- Purpose: Feature investigation completion
- Status: ✅ Complete
- **Superseded by**: [Feature Analysis](../analysis/FEATURE_ANALYSIS.md)

### Tuning Reports

**[TUNING_V3.md](TUNING_V3.md)**  
**[tuning_v3.json](tuning_v3.json)**
- Date: Development
- Purpose: Hyperparameter tuning results
- Status: ℹ️ Reference
- **Current params**: In `src/models/model_v3.py`

### Weather Analysis (Historical)

**[WEATHER_IMPACT_ANALYSIS.md](WEATHER_IMPACT_ANALYSIS.md)** (duplicated in main analysis)  
**[WEATHER_INTEGRATION.md](WEATHER_INTEGRATION.md)**
- Date: Development
- Purpose: Weather feature integration
- Status: ✅ Complete
- **Current**: [Weather Impact Analysis](../analysis/WEATHER_IMPACT_ANALYSIS.md)

### Archive Plan

**[ARCHIVE_PLAN.md](ARCHIVE_PLAN.md)**
- Date: Previous archive attempt
- Purpose: Earlier archiving plan
- Status: 🗃️ Historical
- **Current**: This index

---

## Additional Reports Archive

The following reports were moved from `reports/` directory:

### Consolidation

**[CONSOLIDATION_ROADMAP_2026-01-11.md](CONSOLIDATION_ROADMAP_2026-01-11.md)**
- Consolidation planning roadmap
- Status: ✅ Complete

### Feature Evaluation

**[FEATURE_EVAL_NEW_SOURCES.md](FEATURE_EVAL_NEW_SOURCES.md)**
- New data source feature evaluation
- Status: ℹ️ Reference

### PFR Integration

**[PFR_SCRAPER_IMPLEMENTATION.md](PFR_SCRAPER_IMPLEMENTATION.md)**
- Pro Football Reference scraper details
- Status: ℹ️ Reference
- **Current guide**: [PFR Scraper Quickstart](../guides/PFR_SCRAPER_QUICKSTART.md)

### Postgame Workflow

**[POSTGAME_WORKFLOW_COMPLETE.md](POSTGAME_WORKFLOW_COMPLETE.md)**
- Postgame evaluation workflow
- Status: ✅ Complete
- **Current**: [Postgame Status](../development/POSTGAME_STATUS_FINAL.md)

### Retraining

**[RETRAINING_RECOMMENDATIONS_2026-01-10.md](RETRAINING_RECOMMENDATIONS_2026-01-10.md)**
- Model retraining recommendations
- Status: ℹ️ Reference
- **See**: [Model Improvement Strategy](../development/MODEL_IMPROVEMENT_STRATEGY.md)

### Specific Predictions

**[PREDICTIONS_WEEK1_ROUND2_2026-01-12_13.md](PREDICTIONS_WEEK1_ROUND2_2026-01-12_13.md)**
- Specific week predictions report
- Status: 🗃️ Historical prediction

---

## Document Status Legend

- ✅ **Complete** - Work finished, documented for history
- 🗃️ **Historical** - Old version, replaced by current docs
- ℹ️ **Reference** - May still contain useful information
- ⚠️ **Outdated** - Information no longer accurate

---

## Why Archive?

Documents are archived when:
1. The feature/milestone is complete
2. The information is outdated or superseded
3. The document refers to deprecated code/workflows
4. Consolidation creates a better replacement

**Retention Policy**: Archives are kept indefinitely for historical reference.

---

## Accessing Current Documentation

**Main documentation index**: [docs/README.md](../README.md)

**Key current docs**:
- Getting Started: [docs/guides/GETTING_STARTED.md](../guides/GETTING_STARTED.md)
- System Architecture: [docs/architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md)
- Model Performance: [docs/analysis/MODEL_PERFORMANCE.md](../analysis/MODEL_PERFORMANCE.md)
- Development Progress: [docs/development/DEVELOPMENT_PROGRESS.md](../development/DEVELOPMENT_PROGRESS.md)

---

**Last Updated**: 2026-01-11  
**Maintained By**: NFL Model Development Team
