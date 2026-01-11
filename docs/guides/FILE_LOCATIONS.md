# NFL Model - File Locations Reference

**Last Updated**: 2026-01-11  
**Purpose**: Quick reference for locating all project files

---

## 📁 Directory Structure

```
NFL-Model/
├── docs/                           # Documentation (organized by category)
├── src/                            # Source code
├── data/                           # Data files and database
├── outputs/                        # Generated predictions and analysis
├── tests/                          # Test files
├── .vscode/                        # VS Code configuration
└── [Root files]                    # Configuration and utilities
```

---

## 📚 Documentation (docs/)

### Core Documentation
- **[docs/README.md](../README.md)** - Master documentation index
- **[docs/guides/GETTING_STARTED.md](../guides/GETTING_STARTED.md)** - Setup and first steps
- **[docs/guides/QUICK_REFERENCE.md](../guides/QUICK_REFERENCE.md)** - Common commands

### Architecture
- **[docs/architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md)** - System design
- **[docs/architecture/DATABASE_SCHEMA.md](../architecture/DATABASE_SCHEMA.md)** - SQLite schema
- **[docs/architecture/MODEL_ARCHITECTURE.md](../architecture/MODEL_ARCHITECTURE.md)** - Model v3 design
- **[docs/architecture/DATA_PIPELINE.md](../architecture/DATA_PIPELINE.md)** - Data flow
- **[docs/architecture/SQLITE_INTEGRATION_COMPLETE.md](../architecture/SQLITE_INTEGRATION_COMPLETE.md)** - SQLite migration details
- **[docs/architecture/PFR_INTEGRATION_ROADMAP.md](../architecture/PFR_INTEGRATION_ROADMAP.md)** - Pro Football Reference integration
- **[docs/architecture/PFR_DATA_CATALOG.md](../architecture/PFR_DATA_CATALOG.md)** - PFR data sources
- **[docs/architecture/DATA_SOURCE_VALIDATION.md](../architecture/DATA_SOURCE_VALIDATION.md)** - Data validation

### Guides
- **[docs/guides/HISTORICAL_BACKFILL_GUIDE.md](../guides/HISTORICAL_BACKFILL_GUIDE.md)** - Historical data backfill
- **[docs/guides/PFR_SCRAPER_QUICKSTART.md](../guides/PFR_SCRAPER_QUICKSTART.md)** - PFR scraping guide

### Analysis Reports
- **[docs/analysis/WEATHER_IMPACT_ANALYSIS.md](../analysis/WEATHER_IMPACT_ANALYSIS.md)** - Weather features
- **[docs/analysis/POSTGAME_ANALYSIS_2026-01-10.md](../analysis/POSTGAME_ANALYSIS_2026-01-10.md)** - Postgame evaluation
- **[docs/analysis/POSTGAME_EVAL_2026-01-10.md](../analysis/POSTGAME_EVAL_2026-01-10.md)** - Detailed postgame analysis
- **[docs/analysis/DATA_ENHANCEMENT_VISUAL.md](../analysis/DATA_ENHANCEMENT_VISUAL.md)** - Data enhancements
- **[docs/analysis/FEATURE_OPPORTUNITIES.md](../analysis/FEATURE_OPPORTUNITIES.md)** - Feature ideas
- **[docs/analysis/MISSING_DATA_SUMMARY.md](../analysis/MISSING_DATA_SUMMARY.md)** - Data gaps
- **[docs/analysis/PFR_DATA_GAPS_ANALYSIS.md](../analysis/PFR_DATA_GAPS_ANALYSIS.md)** - PFR data gaps

### Development
- **[docs/development/MODEL_IMPROVEMENT_STRATEGY.md](../development/MODEL_IMPROVEMENT_STRATEGY.md)** - Improvement roadmap
- **[docs/development/MODEL_IMPROVEMENT_COMPLETE.md](../development/MODEL_IMPROVEMENT_COMPLETE.md)** - Completed improvements
- **[docs/development/FEATURE_INTERACTIONS_RESULTS.md](../development/FEATURE_INTERACTIONS_RESULTS.md)** - Feature interaction results
- **[docs/development/DEVELOPMENT_PROGRESS.md](../development/DEVELOPMENT_PROGRESS.md)** - Progress tracker
- **[docs/development/POSTGAME_INCORPORATION_STRATEGY.md](../development/POSTGAME_INCORPORATION_STRATEGY.md)** - Postgame workflow
- **[docs/development/POSTGAME_STATUS_FINAL.md](../development/POSTGAME_STATUS_FINAL.md)** - Postgame completion
- **[docs/development/COMMIT_INSTRUCTIONS.md](../development/COMMIT_INSTRUCTIONS.md)** - Git workflow

### Archive
- **[docs/archive/](../archive/)** - Deprecated documentation and old reports

---

## 💻 Source Code (src/)

### Models
- **[src/models/model_v3.py](../../src/models/model_v3.py)** - Production model (RandomForest, 275 features)
- **[src/models/model_v4.py](../../src/models/model_v4.py)** - Experimental model (testing)
- **[src/models/base.py](../../src/models/base.py)** - Base model class
- **[src/models/README.md](../../src/models/README.md)** - Model documentation

### Scripts

#### Prediction Scripts
- **[src/scripts/predict_ensemble_multiwindow.py](../../src/scripts/predict_ensemble_multiwindow.py)** - Multi-window ensemble predictions
- **[src/scripts/predict_upcoming.py](../../src/scripts/predict_upcoming.py)** - Simple upcoming game predictions

#### Data Management
- **[src/scripts/update_postgame_scores.py](../../src/scripts/update_postgame_scores.py)** - Update game scores
- **[src/scripts/fetch_upcoming_games.py](../../src/scripts/fetch_upcoming_games.py)** - Fetch upcoming schedule
- **[src/scripts/pipeline_daily_sync.py](../../src/scripts/pipeline_daily_sync.py)** - Daily data sync
- **[src/scripts/clean_sqlite_db.py](../../src/scripts/clean_sqlite_db.py)** - Database cleanup

#### Data Import/Integration
- **[src/scripts/migrate_to_sqlite.py](../../src/scripts/migrate_to_sqlite.py)** - Excel to SQLite migration
- **[src/scripts/import_pfr_historical.py](../../src/scripts/import_pfr_historical.py)** - Import PFR historical data
- **[src/scripts/integrate_pfr_data.py](../../src/scripts/integrate_pfr_data.py)** - Integrate PFR data
- **[src/scripts/backfill_historical_data.py](../../src/scripts/backfill_historical_data.py)** - Backfill historical games
- **[src/scripts/backfill_weather.py](../../src/scripts/backfill_weather.py)** - Backfill weather data

#### Scraping
- **[src/scripts/fetch_pfr_nflscrapy.py](../../src/scripts/fetch_pfr_nflscrapy.py)** - Fetch from Pro Football Reference
- **[src/scripts/map_nflscrapy_to_db.py](../../src/scripts/map_nflscrapy_to_db.py)** - Map scraped data to DB

#### Analysis
- **[src/scripts/analysis/](../../src/scripts/analysis/)** - Analysis scripts directory
- **[src/scripts/analyze_correlations.py](../../src/scripts/analyze_correlations.py)** - Feature correlation analysis
- **[src/scripts/compare_v0_v3.py](../../src/scripts/compare_v0_v3.py)** - Compare model versions
- **[src/scripts/diagnostics.py](../../src/scripts/diagnostics.py)** - Model diagnostics

#### Model Training/Tuning
- **[src/scripts/tune_v3.py](../../src/scripts/tune_v3.py)** - Hyperparameter tuning for v3

#### Utilities
- **[src/scripts/migrate_db_schema.py](../../src/scripts/migrate_db_schema.py)** - Database schema migrations
- **[src/scripts/set_prediction_targets.py](../../src/scripts/set_prediction_targets.py)** - Mark games for prediction

### Utilities
- **[src/utils/db_dedupe.py](../../src/utils/db_dedupe.py)** - Database deduplication
- **[src/utils/db_logging.py](../../src/utils/db_logging.py)** - Database logging
- **[src/utils/espn_scraper.py](../../src/utils/espn_scraper.py)** - ESPN data fetching
- **[src/utils/pfr_scraper.py](../../src/utils/pfr_scraper.py)** - Pro Football Reference scraping
- **[src/utils/weather.py](../../src/utils/weather.py)** - Weather data utilities
- **[src/utils/feature_builder.py](../../src/utils/feature_builder.py)** - Feature engineering
- **[src/utils/paths.py](../../src/utils/paths.py)** - Path utilities
- **[src/utils/stadiums.py](../../src/utils/stadiums.py)** - Stadium data
- **[src/utils/schedule.py](../../src/utils/schedule.py)** - Schedule utilities
- **[src/utils/upcoming_games.py](../../src/utils/upcoming_games.py)** - Upcoming game utilities

### API
- **[src/nfl_model/services/api/app.py](../../src/nfl_model/services/api/app.py)** - FastAPI application

---

## 🗄️ Data (data/)

### Primary Database
- **[data/nfl_model.db](../../data/nfl_model.db)** - SQLite database (PRIMARY DATA SOURCE)
  - 2,474 games (2020-2025)
  - Full team game stats
  - Odds and betting lines
  - Weather data
  - Ensemble predictions

### Excel Files
- **[data/nfl_2025_model_data_with_moneylines.xlsx](../../data/nfl_2025_model_data_with_moneylines.xlsx)** - Current season Excel backup
- **[data/nfl_model_data_historical_integrated.xlsx](../../data/nfl_model_data_historical_integrated.xlsx)** - Historical integrated data

### Historical Data
- **[data/pfr_historical/](../../data/pfr_historical/)** - Pro Football Reference historical data
  - `YYYY_games.csv` - Game results by year
  - `YYYY_team_stats.csv` - Team statistics
  - `YYYY_advanced_*.csv` - Advanced metrics
  - `YYYY_situational_*.csv` - Situational stats

---

## 📊 Outputs (outputs/)

### Predictions
- **[outputs/prediction_log.csv](../../outputs/prediction_log.csv)** - All predictions log
- **[outputs/ensemble_multiwindow_*.csv](../../outputs/)** - Multi-window predictions (timestamped)
- **[outputs/ensemble_multiwindow_detail_*.csv](../../outputs/)** - Detailed prediction breakdowns
- **[outputs/upcoming_predictions.json](../../outputs/upcoming_predictions.json)** - JSON format predictions

### Analysis Results
- **[outputs/feature_importance_v3.csv](../../outputs/feature_importance_v3.csv)** - Feature importance rankings
- **[outputs/feature_importance_detailed.csv](../../outputs/feature_importance_detailed.csv)** - Detailed feature analysis
- **[outputs/postgame_results_*.csv](../../outputs/)** - Postgame evaluation results
- **[outputs/postgame_eval_*.csv](../../outputs/)** - Postgame detailed evaluation

### Configuration
- **[outputs/v4_tuning.json](../../outputs/v4_tuning.json)** - Model v4 tuning parameters

### PFR Data
- **[outputs/pfr_data_index.json](../../outputs/pfr_data_index.json)** - PFR data index (JSON)
- **[outputs/pfr_data_index.md](../../outputs/pfr_data_index.md)** - PFR data index (Markdown)

---

## 🧪 Tests (tests/)

### Test Files
- **[tests/test_api_health.py](../../tests/test_api_health.py)** - API health check tests

---

## ⚙️ Configuration

### VS Code
- **[.vscode/tasks.json](../../.vscode/tasks.json)** - VS Code tasks
- **[.vscode/settings.json](../../.vscode/settings.json)** - VS Code settings

### Python
- **[requirements.txt](../../requirements.txt)** - Python dependencies
- **[.gitignore](../../.gitignore)** - Git ignore patterns

### Root Files
- **[README.md](../../README.md)** - Project overview
- **[PROJECT_INDEX.md](../../PROJECT_INDEX.md)** - Deprecated project index (see docs/README.md)

---

## 🗑️ Utility Scripts (Root Level)

- **[archive_old_models.py](../../archive_old_models.py)** - Archive old model files
- **[archive_old_models.bat](../../archive_old_models.bat)** - Windows batch version
- **[audit_db.py](../../audit_db.py)** - Database audit tool
- **[test_espn.py](../../test_espn.py)** - ESPN API test
- **[test_week10_predictions.py](../../test_week10_predictions.py)** - Week 10 validation test

---

## 📋 Quick Find

### "I need to..."

**Generate predictions**:
- → `src/scripts/predict_upcoming.py`
- → `src/scripts/predict_ensemble_multiwindow.py`

**Update game scores**:
- → `src/scripts/update_postgame_scores.py`

**View model code**:
- → `src/models/model_v3.py`

**See database schema**:
- → `docs/architecture/DATABASE_SCHEMA.md`

**Understand the model**:
- → `docs/architecture/MODEL_ARCHITECTURE.md`

**View performance**:
- → `docs/analysis/` (various reports)
- → `outputs/postgame_*.csv`

**Access data**:
- → `data/nfl_model.db` (SQLite)

**View predictions**:
- → `outputs/prediction_log.csv`
- → `outputs/ensemble_multiwindow_*.csv`

**Start API**:
- → `src/nfl_model/services/api/app.py`

---

**Last Updated**: 2026-01-11  
**For**: Quick file location reference  
**See Also**: [Getting Started Guide](GETTING_STARTED.md), [Documentation Index](../README.md)
