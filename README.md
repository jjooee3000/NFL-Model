# NFL Model Workspace

**Production-Ready NFL Point Spread Prediction Model**  
Database-first architecture with automated pipelines, FastAPI service, and comprehensive feature engineering.

**Current Performance**: 7.02 MAE (28% improvement over baseline)  
**Model**: RandomForest with 275 features (38 base × 6 variants + 29 interactions)  
**Database**: SQLite with 2,474 games (2020-2025)

---

## 📚 Documentation

**👉 For complete documentation, see [docs/README.md](docs/README.md)**

### Quick Links

**New Users**:
- [Getting Started Guide](docs/guides/GETTING_STARTED.md) - Complete setup and first prediction
- [Quick Reference](docs/guides/QUICK_REFERENCE.md) - Common commands and tasks
- [File Locations](docs/guides/FILE_LOCATIONS.md) - Where to find everything

**Technical Details**:
- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md) - System design and data flow
- [Database Schema](docs/architecture/SQLITE_INTEGRATION_COMPLETE.md) - Database structure
- [PFR Data Catalog](docs/architecture/PFR_DATA_CATALOG.md) - Available data sources

**Performance & Analysis**:
- [Model Improvement Strategy](docs/development/MODEL_IMPROVEMENT_STRATEGY.md) - Current improvement roadmap
- [Weather Impact Analysis](docs/analysis/WEATHER_IMPACT_ANALYSIS.md) - Weather feature evaluation
- [Feature Interactions Results](docs/development/FEATURE_INTERACTIONS_RESULTS.md) - Latest enhancements

---

## ⚡ Quick Start

### Installation
```powershell
# Install dependencies
pip install -r requirements.txt
```

### Make a Prediction
```powershell
# Predict playoff week 1
& ".venv/Scripts/python.exe" src/scripts/predict_ensemble_multiwindow.py --season 2025 --week 1 --playoffs
```

#### Use Cached Models (Persistence)
```powershell
# Use cached model if available (fast path)
& ".venv/Scripts/python.exe" src/scripts/predict_ensemble_multiwindow.py --season 2025 --week 1 --playoffs

# Force retrain and refresh cache
& ".venv/Scripts/python.exe" src/scripts/predict_ensemble_multiwindow.py --season 2025 --week 1 --playoffs --force-retrain

# Upcoming targets with caching
& ".venv/Scripts/python.exe" src/scripts/predict_upcoming.py --week 19 --train-through 18
```

**Benchmark (single window, default variant):** Cold retrain ~9.5s vs cached ~3.8s (week 1, train_windows=[14]).

### Start API Server
```powershell
# Launch FastAPI service
& ".venv/Scripts/python.exe" -m uvicorn nfl_model.services.api.app:app --reload --app-dir src
```

**API Endpoints**:
- `GET /health` - Server status
- `GET /games?season=2025&week=1` - List games
- `GET /predictions/{game_id}` - Get prediction
- `POST /predict` - Generate predictions

---

## 📁 Project Structure

```
NFL-Model/
├── docs/                    # 📚 Complete documentation (START HERE)
│   ├── README.md           # Documentation index
│   ├── guides/             # User guides and tutorials
│   ├── architecture/       # System design docs
│   ├── analysis/           # Performance reports
│   ├── development/        # Development progress
│   └── archive/            # Historical docs
│
├── src/                    # Source code
│   ├── models/             # Prediction models (v3 = production)
│   ├── scripts/            # Data pipelines and prediction scripts
│   └── utils/              # Database, feature engineering utilities
│
├── data/                   # Data storage
│   ├── nfl_model.db        # SQLite database (2,474 games)
│   └── pfr_historical/     # Pro Football Reference CSVs
│
└── outputs/                # Predictions and reports
    ├── ensemble_multiwindow_*.csv  # Multi-window predictions
    ├── feature_importance_v3.csv   # Feature rankings
    └── prediction_log.csv          # All predictions log
```

---

## 🚀 Core Features

### Data Pipeline
- **Automated Sync**: Daily postgame updates and data cleaning
- **Multiple Sources**: ESPN API, Pro Football Reference, NFLScrapy
- **Data Integrity**: Unique indexes, deduplication, ingestion logging

### Prediction Model (v3)
- **Algorithm**: RandomForest (200 trees, max_depth=20)
- **Features**: 275 total
  - 38 base features (offense, defense, situational)
  - 6 variants per feature (pre8, ema8, trend8, vol8, season_avg, recent_ratio)
  - 29 interaction features (11 categories)
- **Performance**: 7.02 MAE on recent data

### Feature Engineering
- **Rolling Windows**: 8-game, 4-game, recent performance
- **Exponential Moving Average**: Weighted recent performance
- **Momentum & Volatility**: Trend detection and consistency metrics
- **Interactions**: Offense-defense matchups, weather impacts, situational adjustments

### FastAPI Service
- **Game Browsing**: Query games by season, week, team
- **Predictions**: On-demand prediction generation
- **Monitoring**: Health checks and status endpoints

### Testing Infrastructure ⚡ NEW
- **Automated Tests**: 105 test cases with 90.5% pass rate
- **Coverage**: 74% on core model (model_v3.py)
- **CI/CD**: GitHub Actions workflow for automated testing
- **Test Categories**: Unit, integration, API, database tests

---

## 🧪 Testing

### Run Tests
```powershell
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src/models --cov=src/utils --cov-report=html

# Run specific test categories
pytest -m "unit"                  # Fast unit tests only
pytest -m "integration"           # Integration tests
pytest -m "not slow"              # Exclude slow tests
```

### Test Files
- **test_model_v3.py** - Model initialization, features, training, predictions (20 tests)
- **test_feature_builder.py** - Feature engineering functions (31 tests)
- **test_database.py** - Database operations and integrity (27 tests)
- **test_api_endpoints.py** - API endpoints and responses (25 tests)

### Coverage Targets
- `src/models/model_v3.py`: **74%** ✅ (target: 70%+)
- Overall models & utils: 10.75% (expanding coverage)

**See**: [Testing Implementation Report](docs/TESTING_IMPLEMENTATION_REPORT.md)

---

## 🔧 VS Code Tasks

Use the Command Palette (Ctrl+Shift+P) → "Tasks: Run Task":
- **Run Daily Sync Pipeline** - Update scores and clean database
- **Run API (Uvicorn)** - Start FastAPI server
- **Run DB Schema Migrations** - Apply database schema updates
- **Run Weather Impact Comparison** - Analyze weather features
- **Run Tests** - Execute pytest test suite (coming soon)

---

## 📊 Model Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **MAE** | 7.02 | Mean Absolute Error (train_week=18) |
| **Improvement** | 28% | vs baseline (9.77 MAE) |
| **Features** | 275 | 38 base × 6 variants + 29 interactions |
| **Training Data** | 2,474 games | Seasons 2020-2025 |
| **Algorithm** | RandomForest | Outperforms XGBoost (11.06 vs 11.13 MAE) |

**Recent Validations**:
- Week 10 Historical: 3.14 MAE, 66.7% accuracy
- XGBoost Comparison: RandomForest superior by 0.07 MAE

---

## 🎯 Development Status

**Current Phase**: Model Enhancement & Validation  
**Last Updated**: 2026-01-11

##**Testing Infrastructure** - 105 automated tests with CI/CD workflow ⚡ NEW
- Feature interaction implementation (11 categories)
- XGBoost integration and comparison
- Historical validation framework
- Opponent-adjusted metrics design
- Comprehensive documentation restructuring

### Next Priorities 🎯
- Increase test coverage to 80%+ (currently 74% on core model)
### Next Priorities 🎯
- Expand historical validation across multiple weeks
- Implement opponent-adjusted metrics (placeholder ready)
- Advanced ensemble methods
- Real-time prediction monitoring

**See**: [Model Improvement Strategy](docs/development/MODEL_IMPROVEMENT_STRATEGY.md)

---

## 📖 Additional Resources

### Guides
- [PFR Scraper Quickstart](docs/guides/PFR_SCRAPER_QUICKSTART.md) - Data collection
- [Historical Backfill Guide](docs/guides/HISTORICAL_BACKFILL_GUIDE.md) - Adding historical data

### Development
- [Development Progress](docs/development/DEVELOPMENT_PROGRESS.md) - Implementation tracking
- [Commit Instructions](docs/development/COMMIT_INSTRUCTIONS.md) - Git workflow
- [Postgame Status](docs/development/POSTGAME_STATUS_FINAL.md) - Evaluation workflow

### Analysis
- [Postgame Analysis](docs/analysis/POSTGAME_ANALYSIS_2026-01-10.md) - Performance review
- [Postgame Evaluation](docs/analysis/POSTGAME_EVAL_2026-01-10.md) - Detailed metrics

---

## 🆘 Getting Help

1. **First-Time Users**: Start with [Getting Started Guide](docs/guides/GETTING_STARTED.md)
2. **Common Tasks**: Check [Quick Reference](docs/guides/QUICK_REFERENCE.md)
3. **Finding Files**: See [File Locations](docs/guides/FILE_LOCATIONS.md)
4. **Technical Details**: Review [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
5. **Legacy Docs**: Browse [Archive Index](docs/archive/ARCHIVE_INDEX.md)

---

**Last Updated**: 2026-01-11  
**Version**: 3.0  
**Status**: Production Ready
