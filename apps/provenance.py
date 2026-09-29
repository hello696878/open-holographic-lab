"""Bounded, read-only Git detection for the checkout supplying imported ohlab."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess

import ohlab


def detect_source_revision() -> dict[str, str | None]:
    """Return current imported-package provenance, or explicit unavailable data.

    Each call detects afresh. The caller's working directory and saved bundle
    metadata are never used as evidence of the executing source. Each of the
    four read-only Git commands has a ten-second timeout; optional locks are
    disabled. No package installation or Git repair is attempted.
    """
    unavailable = {"revision": None, "state": "unavailable", "method": "git"}
    if ohlab.__file__ is None:
        return unavailable

    def git(directory: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments], check=True,
            capture_output=True, text=True, encoding="utf-8", timeout=10,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        return result.stdout.strip()

    try:
        package = Path(ohlab.__file__).resolve().parent
        checkout = Path(git(package, "rev-parse", "--show-toplevel")).resolve()
        if package != (checkout / "src" / "ohlab").resolve():
            return unavailable
        tracked = git(checkout, "ls-files", "--error-unmatch", "--", "src/ohlab/__init__.py")
        if tracked != "src/ohlab/__init__.py":
            return unavailable
        revision = git(checkout, "rev-parse", "--verify", "HEAD")
        if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
            return unavailable
        status = git(checkout, "status", "--porcelain=v1", "--untracked-files=normal")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, UnicodeError):
        return unavailable
    return {"revision": revision, "state": "dirty" if status else "clean", "method": "git"}
