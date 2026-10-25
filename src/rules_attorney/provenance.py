"""Where a run came from: the commit its code and data were at."""

import subprocess
from pathlib import Path
from typing import Any


def commit(root: Path) -> dict[str, Any]:
    """The repo's HEAD commit, and whether the tree differs from it."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
    )
    return {"commit": head.stdout.strip(), "dirty": bool(status.stdout)}
