# NFL Model Architecture

## Active Models

**model_v3.py** - Current production model
- RandomForest with momentum features (EMA, trend, volatility)
- Expanded data sources (points_for, points_against)
- Fixed feature storage bug from v2
- ~300+ engineered features

## Model Versioning Policy

### For Future AI Assistants / Contributors

When creating a new model version (v4, v5, etc.):

1. **Archive old versions** - Move superseded models to `archive/` subdirectory
   - Keep only the current production model in the main `models/` directory
   - Example: When creating v4, move v3 to `archive/model_v3.py`

2. **Update this README** - Document what changed in the new version

3. **Naming convention**: `model_vN.py` where N is the version number

### Why Archive?

- **Reduce clutter** - Main directory shows only active code
- **Preserve history** - Archive maintains development evolution
- **Avoid confusion** - Clear which model is production-ready

### Archive Location

`src/models/archive/` contains deprecated model versions:
- `model_v0.py` - Baseline (Ridge regression, basic rolling features)
- `model_v1.py` - Added non-linear models (XGBoost, LightGBM, RandomForest)
- `model_v2.py` - Added momentum features (had feature storage bug)

## Model Evolution Summary

| Version | Key Changes | Status |
|---------|-------------|--------|
| v0 | Ridge regression baseline, rolling averages | Archived |
| v1 | Non-linear models (XGBoost, LightGBM, RF) | Archived |
| v2 | Momentum features (EMA, trend, volatility) | Archived |
| v3 | Fixed momentum bug + expanded features | **ACTIVE** |

## Running the Active Model

```bash
# Train the model
python src/models/model_v3.py --model randomforest --train-week 14

# Make predictions (when implemented)
python src/models/model_v3.py --away CHI --home GNB --week 18
```

## Development Guidelines

- Always compare new model performance against active version
- Document performance improvements in this README
- Archive immediately when a new version becomes production-ready
- Keep test scripts up to date
