\
# NFL 2025 v0 Hybrid Model (CLI)

This package contains a single script, `model_v0.py`, which:
- trains a v0 baseline model on the 2025 regular season (from your Excel workbook), and
- predicts spread/total/win probabilities for a single matchup using closing market inputs.

## Prerequisites

Python 3.10+ recommended.

Install dependencies:
```bash
pip install -r requirements.txt
```

## Files you need

Place your workbook in the same folder (or pass an absolute path):
- `nfl_2025_model_data_with_moneylines.xlsx`

## Usage

### Fit + predict (default)
```bash
python model_v0.py \
  --workbook nfl_2025_model_data_with_moneylines.xlsx \
  --home CHI --away GNB \
  --close_spread_home 1.5 \
  --close_total 44.5 \
  --close_ml_home 105 \
  --close_ml_away -125
```

### Fit once and save artifacts
```bash
python model_v0.py \
  --workbook nfl_2025_model_data_with_moneylines.xlsx \
  --home CHI --away GNB \
  --close_spread_home 1.5 \
  --close_total 44.5 \
  --close_ml_home 105 \
  --close_ml_away -125 \
  --save_model artifacts.joblib
```

### Load artifacts and predict (no refit)
```bash
python model_v0.py \
  --workbook nfl_2025_model_data_with_moneylines.xlsx \
  --home CHI --away GNB \
  --close_spread_home 1.5 \
  --close_total 44.5 \
  --close_ml_home 105 \
  --close_ml_away -125 \
  --load_model artifacts.joblib
```

### JSON output
Add `--json` to any command.
