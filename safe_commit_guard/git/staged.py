from __future__ import annotations

from .context import run_git


def staged_files() -> list[str]:
    out = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def staged_patch() -> str:
    return run_git(["diff", "--cached", "-U0", "--no-color"])


def staged_file_content(path: str) -> str:
    return run_git(["show", f":{path}"])
