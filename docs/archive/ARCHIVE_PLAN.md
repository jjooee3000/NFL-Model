# Archive Plan

## Purpose
Collect older, ad-hoc, or superseded scripts/docs into archive folders to reduce clutter while preserving history.

## Directories
- src/scripts/archive/: archived Python scripts
- reports/archive/: archived docs, notes, and one-offs

## Candidate Files
- display_jan12_predictions.py — superseded by API and prediction pipeline
- archive_old_models.bat / archive_old_models.py — replaced by DB-first logging and cleaner
- Ad-hoc analysis scripts under src/scripts/analysis/ (if any) — replace with pipelines and notebooks

## Process
1. Move file into appropriate archive folder.
2. Add a short note at top linking to the modern replacement.
3. Update README and tasks to point to new pipeline/API.

## Replacement References
- Predictions: src/scripts/predict_ensemble_multiwindow.py and API `/predict`
- Daily hygiene: src/scripts/pipeline_daily_sync.py and cleaner
- Ingestion: src/scripts/fetch_pfr_nflscrapy.py and import_pfr_historical.py under ingestion module
