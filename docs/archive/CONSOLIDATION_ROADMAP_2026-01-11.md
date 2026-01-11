# Consolidation & Refactor Roadmap (2026-01-11)

## Objectives
- Reduce script sprawl, centralize pipelines, and enforce consistency.
- Prepare a clean, well-documented codebase ready for a simple web client.
- Strengthen data integrity, logging, and repeatability across ingestion and prediction.

## Current State Snapshot
- Data: SQLite at data/nfl_model.db; raw PFR tables (pfr_*), core tables (games, team_games, odds, features), logs (ensemble_predictions*).
- Pipelines: Multiple scripts under src/scripts for fetch/map/import/clean/predict/update; utilities in src/utils; models in src/models.
- Quality: Dedup-aware writes, enforced unique indexes, cleaner and daily pipeline tasks now in place.

## Target Package Structure
- src/nfl_model/
  - ingestion/ — PFR/ESPN/FTE source adapters, mapping, dedup-aware writes.
  - features/ — feature builders, priors (splits/EPA), transformation utilities.
  - models/ — training, prediction interface, ensemble orchestration.
  - pipelines/ — runnable orchestrations (daily sync, backfills, prediction runs).
  - services/api/ — FastAPI app exposing read endpoints and prediction triggers.
  - utils/ — shared helpers (paths, team normalization, db_dedupe, db_logging).

## Refactor Phases
1) Schema & Data Layer
- Define SQLAlchemy models for core entities; centralize DB access helpers.
- Migrations script: ensure unique indexes, idempotent schema checks (already added).
- Document table keys & relationships in reports/PFR_DATA_CATALOG.md.

2) Ingestion Consolidation
- Wrap fetch_pfr_nflscrapy.py and import_pfr_historical.py into nfl_model.ingestion with a uniform interface.
- Keep dedup-aware insert (utils/db_dedupe.py) and ingestion logging (utils/db_logging.py) as shared primitives.
- Provide a single config-driven pipeline runner in pipelines/daily_sync.py (extends existing).

3) Features & Modeling
- Consolidate feature builder to nfl_model/features/feature_builder.py with documented inputs/outputs.
- Standardize model interface Model.predict_game()/Model.train(); unify ensemble logic.
- Persist training metadata (params, MAE) to DB; expose via API.

4) Archival & Deletion
- Move deprecated or one-off scripts to src/scripts/archive and docs to reports/archive.
- Candidates: legacy weather comparison scripts, ad hoc evaluators superseded by pipeline.
- Keep a changelog entry pointing to replacements.

5) Testing & Tooling
- Add unit tests for ingestion (dedup, logging), features, mapping, and prediction.
- Configure pytest, coverage, and pre-commit (black/isort/flake8) for basic hygiene.
- Expand README.md with run guides and API overview.

6) Web API Readiness
- Backend: FastAPI app (services/api/app.py) with endpoints:
  - /games list/filter; /games/{game_id} details; /predictions/{game_id}; /features/{team}/{season}/{week}; /ingestion/logs.
  - /predict trigger with payload (season/week/game selection); /sync-postgame.
- Security: simple API key env for write endpoints initially.
- UI: minimal client (later), or HTMX templates for quick review.

7) Operations
- Tasks: VS Code tasks for migrations, daily sync, API run.
- Scheduler: optional Windows Task Scheduler XML export to run daily pipeline.
- Monitoring: ingestion log summaries written to outputs with timestamps.

## Immediate Actions
- Create nfl_model package scaffolding; move shared utils first.
- Stub FastAPI app with read-only endpoints from DB and a /health check.
- Add pytest and a few smoke tests (dedup insert, schema migration, postgame sync).
- Update requirements.txt with fastapi, uvicorn, sqlalchemy, pydantic (optional now, install later).

## Implementation Notes
- Keep changes surgical: move code with minimal edits; import paths updated via package init.
- Preserve existing scripts for now; add wrappers in pipelines/ and deprecate gradually.
- Maintain idempotency (migrations, cleaner, pipeline) and logging for every write.

## Timeline (Suggested)
- Week 1: Package scaffolding, FastAPI skeleton, core DB models, tests.
- Week 2: Ingestion unification, feature consolidation, ensemble interface.
- Week 3: Archive legacy scripts, expand endpoints, minimal UI, polish docs.
