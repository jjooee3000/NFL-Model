"""Compare and inspect saved models from the registry.

Usage examples:
    # Show latest 5 randomforest models
    & ".venv/Scripts/python.exe" src/scripts/compare_models.py --model-type randomforest --limit 5

    # Show all models (any type)
    & ".venv/Scripts/python.exe" src/scripts/compare_models.py --model-type any --limit 20

    # Clean up, keep last 3 per type
    & ".venv/Scripts/python.exe" src/scripts/compare_models.py --cleanup 3
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
import sys
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.model_registry import (
    list_models,
    get_latest_model,
    cleanup_old_models,
    load_registry,
)


def format_row(entry: Dict[str, Any]) -> str:
    """Format a single registry entry for console output."""
    meta = entry.get("metadata", {}) or {}
    mae = meta.get("mae") or meta.get("margin_MAE")
    train_week = meta.get("train_week")
    variant = meta.get("variant")
    return (
        f"{entry.get('model_id','?'):20} | "
        f"{entry.get('model_type','?'):12} | "
        f"{entry.get('features_count','?'):4} feats | "
        f"train_wk={train_week if train_week is not None else '?':>2} | "
        f"mae={mae if mae is not None else '?':>5} | "
        f"variant={variant if variant else '-':8} | "
        f"path={entry.get('path','?')}"
    )


def show_models(model_type: str, limit: int) -> None:
    models = list_models(model_type=None if model_type == "any" else model_type, limit=limit)
    if not models:
        print("No models found in registry.")
        return
    print(f"Found {len(models)} model(s):")
    for entry in models:
        print("  " + format_row(entry))


def main():
    parser = argparse.ArgumentParser(description="Compare saved models from registry")
    parser.add_argument(
        "--model-type",
        default="randomforest",
        help="Filter by model type (randomforest, xgboost, etc.) or 'any'"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of models to display"
    )
    parser.add_argument(
        "--show-latest",
        action="store_true",
        help="Print the latest model path"
    )
    parser.add_argument(
        "--cleanup",
        type=int,
        default=0,
        help="If >0, keep only this many most recent models per type (deletes older)"
    )

    args = parser.parse_args()

    # Display models
    show_models(args.model_type, args.limit)

    # Show latest
    if args.show_latest:
        latest = get_latest_model(None if args.model_type == "any" else args.model_type)
        if latest:
            print(f"\nLatest model: {latest}")
        else:
            print("\nNo latest model found.")

    # Cleanup
    if args.cleanup > 0:
        removed = cleanup_old_models(keep_recent=args.cleanup, model_type=None if args.model_type == "any" else args.model_type)
        print(f"\nCleanup removed {removed} model(s)")


if __name__ == "__main__":
    main()
