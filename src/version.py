from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

CLI_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def version_string() -> str:
    sha = _git_sha()
    if sha and sha != "unknown":
        return f"{CLI_VERSION}+{sha}"
    return CLI_VERSION


def version_metadata(ui_version: str | None = None) -> dict[str, str]:
    meta = {
        "cli_version": CLI_VERSION,
        "git_sha": _git_sha(),
    }
    if ui_version:
        meta["ui_version"] = ui_version
    return meta
