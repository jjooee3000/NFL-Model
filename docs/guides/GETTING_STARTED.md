# NFL Model - Getting Started Guide

**Last Updated**: 2026-01-11  
**Audience**: New users, first-time setup  
**Time Required**: 15-30 minutes

---

## Prerequisites

- **Python**: 3.9 or higher
- **Operating System**: Windows (PowerShell), macOS, or Linux
- **Storage**: ~500 MB for data and environment
- **Internet**: Required for data fetching

---

## Installation

### 1. Clone or Download Project

```powershell
cd "C:\Users\[YourUsername]\Desktop\Sports Model"
# Project should be in: NFL-Model/
```

### 2. Create Virtual Environment

```powershell
cd NFL-Model
python -m venv .venv
```

### 3. Activate Virtual Environment

**Windows (PowerShell)**:
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**:
```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

**Key Packages Installed**:
- `pandas`, `numpy` - Data manipulation
- `scikit-learn` - Machine learning
- `xgboost` - Gradient boosting
- `openpyxl` - Excel file handling
- `fastapi`, `uvicorn` - API server
- `requests`, `beautifulsoup4` - Web scraping

---

## Verify Installation

### Check Database

```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/nfl_model.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM games'); print(f'Games in database: {cursor.fetchone()[0]}'); conn.close()"
```

**Expected Output**: `Games in database: 2474` (or similar)

### Test Model Import

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from models.model_v3 import NFLHybridModelV3; print('Model import successful!')"
```

**Expected Output**: `Model import successful!`

---

## Your First Prediction

### Option 1: Simple Prediction (Fastest)

Generate predictions for upcoming playoff games:

```powershell
python src/scripts/predict_upcoming.py --week 1 --train-through 18 --playoffs
```

**What happens**:
1. Loads data from SQLite database
2. Trains model through week 18
3. Generates predictions for week 1 playoff games
4. Saves results to `outputs/prediction_log.csv`

**Output Example**:
```
2025_01_SF_PHI: PHI -1.5 pts, Total 45.7, Win Prob: 54%
2025_01_LAC_NE: NE -1.5 pts, Total 45.7, Win Prob: 54%
2025_01_HOU_PIT: PIT -3.8 pts, Total 46.1, Win Prob: 60%
```

### Option 2: Multi-Window Ensemble (Most Accurate)

Use multiple training windows for better predictions:

```powershell
python src/scripts/predict_ensemble_multiwindow.py --week 1 --playoffs
```

**What happens**:
1. Trains 15 models (5 training windows × 3 variants)
2. Aggregates predictions via median
3. Provides detailed output with confidence intervals
4. Saves to `outputs/ensemble_multiwindow_[timestamp].csv`

**Runtime**: ~5-8 minutes

---

## Understanding the Output

### prediction_log.csv Format

| Column | Description | Example |
|--------|-------------|---------|
| `game_id` | Unique identifier | `2025_01_SF_PHI` |
| `week` | Week number | `1` |
| `away_team` | Visiting team | `SF` |
| `home_team` | Home team | `PHI` |
| `pred_margin_home` | Predicted margin (home perspective) | `-1.5` |
| `pred_total` | Predicted total points | `45.7` |
| `pred_winprob_home` | Home win probability | `0.54` |
| `timestamp` | When prediction was made | `2026-01-11 19:11:26` |

### Interpreting Results

**Margin**: 
- Positive = Home team favored
- Negative = Away team favored
- `PHI -1.5` means Philadelphia favored by 1.5 points

**Total**: Combined points scored by both teams

**Win Probability**: 
- 0.54 = 54% chance home team wins
- 0.46 = 46% chance away team wins

---

## Common First Tasks

### 1. View Recent Predictions

```powershell
Get-Content outputs/prediction_log.csv -Tail 10
```

### 2. Train Model for Analysis

```powershell
python src/models/model_v3.py --model randomforest --train-week 18
```

**Output**:
```
n_features: 275
margin_MAE_test: 7.02
total_MAE_test: 7.5
```

### 3. Start API Server

```powershell
python -m uvicorn nfl_model.services.api.app:app --reload --app-dir src
```

Then visit: `http://localhost:8000/docs`

### 4. Update Database with Latest Scores

```powershell
python src/scripts/update_postgame_scores.py
```

---

## Project Structure Overview

```
NFL-Model/
├── src/
│   ├── models/          # Model definitions (model_v3.py)
│   ├── scripts/         # Executable scripts
│   ├── utils/           # Helper modules
│   └── nfl_model/       # Main package
│
├── data/
│   └── nfl_model.db     # SQLite database (PRIMARY DATA)
│
├── outputs/             # Generated predictions
│
├── docs/                # Documentation (guides, architecture)
│
└── tests/               # Test files
```

---

## VS Code Integration (Recommended)

If using VS Code, pre-configured tasks are available:

1. **Ctrl+Shift+P** → "Tasks: Run Task"
2. Select from:
   - `Run Daily Sync Pipeline`
   - `Run API (Uvicorn)`
   - `Predict Upcoming Games`

### Configure VS Code

`.vscode/tasks.json` is already configured. Just press **Ctrl+Shift+B** to run default task.

---

## Troubleshooting

### "Module not found" Error

**Solution**: Ensure virtual environment is activated:
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Database Not Found

**Solution**: Database should exist at `data/nfl_model.db`. If missing:
```powershell
# Check if file exists
Test-Path data/nfl_model.db
```

If `False`, the database may need to be regenerated or restored from backup.

### Predictions Fail with "No data for team X"

**Solution**: Update database with latest data:
```powershell
python src/scripts/update_postgame_scores.py
```

### API Won't Start

**Solution**: Check if port 8000 is in use:
```powershell
netstat -ano | findstr :8000
```

Use alternative port:
```powershell
python -m uvicorn nfl_model.services.api.app:app --app-dir src --port 8001
```

---

## Next Steps

Now that you're set up:

1. **Explore Predictions** → [Prediction Workflows Guide](PREDICTION_WORKFLOWS.md)
2. **Understand the Model** → [Model Architecture](../architecture/MODEL_ARCHITECTURE.md)
3. **View Performance** → [Model Performance Report](../analysis/MODEL_PERFORMANCE.md)
4. **Common Commands** → [Quick Reference](QUICK_REFERENCE.md)

---

## Quick Reference Card

**Generate Predictions**:
```powershell
python src/scripts/predict_upcoming.py --week [WEEK] --playoffs
```

**Train Model**:
```powershell
python src/models/model_v3.py --train-week [WEEK]
```

**Update Scores**:
```powershell
python src/scripts/update_postgame_scores.py
```

**Start API**:
```powershell
python -m uvicorn nfl_model.services.api.app:app --reload --app-dir src
```

---

**Questions?** → See [Troubleshooting Guide](TROUBLESHOOTING.md) or review [docs/README.md](../README.md)
