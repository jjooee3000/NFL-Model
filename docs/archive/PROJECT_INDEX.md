# NFL Model - Complete Project Index

**Last Updated**: 2026-01-12  
**Current Model**: v3 (RandomForest with momentum features)  
**Data Source**: SQLite (`nfl_model.db` with 1,690 games)  
**Active Status**: ✅ Fully integrated with SQLite, all predictions using full data universe

---

## Quick Navigation

- **[Key Commands](#key-commands)** - How to run predictions and analysis
- **[Directory Structure](#directory-structure)** - Folder organization
- **[Scripts Guide](#scripts-guide)** - All 16 scripts documented
- **[Models](#models)** - Model versions and status
- **[Data & Database](#data--database)** - SQLite schema and files
- **[Reports & Analysis](#reports--analysis)** - Generated documents
- **[Strategic Documents](#strategic-documents)** - Important guides and plans
- **[Utilities](#utilities)** - Helper modules
- **[Configuration & Testing](#configuration--testing)** - Config and test files

---

## Key Commands

### Generate Predictions (Most Common)
```bash
# Predict upcoming games for a specific week
python src/scripts/predict_upcoming.py --week 1 --train-through 18 --playoffs --variants default

# Output: logs to outputs/prediction_log.csv with margin, total, win probability
```

### Model Comparison & Analysis
```bash
# Compare all model versions (v0, v1, v2, v3)
python src/scripts/compare_all_versions.py

# Compare v3 vs v4 (experimental)
python src/scripts/compare_v4_vs_v3.py

# Compare v0 baseline vs v3 with SQLite data
python src/scripts/compare_v0_v3.py
```

### Feature Analysis
```bash
# Analyze feature importance for v3 model
python src/scripts/analyze_v3_features.py

# Check which features are being used
python src/scripts/check_features.py

# Debug momentum features specifically
python src/scripts/debug_momentum.py
```

### Validation & Diagnostics
```bash
# Run model diagnostics and sanity checks
python src/scripts/diagnostics.py

# Verify odds feed data
python src/scripts/inspect_odds_feed.py

# Validate weather features
python src/scripts/quick_weather_test.py
```

### Hyperparameter Tuning
```bash
# Tune v3 model hyperparameters
python src/scripts/tune_v3.py
```

### Utility Operations
```bash
# Audit entire database schema
python audit_db.py

# Archive old model versions
python archive_old_models.py
```

---

## Directory Structure

### Root Level
Contains main configuration, documentation, and orchestration files.

```
NFL-Model/
├── .git/                                # Version control
├── .venv/                               # Python virtual environment
├── .vscode/                             # VS Code settings
├── data/                                # Data storage
├── src/                                 # Source code
├── outputs/                             # Generated predictions/analysis
├── reports/                             # Analysis reports
├── README.md                            # Main documentation (original)
├── PROJECT_INDEX.md                     # This file - comprehensive guide
├── requirements.txt                     # Python dependencies
└── [Strategic Documents]                # See "Strategic Documents" section
```

---

## Scripts Guide

All scripts should be run from the repository root.

### 🎯 Primary Prediction Interface

#### `src/scripts/predict_upcoming.py`
**Purpose**: Generate predictions for upcoming games  
**Usage**: `python src/scripts/predict_upcoming.py --week 1 --train-through 18 --playoffs [--variants default]`  
**Arguments**:
- `--week`: Week number to predict
- `--train-through`: Latest week to use for training (usually 18 or 21 for playoffs)
- `--playoffs`: Include playoff games in predictions
- `--variants`: Model variants to use (default, tuned, stacking)

**Output**: 
- Logs all predictions to `outputs/prediction_log.csv`
- Prints to stdout: game, spread, total, home win probability
- Model automatically loads 1,690 games from SQLite with weather features

**Data Source**: ✅ SQLite-enabled (`prefer_sqlite=True`)  
**Status**: ✅ Production-ready, tested 2026-01-11

---

### 📊 Model Comparison & Selection

#### `src/scripts/compare_all_versions.py`
**Purpose**: Compare v0, v1, v2, v3 models side-by-side  
**Usage**: `python src/scripts/compare_all_versions.py`  
**Outputs**: 
- Test set performance (MAE, MSE, R²)
- Feature importance comparison
- Prediction variance across models
- Ensemble accuracy if available

**Status**: ✅ Active, helps validate v3 superiority

#### `src/scripts/compare_v0_v3.py`
**Purpose**: Detailed comparison of baseline (v0) vs current (v3)  
**Usage**: `python src/scripts/compare_v0_v3.py`  
**Shows**: 
- Margin prediction improvement
- Feature set differences
- Data loading verification (SQL vs Excel)
- Detailed performance metrics

**Status**: ✅ Active, v3 now loads 1,690 games via SQLite

#### `src/scripts/compare_v4_vs_v3.py`
**Purpose**: Compare experimental v4 model against production v3  
**Usage**: `python src/scripts/compare_v4_vs_v3.py`  
**Notes**: v4 is experimental; v3 recommended for production  
**Status**: ✅ For research/experimentation only

---

### 🔍 Feature & Data Analysis

#### `src/scripts/analyze_v3_features.py`
**Purpose**: Feature importance analysis for v3 model with momentum features  
**Usage**: `python src/scripts/analyze_v3_features.py`  
**Output**: 
- Feature importance rankings (top 20-30 features)
- Feature impact distribution
- CSV saved to `outputs/feature_importance_v3.csv`

**Key Features Analyzed**:
- Rolling averages (8-game window)
- Exponential moving averages (EMA)
- Momentum indicators
- Weather features (temperature, wind, precipitation)
- EPA metrics, success rates
- Betting odds and line movement

**Status**: ✅ Updated for v3 with momentum

#### `src/scripts/analyze_features.py`
**Purpose**: Feature analysis baseline (v2 comparison)  
**Usage**: `python src/scripts/analyze_features.py`  
**Output**: `FEATURE_IMPORTANCE_REPORT.md` in reports/  
**Status**: ✅ Historical reference, v3 recommended

#### `src/scripts/check_features.py`
**Purpose**: Verify which features are available and being used  
**Usage**: `python src/scripts/check_features.py`  
**Useful For**: Debugging missing features, validating data loading  
**Status**: ✅ Active diagnostic tool

#### `src/scripts/debug_momentum.py`
**Purpose**: Detailed analysis of momentum feature calculations  
**Usage**: `python src/scripts/debug_momentum.py`  
**Outputs**: Momentum feature values, calculations, impact verification  
**Status**: ✅ For validating momentum calculations

---

### 🔧 Diagnostics & Validation

#### `src/scripts/diagnostics.py`
**Purpose**: Run comprehensive model sanity checks  
**Usage**: `python src/scripts/diagnostics.py`  
**Checks**:
- Data loading (SQLite vs Excel fallback)
- Feature availability
- Train/test split validity
- Model prediction shapes and ranges
- Feature scaling validation
- Numerical stability checks

**Output**: `outputs/diagnostics.txt`  
**Status**: ✅ Uses SQLite data, essential before predictions

#### `src/scripts/inspect_odds_feed.py`
**Purpose**: Validate betting odds data integrity  
**Usage**: `python src/scripts/inspect_odds_feed.py`  
**Checks**: 
- Odds data availability by game
- Line movement patterns
- Moneyline consistency
- Missing data detection

**Status**: ✅ Active for betting data validation

#### `src/scripts/quick_weather_test.py`
**Purpose**: Validate weather features from SQLite  
**Usage**: `python src/scripts/quick_weather_test.py`  
**Checks**:
- Weather data availability
- Indoor vs outdoor games
- Feature engineering accuracy
- Temperature/wind/precipitation validity

**Status**: ✅ Uses SQLite, validates weather integration

---

### ⚙️ Tuning & Optimization

#### `src/scripts/tune_v3.py`
**Purpose**: Hyperparameter tuning for v3 model  
**Usage**: `python src/scripts/tune_v3.py`  
**Grid Search Parameters**:
- Random forest: n_estimators, max_depth, min_samples_leaf
- Ridge regression: alpha values
- Other ensemble parameters

**Output**: Tuning results to `reports/tuning_v3.json` and `TUNING_V3.md`  
**Data Source**: ✅ SQLite-enabled  
**Status**: ✅ Recently run, optimized hyperparameters available

---

### 📥 Data Integration & Backfill

#### `src/scripts/backfill_weather.py`
**Purpose**: Populate/update weather features in SQLite database  
**Usage**: `python src/scripts/backfill_weather.py`  
**Data Sources**: 
- Historical weather API integration
- Game location and date matching
- Temperature, wind, precipitation, humidity

**Status**: ✅ Active, maintains weather columns

#### `src/scripts/backfill_historical_data.py`
**Purpose**: Populate historical stats and advanced metrics  
**Usage**: `python src/scripts/backfill_historical_data.py`  
**Data Types**:
- EPA metrics from play-by-play
- Success rates
- Advanced offensive/defensive stats
- Situational conversions

**Status**: ✅ Core data population utility

#### `src/scripts/integrate_pfr_data.py`
**Purpose**: Scrape and integrate Pro Football Reference data into SQLite  
**Usage**: `python src/scripts/integrate_pfr_data.py`  
**Data Integrated**:
- Team season stats
- Advanced passing (QB)
- Advanced rushing (RB)
- Advanced receiving (WR/TE)
- Advanced defense (Individual defenders)
- Situational conversions, scoring breakdown

**PFR Tables**: 14 tables with player-level detail  
**Status**: ✅ Core integration, enables advanced features

#### `src/scripts/migrate_to_sqlite.py`
**Purpose**: Migrate from Excel to SQLite database  
**Usage**: `python src/scripts/migrate_to_sqlite.py`  
**Status**: ✅ Historical utility, migration complete (1,690 games)

#### `src/scripts/fetch_upcoming_games.py`
**Purpose**: Mark games in SQLite as upcoming/prediction targets  
**Usage**: `python src/scripts/fetch_upcoming_games.py`  
**Status**: ✅ Utility for setting up prediction jobs

#### `src/scripts/set_prediction_targets.py`
**Purpose**: Configure which games should be predicted  
**Usage**: `python src/scripts/set_prediction_targets.py`  
**Status**: ✅ Utility for targeting predictions

---

### 📈 Specialized Analysis

#### `src/scripts/record_predictions.py`
**Purpose**: Log predictions to CSV with timestamp and metadata  
**Usage**: Called by predict_upcoming.py  
**Output**: Appends to `outputs/prediction_log.csv`  
**Status**: ✅ Active logging system

#### `src/scripts/run_ensemble_oneoff.py`
**Purpose**: Run ensemble prediction for single game or set of games  
**Usage**: Edit HOME/AWAY/API key in script, then `python src/scripts/run_ensemble_oneoff.py`  
**Features**: 
- Multi-model ensemble
- API integration (optional)
- Single game or multiple game modes

**Status**: ✅ Flexible prediction tool

#### `src/scripts/extract_predictions.py`
**Purpose**: Extract and reformat predictions from prior prediction runs (post-processing)  
**Usage**: 
```bash
# Extract all predictions
python src/scripts/extract_predictions.py --input outputs/predictions_playoffs_week1_2026-01-10.csv

# Extract specific games only
python src/scripts/extract_predictions.py --input outputs/prediction_log.csv --games BUF@JAX SFO@PHI

# Combine variants
python src/scripts/extract_predictions.py --input outputs/prediction_log.csv --combine-variants
```
**Note**: POST-PROCESSING only. For NEW predictions, use `predict_upcoming.py`  
**Status**: ✅ Consolidated utility (merged predict_week1_round2.py and predict_playoffs_week1_round2.py)

---

## Models

### `src/models/model_v3.py` ⭐ **PRODUCTION**
**Type**: RandomForest with momentum features  
**Status**: ✅ **ACTIVE** - All predictions use this model  
**Data Source**: SQLite-first (prefers 1,690 games)  
**Architecture**:
- Base model: RandomForest (300-1000 trees, configurable)
- Feature engineering: 8-game rolling window, EMA, momentum
- Input features: 230+ candidate features
- Output: Margin prediction, total prediction
- Validation: Time-series split (preserve temporal ordering)

**Key Methods**:
- `__init__(prefer_sqlite=True)`: Initialize with SQLite preference
- `load_workbook()`: Auto-detects SQLite, loads 1,690 games if available
- `_prepare_team_games_with_week()`: Handles Excel/SQLite column naming differences
- `fit()`: Train on full data with momentum features
- `predict_game()`: Single game prediction with spread/total/win prob

**Recent Updates**:
- Added `prefer_sqlite=True` parameter (default for all predictions)
- Fixed column naming: `is_home (0/1)` (Excel) ↔ `is_home_0_1` (SQLite)
- Fixed `neutral_site` column handling across data sources
- Verified loading 1,690 games via SQLite

**Typical Prediction Accuracy**: 
- Margin MAE: 1.8-1.9 points
- Potential: 1.2-1.4 with data gaps filled

**Status**: ✅ Production-ready, tested extensively

---

### `src/models/model_v4.py` 🧪 **EXPERIMENTAL**
**Type**: Advanced ensemble with multiple sub-models  
**Status**: ⚠️ **RESEARCH ONLY** - Not recommended for production  
**Purpose**: Test new architectures and feature combinations  
**Comparison**: Use `compare_v4_vs_v3.py` to evaluate vs v3  
**Status**: For evaluation/experimentation

---

### `src/models/base.py`
**Purpose**: Base model class with common functionality  
**Contains**: 
- Common training/evaluation methods
- Feature engineering utilities
- Cross-validation setup
- Utility functions used by v3/v4

**Status**: ✅ Core infrastructure

---

### `src/models/archive/`
**Purpose**: Archive older model versions (v0, v1, v2)  
**When to Use**: 
- Historical comparison (use compare_all_versions.py)
- Understanding model evolution
- Backfilling with older models

**Status**: ✅ Historical reference

---

## Data & Database

### SQLite Database: `data/nfl_model.db`

**Current Status**: ✅ Active, contains 1,690 games (2020-2025)  
**Default Data Source**: All v3 predictions use SQLite  
**Schema**: 26 tables, 573 columns  
**Games Covered**: 2020-2025 regular + playoff seasons

#### Core Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `games` | 1,690 | Game fundamentals: scores, dates, weather, rest |
| `team_games` | 544 | Per-game team stats (56 columns) |

#### Offensive & Defensive Stats

| Table | Purpose |
|-------|---------|
| `offense_team_games` | Offensive metrics per game |
| `defense_team_games` | Defensive metrics per game |
| `passing` | Passing stats per team/game |
| `rushing` | Rushing stats per team/game |

#### Special Teams & Situational

| Table | Purpose |
|-------|---------|
| `penalties_team_games` | Penalty statistics |
| `punting_team_games` | Punting metrics |
| `pfr_situational_conversions` | 3rd/4th down conversions |
| `pfr_situational_drives` | Drive-level statistics |
| `pfr_situational_scoring` | Scoring breakdown |

#### Advanced Stats (Player-Level Detail)

| Table | Rows | Purpose |
|-------|------|---------|
| `pfr_advanced_passing` | 553 | Individual QB stats |
| `pfr_advanced_rushing` | 1,869 | Individual RB stats |
| `pfr_advanced_receiving` | 2,687 | Individual WR/TE stats |
| `pfr_advanced_defense` | 4,989 | Individual defender stats |
| `pfr_team_stats` | Seasonal | Team aggregate stats |
| `pfr_team_defense` | Seasonal | Team defensive stats |

#### Betting & Odds

| Table | Rows | Purpose |
|-------|------|---------|
| `odds` | 272 | Opening/closing spreads, moneylines |
| `opening_odds_source` | - | Line opening history |
| `moneylines_source` | - | Moneyline history |
| `odds_team_games` | - | Per-team odds context |

#### Reference Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `pfr_games` | 1,413 | PFR game references |
| `pfr_team_gamelogs` | 3,048 | Team per-game logs |

**Data Loading**: Model automatically loads via `prefer_sqlite=True` in v3  
**Fallback**: Excel only if SQLite unavailable  
**Verification**: Run `python audit_db.py` for schema audit

---

### Excel Data: `data/nfl_2025_model_data_with_moneylines.xlsx`

**Purpose**: Legacy data source (fallback only)  
**Status**: ✅ Still available but deprecated  
**When Used**: Only if SQLite unavailable (not recommended)  
**Games**: 277 rows (subset of 1,690 in SQLite)  
**Note**: Model automatically prefers SQLite (1,690 games)

---

### PFR Scraper Data

**Purpose**: Raw PFR data before integration into SQLite  
**Status**: ✅ Integrated, see `src/scripts/integrate_pfr_data.py`  
**Output Location**: Processed into `data/nfl_model.db`

---

## Reports & Analysis

All report files are in `reports/` directory. These are generated analysis documents.

### Model Comparison & Validation

| File | Purpose |
|------|---------|
| `MODEL_V1_COMPARISON.md` | V0 vs V1 detailed comparison |
| `MODEL_V3_BREAKTHROUGH.md` | V3 architectural improvements |
| `V0_V1_V2_COMPARISON.md` | Historical progression |
| `V0_V3_COMPARISON.md` | Baseline vs current model |
| `V0_V3_VARIANTS_COMPARISON.md` | V3 variants tested |
| `V0_V3_VARIANTS_COMPARISON_001.md` | Additional variant analysis |

### Feature Analysis

| File | Purpose |
|------|---------|
| `FEATURE_IMPORTANCE_REPORT.md` | Top features for v3 |

### Tuning & Configuration

| File | Purpose |
|------|---------|
| `tuning_v3.json` | Hyperparameter values (JSON) |
| `TUNING_V3.md` | Tuning results and methodology |

### Investigation Reports

| File | Purpose |
|------|---------|
| `INVESTIGATION_COMPLETE.md` | Investigation summary |

---

## Strategic Documents

Key planning and status documents in project root.

### ✅ Integration & Status

| File | Purpose |
|------|---------|
| `SQLITE_INTEGRATION_COMPLETE.md` | SQLite implementation complete |
| `DATA_SOURCE_VALIDATION.md` | Validation that SQLite loads correctly |

### 📋 Postgame & Retraining

| File | Purpose |
|------|---------|
| `POSTGAME_INCORPORATION_STRATEGY.md` | How to incorporate postgame results |
| `POSTGAME_STATUS_FINAL.md` | Latest postgame retraining status |

### 📊 Data Enhancement Planning

| File | Purpose |
|------|---------|
| `PFR_DATA_GAPS_ANALYSIS.md` | 15 missing data points identified |
| `PFR_INTEGRATION_ROADMAP.md` | Technical roadmap for enhancements |
| `PFR_SCRAPER_QUICKSTART.md` | How to use PFR scraper utilities |
| `DATA_ENHANCEMENT_VISUAL.md` | Visual impact of data enhancements |
| `MISSING_DATA_SUMMARY.md` | Quick reference for gaps |

### 📚 Historical & Planning

| File | Purpose |
|------|---------|
| `HISTORICAL_BACKFILL_GUIDE.md` | Historical data population guide |
| `INVENTORY_AND_REFACTOR_PLAN.md` | Refactoring strategy |
| `COMMIT_INSTRUCTIONS.md` | Git commit guidelines |
| `COMMIT_INSTRUCTIONS_ARCHIVE.md` | Historical commit patterns |

---

## Utilities

Located in `src/utils/` - helper modules used by all scripts.

### Core Utilities

#### `paths.py`
**Purpose**: Path management and directory utilities  
**Exports**:
- Project root path
- Data directory paths
- Output directory paths
- SQLite database path

**Usage**: `from src.utils.paths import PROJECT_ROOT, DATA_DIR, DB_PATH`

#### `weather.py`
**Purpose**: Weather data retrieval and feature engineering  
**Functions**:
- Fetch historical weather
- Calculate wind chill, heat index
- Weather feature engineering
- Indoor game detection

**Usage**: Weather features automatically applied in model

#### `pfr_scraper.py`
**Purpose**: Pro Football Reference data scraping  
**Capabilities**:
- Scrape team stats
- Scrape advanced passing/rushing/receiving/defense stats
- Player-level data extraction
- Situational stats extraction

**Usage**: Called by `src/scripts/integrate_pfr_data.py`  
**Documentation**: See `PFR_SCRAPER_README.md`

#### `espn_scraper.py`
**Purpose**: ESPN data scraping utilities  
**Status**: ✅ Available for extended integration

#### `schedule.py`
**Purpose**: NFL schedule utilities  
**Functions**:
- Get upcoming games
- Parse schedule data
- Week/date handling

#### `stadiums.py`
**Purpose**: Stadium information and data  
**Contains**: Stadium names, locations, indoor/outdoor status  
**Usage**: Weather feature enrichment, location normalization

---

## Configuration & Testing

### Configuration Files

#### `requirements.txt`
**Purpose**: Python package dependencies  
**Status**: ✅ Up to date  
**Key Packages**:
- pandas: Data manipulation
- scikit-learn: ML models (RandomForest, Ridge)
- numpy: Numerical computing
- joblib: Model serialization
- requests: API calls
- beautifulsoup4: Web scraping (PFR)
- Other data/utility packages

**Setup**:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### Testing & Audit Scripts

#### `audit_db.py`
**Purpose**: Comprehensive SQLite schema audit  
**Usage**: `python audit_db.py`  
**Output**: 
- 26 tables listed with row counts
- 573 columns documented with types
- Data availability summary
- Games coverage (1,690 total)

**Status**: ✅ Essential validation tool

#### `test_espn.py`
**Purpose**: Test ESPN scraper functionality  
**Usage**: `python test_espn.py`  
**Status**: ✅ Development/testing only

#### `display_jan12_predictions.py`
**Purpose**: Format and display predictions nicely  
**Usage**: `python display_jan12_predictions.py`  
**Status**: ✅ Utility for output formatting

#### `archive_old_models.py`
**Purpose**: Automate archiving of old model versions  
**Usage**: `python archive_old_models.py`  
**Batch Script**: `archive_old_models.bat` (Windows batch wrapper)  
**Status**: ✅ Model housekeeping utility

---

## Critical File Locations (Quick Reference)

### For Making Predictions
- **Model code**: [src/models/model_v3.py](src/models/model_v3.py)
- **Primary script (default)**: [src/scripts/predict_ensemble_multiwindow.py](src/scripts/predict_ensemble_multiwindow.py)
- **Alternative (single-run)**: [src/scripts/predict_upcoming.py](src/scripts/predict_upcoming.py)
- **Output log**: [outputs/prediction_log.csv](outputs/prediction_log.csv)
- **Database**: [data/nfl_model.db](data/nfl_model.db)

### For Understanding Model
- **Feature analysis**: [src/scripts/analyze_v3_features.py](src/scripts/analyze_v3_features.py)
- **Model comparison**: [src/scripts/compare_all_versions.py](src/scripts/compare_all_versions.py)
- **Reports**: [reports/](reports/) directory

### For Data & Integration
- **Database audit**: `python audit_db.py`
- **PFR scraper**: [src/utils/pfr_scraper.py](src/utils/pfr_scraper.py)
- **Weather data**: [src/utils/weather.py](src/utils/weather.py)
- **Data backfill**: [src/scripts/backfill_weather.py](src/scripts/backfill_weather.py)

### For Planning & Enhancement
- **Data gaps**: [PFR_DATA_GAPS_ANALYSIS.md](PFR_DATA_GAPS_ANALYSIS.md)
- **Enhancement roadmap**: [PFR_INTEGRATION_ROADMAP.md](PFR_INTEGRATION_ROADMAP.md)
- **Implementation timeline**: [MISSING_DATA_SUMMARY.md](MISSING_DATA_SUMMARY.md)

---

## Recent Predictions (Latest)

**Generated**: 2026-01-11 00:13:29 UTC  
**Data Source**: SQLite (1,690 games, 2020-2025)  
**Model**: v3 with momentum features  

| Game | Spread | Total | Home Win % |
|------|--------|-------|------------|
| BUF @ JAX | 0.8 | 51.6 | 47.8% |
| SFO @ PHI | -5.4 | 45.2 | 64.9% |
| LAC @ NWE | -3.1 | 47.2 | 58.6% |

**All predictions logged to**: [outputs/prediction_log.csv](outputs/prediction_log.csv)

---

## Troubleshooting & FAQ

### "Model is loading Excel instead of SQLite"
- **Check**: Ensure `data/nfl_model.db` exists
- **Fix**: Run `python audit_db.py` to verify database
- **Verify**: Script should log `[SQLite] Loading: 1690 games...`

### "Feature X is missing"
- **Debug**: Run `python src/scripts/check_features.py`
- **Common**: Missing weather backfill - run `python src/scripts/backfill_weather.py`
- **PFR data**: Run `python src/scripts/integrate_pfr_data.py`

### "Predictions seem off"
- **Step 1**: Run `python src/scripts/diagnostics.py`
- **Step 2**: Run `python src/scripts/quick_weather_test.py`
- **Step 3**: Compare with `python src/scripts/compare_all_versions.py`
- **Check**: Latest postgame status in `POSTGAME_STATUS_FINAL.md`

### "Want to improve predictions"
- **Read**: [PFR_DATA_GAPS_ANALYSIS.md](PFR_DATA_GAPS_ANALYSIS.md) (25-35% improvement potential identified)
- **Next Steps**: [PFR_INTEGRATION_ROADMAP.md](PFR_INTEGRATION_ROADMAP.md) (technical roadmap)
- **Quick Wins**: Injury data + snap counts (highest priority)

---

## Development Status

### ✅ Complete & Active
- SQLite integration (1,690 games, 2020-2025)
- Model v3 with momentum features
- Weather feature engineering (7 features)
- Advanced stats (EPA, success rates)
- Betting odds integration
- Prediction generation system
- Feature importance analysis
- Model comparison framework
- Hyperparameter tuning

### 🟡 In Progress / Planned
- Injury data integration (HIGHEST priority)
- Snap count data (HIGH priority)
- Red zone detail analysis (HIGH priority)
- Vegas line movement tracking (MEDIUM priority)
- See [PFR_INTEGRATION_ROADMAP.md](PFR_INTEGRATION_ROADMAP.md) for full roadmap

### 📈 Potential Improvements
- Current accuracy: MAE 1.8-1.9 pts
- With data gaps filled: MAE 1.2-1.4 pts (25-35% improvement)
- Injury data alone: -0.4 to -0.5 pts improvement
- Snap counts: -0.2 pts improvement

---

## Getting Started (For New Contributors)

1. **Setup**: Follow "Configuration Files" section above
2. **Verify**: Run `python audit_db.py` to confirm SQLite works
3. **Try**: Generate a prediction: `python src/scripts/predict_upcoming.py --week 1 --train-through 18 --playoffs`
4. **Explore**: Read [PFR_DATA_GAPS_ANALYSIS.md](PFR_DATA_GAPS_ANALYSIS.md) for enhancement opportunities
5. **Understand**: Run `python src/scripts/analyze_v3_features.py` to see what the model learns

---

## File Inventory Summary

| Category | Count | Key Files |
|----------|-------|-----------|
| Scripts | 15 | predict_upcoming.py, compare_all_versions.py, extract_predictions.py, analyze_v3_features.py |
| Models | 3 active + archive | model_v3.py (production), model_v4.py (experimental), base.py + v0/v1/v2 in archive/ |
| Reports | 9 | MODEL_V3_BREAKTHROUGH.md, FEATURE_IMPORTANCE_REPORT.md |
| Strategic Docs | 10 | PFR_DATA_GAPS_ANALYSIS.md, PFR_INTEGRATION_ROADMAP.md |
| Utilities | 7 | paths.py, weather.py, pfr_scraper.py |
| Data Files | 8+ | nfl_model.db (main), Excel workbook (legacy) |
| Output Files | 10+ | prediction_log.csv, feature_importance_v3.csv |
| Config | 2 | requirements.txt, .gitignore |
| **Total** | **~65** | Consolidated & optimized (cleaned up from 70+) |

**Recent Consolidations** ✅:
- Merged `predict_week1_round2.py` + `predict_playoffs_week1_round2.py` → `extract_predictions.py`
- Moved v0, v1, v2 models to `src/models/archive/`
- Deleted test log files (4 files)

---

**Questions?** Check the relevant section above or read the specific strategic document for your task.

