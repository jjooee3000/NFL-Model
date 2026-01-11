import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

import subprocess
import datetime

# Simulate what the API does
script = ROOT / "src" / "scripts" / "predict_ensemble_multiwindow.py"
python_exe = ROOT / ".venv" / "Scripts" / "python.exe"
cmd = [
    str(python_exe), str(script),
    "--sync-postgame",
    "--season", "2026",
    "--week", "18",
    "--train-windows", "18",
    "--variants", "default",
    "--games", "SF@PHI"
]

print("Running command:", " ".join(cmd))
print("Timeout: 180 seconds")
print()

try:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
    print(f"Return code: {proc.returncode}")
    print(f"STDOUT length: {len(proc.stdout)}")
    print(f"STDERR length: {len(proc.stderr)}")
    print()
    print("Last 500 chars of STDOUT:")
    print(proc.stdout[-500:])
    print()
    print("Last 500 chars of STDERR:")
    print(proc.stderr[-500:])
except subprocess.TimeoutExpired as e:
    print(f"TIMEOUT ERROR: Command timed out after 180 seconds")
except Exception as e:
    print(f"ERROR: {e}")
