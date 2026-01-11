"""
Model Registry - Track and manage saved model versions

This module provides utilities for:
- Registering saved models with metadata
- Retrieving the latest model by version/type
- Comparing model performance
- Managing model lifecycle
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "outputs" / "models"
REGISTRY_FILE = MODELS_DIR / "registry.json"


def load_registry() -> Dict[str, Any]:
    """Load the model registry from disk"""
    if not REGISTRY_FILE.exists():
        return {"models": [], "version": "1.0"}
    
    with open(REGISTRY_FILE, 'r') as f:
        return json.load(f)


def save_registry(registry: Dict[str, Any]) -> None:
    """Save the model registry to disk"""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2, default=str)


def register_model(
    model_path: Path,
    model_type: str,
    features_count: int,
    metadata: Dict[str, Any] = None
) -> str:
    """
    Register a saved model in the registry.
    
    Args:
        model_path: Path to the saved model file
        model_type: Type of model (randomforest, xgboost, etc.)
        features_count: Number of features in the model
        metadata: Optional metadata (metrics, notes, etc.)
        
    Returns:
        Model ID (timestamp-based)
    """
    registry = load_registry()
    
    # Generate model ID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_id = f"{model_type}_{timestamp}"
    
    # Create registry entry
    entry = {
        "model_id": model_id,
        "path": str(model_path.relative_to(PROJECT_ROOT)),
        "model_type": model_type,
        "features_count": features_count,
        "registered_at": datetime.now().isoformat(),
        "metadata": metadata or {},
    }
    
    # Add to registry
    registry["models"].append(entry)
    
    # Save
    save_registry(registry)
    
    print(f"[REGISTERED] Model: {model_id}")
    
    return model_id


def get_latest_model(
    model_type: Optional[str] = None,
    version: str = "v3"
) -> Optional[Path]:
    """
    Get the path to the most recently saved model.
    
    Args:
        model_type: Filter by model type (e.g., 'randomforest'). None = any type.
        version: Model version (default: 'v3')
        
    Returns:
        Path to latest model file, or None if no models found
    """
    registry = load_registry()
    
    # Filter models
    models = registry.get("models", [])
    
    if model_type:
        models = [m for m in models if m["model_type"] == model_type]
    
    if not models:
        return None
    
    # Sort by registration time (most recent first)
    models.sort(key=lambda m: m["registered_at"], reverse=True)
    
    # Get latest
    latest = models[0]
    model_path = PROJECT_ROOT / latest["path"]
    
    if model_path.exists():
        return model_path
    else:
        print(f"[WARN] Registered model not found: {model_path}")
        return None


def list_models(
    model_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    List registered models with their metadata.
    
    Args:
        model_type: Filter by model type
        limit: Maximum number of models to return
        
    Returns:
        List of model entries (most recent first)
    """
    registry = load_registry()
    models = registry.get("models", [])
    
    # Filter
    if model_type:
        models = [m for m in models if m["model_type"] == model_type]
    
    # Sort by registration time (most recent first)
    models.sort(key=lambda m: m["registered_at"], reverse=True)
    
    return models[:limit]


def get_model_info(model_path: Path) -> Optional[Dict[str, Any]]:
    """
    Get registry information for a specific model.
    
    Args:
        model_path: Path to model file
        
    Returns:
        Model registry entry, or None if not found
    """
    registry = load_registry()
    models = registry.get("models", [])
    
    relative_path = str(model_path.relative_to(PROJECT_ROOT))
    
    for model in models:
        if model["path"] == relative_path:
            return model
    
    return None


def delete_model(model_id: str, remove_file: bool = False) -> bool:
    """
    Remove a model from the registry.
    
    Args:
        model_id: ID of model to remove
        remove_file: If True, also delete the model file from disk
        
    Returns:
        True if model was removed, False if not found
    """
    registry = load_registry()
    models = registry.get("models", [])
    
    # Find model
    for i, model in enumerate(models):
        if model["model_id"] == model_id:
            # Remove from registry
            removed = models.pop(i)
            save_registry(registry)
            
            # Optionally delete file
            if remove_file:
                model_path = PROJECT_ROOT / removed["path"]
                if model_path.exists():
                    model_path.unlink()
                    print(f"[CLEANUP] Deleted model file: {model_path}")
            
            print(f"[REMOVED] Model removed from registry: {model_id}")
            return True
    
    print(f"[WARN] Model not found in registry: {model_id}")
    return False


def cleanup_old_models(keep_recent: int = 5, model_type: Optional[str] = None) -> int:
    """
    Remove old models from registry and optionally disk, keeping only N most recent.
    
    Args:
        keep_recent: Number of recent models to keep per type
        model_type: Only cleanup this model type (None = all types)
        
    Returns:
        Number of models removed
    """
    registry = load_registry()
    models = registry.get("models", [])
    
    # Group by model type
    by_type: Dict[str, List] = {}
    for model in models:
        mtype = model["model_type"]
        if model_type and mtype != model_type:
            continue
        if mtype not in by_type:
            by_type[mtype] = []
        by_type[mtype].append(model)
    
    # Remove old models
    removed_count = 0
    new_models = []
    
    for mtype, mlist in by_type.items():
        # Sort by date (newest first)
        mlist.sort(key=lambda m: m["registered_at"], reverse=True)
        
        # Keep recent, mark rest for removal
        keep = mlist[:keep_recent]
        remove = mlist[keep_recent:]
        
        new_models.extend(keep)
        removed_count += len(remove)
        
        # Delete files
        for model in remove:
            model_path = PROJECT_ROOT / model["path"]
            if model_path.exists():
                model_path.unlink()
                print(f"[CLEANUP] Deleted old model: {model_path.name}")
    
    # Update registry
    registry["models"] = new_models
    save_registry(registry)
    
    if removed_count > 0:
        print(f"[CLEANUP] Removed {removed_count} old models")
    
    return removed_count


if __name__ == "__main__":
    # Example usage
    print("Model Registry Status")
    print("=" * 60)
    
    models = list_models(limit=20)
    
    if not models:
        print("No models registered yet.")
    else:
        print(f"\nFound {len(models)} registered models:\n")
        for m in models:
            print(f"  {m['model_id']}")
            print(f"    Type: {m['model_type']}")
            print(f"    Features: {m['features_count']}")
            print(f"    Registered: {m['registered_at']}")
            print(f"    Path: {m['path']}")
            print()
    
    # Show latest model
    latest = get_latest_model()
    if latest:
        print(f"\nLatest model: {latest.name}")
