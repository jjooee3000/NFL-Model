# NFL Model - Quick Reference

**Last Updated**: 2026-01-11  
**Purpose**: Fast command reference for common tasks

---

## 🚀 Most Common Commands

### Generate Predictions

**Simple prediction (fastest)**:
```powershell
python src/scripts/predict_upcoming.py --week 1 --train-through 18 --playoffs
```

**Ensemble prediction (most accurate)**:
```powershell
python src/scripts/predict_ensemble_multiwindow.py --week 1 --playoffs
```

**Specific games**:
```powershell
python src/scripts/predict_ensemble_multiwindow.py --week 1 --games SF@PHI LAC@NE HOU@PIT
```

### Train Model

**Train and evaluate**:
```powershell
python src/models/model_v3.py --model randomforest --train-week 18
```

**With XGBoost**:
```powershell
python src/models/model_v3.py --model xgboost --train-week 18
```

### Update Database

**Update game scores**:
```powershell
python src/scripts/update_postgame_scores.py
```

**Full daily sync**:
```powershell
python src/scripts/pipeline_daily_sync.py --season 2025
```

### Start API Server

**Development (auto-reload)**:
```powershell
python -m uvicorn nfl_model.services.api.app:app --reload --app-dir src
```

**Production**:
```powershell
python -m uvicorn nfl_model.services.api.app:app --app-dir src --port 8001
```

---

## 📊 View Results

### View Predictions

**Latest predictions**:
```powershell
Get-Content outputs/prediction_log.csv -Tail 20
```

**Specific date**:
```powershell
Get-Content outputs/ensemble_multiwindow_2026-01-11*.csv
```

### Check Model Performance

**View training output**:
```powershell
python src/models/model_v3.py --train-week 18
# Look for: margin_MAE_test, total_MAE_test
```

**Feature importance**:
```powershell
Get-Content outputs/feature_importance_v3.csv | Select-Object -First 20
```

---

## 🗄️ Database Operations

### Query Games

**Count games**:
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/nfl_model.db'); print(f'Total games: {conn.execute(\"SELECT COUNT(*) FROM games\").fetchone()[0]}'); conn.close()"
```

**Recent games**:
```powershell
python -c "import sqlite3, pandas as pd; conn = sqlite3.connect('data/nfl_model.db'); df = pd.read_sql('SELECT game_id, home_team, away_team, home_score, away_score FROM games ORDER BY gameday DESC LIMIT 10', conn); print(df); conn.close()"
```

### Audit Database

**Full audit**:
```powershell
python audit_db.py
```

**Clean duplicates**:
```powershell
python src/scripts/clean_sqlite_db.py --mode audit
python src/scripts/clean_sqlite_db.py --mode apply  # After review
```

---

## 📈 Analysis

### Feature Analysis

**Correlation analysis**:
```powershell
python src/scripts/analyze_correlations.py
```

**Model comparison**:
```powershell
python src/scripts/compare_v0_v3.py
```

### Model Diagnostics

**Run diagnostics**:
```powershell
python src/scripts/diagnostics.py
```

**Test weather features**:
```powershell
python src/scripts/quick_weather_test.py
```

---

## 🔧 Data Management

### Backfill Data

**Historical games**:
```powershell
python src/scripts/backfill_historical_data.py --start-year 2015 --end-year 2019
```

**Weather data**:
```powershell
python src/scripts/backfill_weather.py
```

### Pro Football Reference

**Fetch PFR data**:
```powershell
python src/scripts/fetch_pfr_nflscrapy.py --season 2024
```

**Import PFR historical**:
```powershell
python src/scripts/import_pfr_historical.py --season 2020
```

**Integrate PFR data**:
```powershell
python src/scripts/integrate_pfr_data.py
```

---

## 🛠️ Utilities

### Archive Old Models

```powershell
python archive_old_models.py
# Or: .\archive_old_models.bat
```

### Hyperparameter Tuning

```powershell
python src/scripts/tune_v3.py
```

### Set Prediction Targets

```powershell
python src/scripts/set_prediction_targets.py --week 1 --season 2025
```

---

## 🌐 API Usage

### Endpoints (when API running)

**Health check**:
```bash
curl http://localhost:8000/health
```

**List games**:
```bash
curl "http://localhost:8000/games?season=2025&week=1"
```

**Get prediction**:
```bash
curl http://localhost:8000/predictions/2025_01_SF_PHI
```

**Run prediction (POST)**:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"season": 2025, "week": 1, "playoffs": true}'
```

**View docs**:
- Navigate to: `http://localhost:8000/docs`

---

## 📁 Key File Locations

### Data
- **Database**: `data/nfl_model.db`
- **Current season**: `data/nfl_2025_model_data_with_moneylines.xlsx`
- **Historical PFR**: `data/pfr_historical/`

### Code
- **Model**: `src/models/model_v3.py`
- **Predict script**: `src/scripts/predict_ensemble_multiwindow.py`
- **Update scores**: `src/scripts/update_postgame_scores.py`
- **API**: `src/nfl_model/services/api/app.py`

### Outputs
- **Predictions**: `outputs/prediction_log.csv`
- **Ensemble**: `outputs/ensemble_multiwindow_*.csv`
- **Feature importance**: `outputs/feature_importance_v3.csv`

### Documentation
- **Main index**: `docs/README.md`
- **Getting started**: `docs/guides/GETTING_STARTED.md`
- **Architecture**: `docs/architecture/SYSTEM_ARCHITECTURE.md`

---

## 🆘 Troubleshooting

### Model Won't Train

**Check database**:
```powershell
Test-Path data/nfl_model.db
```

**Verify data**:
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/nfl_model.db'); print(f'Games: {conn.execute(\"SELECT COUNT(*) FROM games\").fetchone()[0]}'); conn.close()"
```

### Predictions Fail

**Update scores first**:
```powershell
python src/scripts/update_postgame_scores.py
```

**Check for upcoming games**:
```powershell
python -c "import sqlite3, pandas as pd; conn = sqlite3.connect('data/nfl_model.db'); df = pd.read_sql('SELECT game_id, week, home_team, away_team FROM games WHERE home_score IS NULL AND week > 0 LIMIT 5', conn); print(df); conn.close()"
```

### API Won't Start

**Check port availability**:
```powershell
netstat -ano | findstr :8000
```

**Use different port**:
```powershell
python -m uvicorn nfl_model.services.api.app:app --app-dir src --port 8001
```

### Module Not Found

**Activate venv**:
```powershell
.\.venv\Scripts\Activate.ps1
```

**Install requirements**:
```powershell
pip install -r requirements.txt
```

---

## 🎯 Common Workflows

### Weekly Prediction Workflow

```powershell
# 1. Update database
python src/scripts/update_postgame_scores.py

# 2. Generate predictions
python src/scripts/predict_ensemble_multiwindow.py --week 1 --playoffs

# 3. View results
Get-Content outputs/ensemble_multiwindow_*.csv -Tail 10

# 4. (Optional) Evaluate after games complete
python src/scripts/update_postgame_scores.py
# Check prediction accuracy in outputs/postgame_eval_*.csv
```

### Model Improvement Workflow

```powershell
# 1. Train baseline
python src/models/model_v3.py --train-week 18

# 2. Analyze features
python src/scripts/analyze_correlations.py

# 3. Make code changes to model

# 4. Re-train and compare
python src/models/model_v3.py --train-week 18

# 5. Validate on historical games
python test_week10_predictions.py
```

### Data Refresh Workflow

```powershell
# 1. Fetch latest scores
python src/scripts/update_postgame_scores.py

# 2. (Optional) Fetch PFR data
python src/scripts/fetch_pfr_nflscrapy.py --season 2025

# 3. (Optional) Integrate PFR
python src/scripts/integrate_pfr_data.py

# 4. Clean database
python src/scripts/clean_sqlite_db.py --mode audit
python src/scripts/clean_sqlite_db.py --mode apply

# 5. Run daily sync (all-in-one)
python src/scripts/pipeline_daily_sync.py --season 2025
```

---

## 💡 Pro Tips

### Performance

- Use `--train-through 18` for best accuracy
- Ensemble predictions are more accurate but slower
- Single model predictions are 100x faster

### Data Quality

- Run `audit_db.py` regularly to check data integrity
- Clean database before important prediction runs
- Update scores immediately after games complete

### Feature Engineering

- Check `outputs/feature_importance_v3.csv` to see which features matter
- Focus improvements on top 20 features
- Weather features have moderate impact (indoor vs outdoor)

### Model Selection

- RandomForest is currently best (7.02 MAE)
- XGBoost comparable but no better (11.13 MAE with default train_week)
- v4 is experimental, use v3 for production

---

## 📚 Related Documentation

- **[Getting Started Guide](../guides/GETTING_STARTED.md)** - First-time setup
- **[File Locations](FILE_LOCATIONS.md)** - Where everything is
- **[System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)** - How it works
- **[Model Architecture](../architecture/MODEL_ARCHITECTURE.md)** - Model details

---

**Quick Navigation**: [Main Docs](../README.md) | [Architecture](../architecture/) | [Analysis](../analysis/) | [Development](../development/)
