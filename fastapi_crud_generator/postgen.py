from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path


def _run(cmd: Sequence[str], cwd: Path) -> int:
    proc = subprocess.run(cmd, check=False, cwd=str(cwd))
    return proc.returncode


def run_ruff_fix(project_root: Path, *, strict: bool = False, use_uv: bool = True) -> None:
    """
    Run Ruff auto-fix for the repository, preferring 'uv run'.
    Raises CalledProcessError on failure if strict=True.
    """
    if use_uv and shutil.which("uv"):
        cmd = ["uv", "run", "ruff", "check", "--fix", "."]
    else:
        cmd = ["ruff", "check", "--fix", "."]
    code = _run(cmd, cwd=project_root)
    if strict and code != 0:
        raise subprocess.CalledProcessError(code, cmd)
