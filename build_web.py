import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "web_build"

if (APP_DIR / "build").exists():
    shutil.rmtree(APP_DIR / "build")
APP_DIR.mkdir(exist_ok=True)

for filename in ("main.py", "artillery_calculation.py", "favicon.png"):
    shutil.copy2(ROOT / filename, APP_DIR / filename)

subprocess.run(
    [
        sys.executable,
        "-m",
        "pygbag",
        "--build",
        "--title",
        "Artillery Calculation",
        "main.py",
    ],
    cwd=APP_DIR,
    check=True,
)
