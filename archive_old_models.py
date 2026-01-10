"""Archive old model versions to src/models/archive/"""
import os
import shutil
from pathlib import Path

# Define paths
project_root = Path(__file__).parent
models_dir = project_root / "src" / "models"
archive_dir = models_dir / "archive"

# Create archive directory
archive_dir.mkdir(exist_ok=True)
print(f"Created archive directory: {archive_dir}")

# Move old model versions
old_models = ["model_v0.py", "model_v1.py", "model_v2.py"]

for model_file in old_models:
    src = models_dir / model_file
    dst = archive_dir / model_file
    
    if src.exists():
        shutil.move(str(src), str(dst))
        print(f"Moved {model_file} to archive/")
    else:
        print(f"Skipped {model_file} (not found)")

print("\nArchiving complete!")
print(f"\nActive model: {models_dir / 'model_v3.py'}")
print(f"Archived models: {list(archive_dir.glob('model_v*.py'))}")
