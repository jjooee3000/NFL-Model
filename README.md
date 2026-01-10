````markdown
# NFL Model Workspace

Models v0–v3, analysis scripts, and reports are grouped under `src/`, `data/`, `outputs/`, and `reports/` for easier navigation.

## Layout
- Data: [data](data) (place `nfl_2025_model_data_with_moneylines.xlsx` here)
- Models: [src/models](src/models) ([model_v0.py](src/models/model_v0.py), [model_v1.py](src/models/model_v1.py), [model_v2.py](src/models/model_v2.py), [model_v3.py](src/models/model_v3.py))
- Scripts: [src/scripts](src/scripts) ([compare_all_versions.py](src/scripts/compare_all_versions.py), [analyze_features.py](src/scripts/analyze_features.py), [analyze_v3_features.py](src/scripts/analyze_v3_features.py), [run_ensemble_oneoff.py](src/scripts/run_ensemble_oneoff.py), [debug_momentum.py](src/scripts/debug_momentum.py), [check_features.py](src/scripts/check_features.py), [inspect_odds_feed.py](src/scripts/inspect_odds_feed.py))
- Utilities: [src/utils](src/utils) ([paths.py](src/utils/paths.py))
- Reports: [reports](reports)
- Outputs (generated): [outputs](outputs)

## Setup
```bash
pip install -r requirements.txt
```

Ensure the workbook is available at [data/nfl_2025_model_data_with_moneylines.xlsx](data/nfl_2025_model_data_with_moneylines.xlsx).

## Common Tasks

Run commands from the repository root. Scripts add `src/` to `PYTHONPATH` automatically, so direct invocation works:

1. Compare all model versions (v0–v3):
```bash
python src/scripts/compare_all_versions.py
```

2. Feature importance (v2 baseline):
```bash
python src/scripts/analyze_features.py
```

3. Feature importance (v3 with momentum):
```bash
python src/scripts/analyze_v3_features.py
```

4. One-off ensemble prediction (edit HOME/AWAY/API key inside the script or pass via env):
```bash
python src/scripts/run_ensemble_oneoff.py
```

5. Train and predict with a specific model (example v3):
```bash
python -m src.models.model_v3 --model randomforest --train-week 14
```

Generated outputs land in [outputs](outputs) (e.g., feature importance CSVs and plots).
````
