"""Run the TypeScript catalog exporter with the repository's pinned tsx binary."""

from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TSX = PROJECT_ROOT / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform == "win32" else "tsx")


def export_catalog() -> None:
    if not TSX.exists():
        raise RuntimeError("tsx is not installed; run 'npm install' first")
    subprocess.run(
        [str(TSX), str(PROJECT_ROOT / "scripts" / "export_catalog.ts")],
        cwd=PROJECT_ROOT,
        check=True,
    )


if __name__ == "__main__":
    export_catalog()
