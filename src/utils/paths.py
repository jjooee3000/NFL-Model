"""Common path helpers for project-level references."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"


def add_src_to_sys_path() -> None:
    """Ensure the src directory is available for imports when running scripts directly."""
    path_str = str(SRC_DIR)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def ensure_dir(path: Path) -> None:
    """Create directory if missing."""
    path.mkdir(parents=True, exist_ok=True)


__all__ = [
    "ROOT",
    "SRC_DIR",
    "DATA_DIR",
    "OUTPUTS_DIR",
    "REPORTS_DIR",
    "add_src_to_sys_path",
    "ensure_dir",
]
