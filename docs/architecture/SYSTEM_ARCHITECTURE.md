# NFL Model - System Architecture

**Last Updated**: 2026-01-11  
**Version**: 3.0 (SQLite-based)  
**Status**: Production

---

## Overview

The NFL Prediction Model is a machine learning system that predicts NFL game outcomes (margin and total points) using historical team performance data, betting market data, and weather conditions.

```
┌─────────────────────────────────────────────────────────────────┐
│                    NFL PREDICTION SYSTEM                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Data        │      │  Feature     │      │  Model       │
│  Sources     │ ───▶ │  Engineering │ ───▶ │  Training    │
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
     │                                             │
     │                                             │
     ▼                                             ▼
┌──────────────┐                         ┌──────────────┐
│  SQLite DB   │                         │  Predictions │
│  (Primary    │ ◀────────────────────── │  Output      │
│   Storage)   │                         │              │
└──────────────┘                         └──────────────┘
```

---

## Core Components

### 1. Data Layer

**Primary Storage**: SQLite Database (`data/nfl_model.db`)

**Tables**:
- `games` - Game results and metadata (2,474 games, 2020-2025)
- `team_games` - Team-level stats per game (~4,948 rows)
- `odds` - Betting lines and market data
- `ensemble_predictions` - Model predictions
- `ingestion_log` - Data import tracking

**Data Sources**:
- **ESPN API** - Live scores, schedules, basic stats
- **Pro Football Reference** - Advanced stats, historical data
- **Weather APIs** - Game-day weather conditions
- **Betting Feeds** - Opening/closing lines, moneylines

### 2. Feature Engineering

**Feature Builder**: `src/utils/feature_builder.py`

**Feature Types** (275 total):

1. **Base Features** (38):
   - Team performance: `points_for`, `points_against`
   - Efficiency: `yards_per_play`, `rush_ypa`
   - Defense: `sacks_made`, `turnovers_take`
   - Weather: `temp_f`, `wind_mph`, `precip_inch`

2. **Rolling Window Features** (6 variants each):
   - `_pre8`: 8-game rolling average
   - `_ema8`: Exponential moving average
   - `_trend8`: Linear trend
   - `_vol8`: Volatility (std dev)
   - `_season_avg`: Season cumulative average
   - `_recent_ratio`: Recent / Season average

3. **Phase 1 Interactions** (11 categories):
   - Pressure differential
   - Turnover impact
   - Scoring efficiency
   - Consistency metrics
   - Form indicators

4. **Delta Features**:
   - Home team feature - Away team feature
   - Captures matchup differentials

### 3. Model Layer

**Production Model**: `src/models/model_v3.py`

**Algorithm**: RandomForest Regressor
- **Trees**: 100
- **Max Depth**: 12
- **Min Samples Split**: 5
- **Features**: 275

**Dual Model Approach**:
- **Margin Model**: Predicts home team margin (home_score - away_score)
- **Total Model**: Predicts total points (home_score + away_score)

**Training**:
- Time series split (by week)
- Train through week N, predict week N+1
- No data leakage

**Alternative Models**:
- **XGBoost**: Available but RandomForest performs better
- **v4 Experimental**: Testing new architectures

### 4. Prediction Layer

**Prediction Scripts**:

1. **Simple Prediction**: `src/scripts/predict_upcoming.py`
   - Single model training
   - Fast execution (~5 seconds)
   - Good for quick predictions

2. **Ensemble Multi-Window**: `src/scripts/predict_ensemble_multiwindow.py`
   - 15 models (5 training windows × 3 variants)
   - Median aggregation
   - Best accuracy (~7-8 minutes)

**Prediction Output**:
```python
{
    "game_id": "2025_01_SF_PHI",
    "pred_margin_home": 1.45,     # PHI favored by 1.45
    "pred_total": 45.7,            # Total points
    "pred_winprob_home": 0.54      # 54% home win chance
}
```

### 5. API Layer

**Framework**: FastAPI  
**File**: `src/nfl_model/services/api/app.py`

**Endpoints**:
- `GET /health` - Health check
- `GET /games` - List games (filter by season/week)
- `GET /predictions/{game_id}` - Get prediction
- `POST /predict` - Trigger prediction run

**Features**:
- Auto-generated OpenAPI docs (`/docs`)
- JSON responses
- CORS enabled
- Async support

### 6. Data Pipeline

**Daily Sync**: `src/scripts/pipeline_daily_sync.py`

**Workflow**:
```
1. Update postgame scores (ESPN API)
   ↓
2. Optional: Fetch new PFR data
   ↓
3. Optional: Map/integrate PFR data
   ↓
4. Clean database (deduplication)
   ↓
5. Log operations
```

**Scheduling**: Can be automated via cron/Task Scheduler

---

## Data Flow

### Training Flow

```
1. Load data from SQLite
   ↓
2. Filter games (train through week N)
   ↓
3. Build features (rolling, momentum, interactions)
   ↓
4. Create delta features (home - away)
   ↓
5. Add market features (odds, line movement)
   ↓
6. Train RandomForest (margin + total models)
   ↓
7. Validate on test set (week N+1 onwards)
   ↓
8. Save model artifacts
```

### Prediction Flow

```
1. Load saved model artifacts
   ↓
2. Get target game (away_team, home_team, week)
   ↓
3. Fetch latest team stats (up to target week - 1)
   ↓
4. Build features for both teams
   ↓
5. Calculate deltas (home - away)
   ↓
6. Add market features (if available)
   ↓
7. Predict margin and total
   ↓
8. Calculate win probability
   ↓
9. Save to database and CSV
```

---

## Storage Architecture

### Database Schema (SQLite)

**games** table:
```sql
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    season INTEGER,
    week REAL,
    gameday TEXT,
    home_team TEXT,
    away_team TEXT,
    home_score REAL,
    away_score REAL,
    neutral_site_0_1 INTEGER,
    venue TEXT,
    -- Weather fields
    temp_f REAL,
    wind_mph REAL,
    precip_inch REAL,
    -- 30+ total columns
);
```

**team_games** table:
```sql
CREATE TABLE team_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT,
    team TEXT,
    is_home_0_1 INTEGER,
    points_for REAL,
    points_against REAL,
    yards_per_play REAL,
    -- 56+ team stat columns
);
```

**Size**: ~25 MB for 2,474 games

### File Storage

- **Models**: Serialized via `joblib` (not persisted, retrained on demand)
- **Predictions**: CSV files in `outputs/`
- **Logs**: Text-based in `outputs/`

---

## Performance Characteristics

### Training Performance
- **Time**: ~5-6 seconds (single model, 2,474 games)
- **Memory**: ~200 MB peak
- **CPU**: Utilizes all cores (`n_jobs=-1`)

### Prediction Performance
- **Single Game**: <1 second
- **10 Games (Simple)**: ~5 seconds
- **10 Games (Ensemble)**: ~7-8 minutes

### Model Accuracy
- **Margin MAE**: 7.02 pts (train through week 18)
- **Total MAE**: ~7.5 pts
- **Winner Accuracy**: 60-67% (varies by sample)

### Baseline Comparison
- **Vegas Consensus**: ~11 pts MAE
- **Our Model**: ~4 pts better than Vegas

---

## Scalability Considerations

### Current Limitations
1. **Single-threaded prediction** - Ensemble runs sequentially
2. **In-memory processing** - Full dataset loaded
3. **No caching** - Features recalculated each run

### Scaling Strategies (Future)
1. **Parallel ensemble** - Use multiprocessing
2. **Feature caching** - Pre-compute rolling features
3. **Incremental updates** - Only recompute changed games
4. **Distributed training** - Dask/Ray for large datasets

---

## Security & Data Integrity

### Data Integrity
- **Unique indexes** - Prevent duplicates
- **Deduplication** - Pre-insert checks (`db_dedupe.py`)
- **Logging** - All ingestion operations logged
- **Validation** - Schema constraints enforced

### API Security
- **No authentication** (local use only)
- **CORS**: Configurable
- **Input validation**: Pydantic models

### Backup Strategy
- **Database**: Manual backups recommended
- **Excel**: Parallel Excel files maintained
- **Version control**: `.gitignore` excludes large data

---

## Technology Stack

### Core
- **Python**: 3.9+
- **SQLite**: 3.x (built-in)
- **Pandas**: Data manipulation
- **NumPy**: Numerical operations

### Machine Learning
- **scikit-learn**: RandomForest, preprocessing
- **XGBoost**: Gradient boosting (available)

### Web/API
- **FastAPI**: REST API framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Data Fetching
- **requests**: HTTP client
- **beautifulsoup4**: HTML parsing
- **openpyxl**: Excel file handling

---

## Deployment Architecture

### Current (Local Development)

```
Developer Machine
├── Python 3.9 venv
├── SQLite database
├── VS Code
└── PowerShell terminal
```

### Potential Production

```
┌─────────────────┐
│  Web Server     │
│  (FastAPI)      │
│  Port 8000      │
└────────┬────────┘
         │
┌────────▼────────┐
│  Application    │
│  (Model + DB)   │
└────────┬────────┘
         │
┌────────▼────────┐
│  SQLite DB      │
│  (Read/Write)   │
└─────────────────┘
```

**Deployment Options**:
1. **Cloud VM**: AWS EC2, Azure VM, GCP Compute
2. **Containerized**: Docker + Docker Compose
3. **Serverless**: AWS Lambda (with scheduled retraining)

---

## Monitoring & Observability

### Current Monitoring
- **Manual**: Check logs and output files
- **API**: Health endpoint for status

### Recommended (Future)
- **Application logs**: Structured logging (JSON)
- **Performance metrics**: Prediction latency, accuracy
- **Alerts**: Model drift, data quality issues
- **Dashboards**: Grafana for visualization

---

## Related Documentation

- **[Database Schema](DATABASE_SCHEMA.md)** - Detailed schema reference
- **[Model Architecture](MODEL_ARCHITECTURE.md)** - Model design deep dive
- **[Data Pipeline](DATA_PIPELINE.md)** - Pipeline workflows
- **[API Documentation](../guides/API_GUIDE.md)** - API reference

---

**Last Updated**: 2026-01-11  
**Version**: 3.0 (SQLite-based)  
**Maintained By**: NFL Model Development Team
