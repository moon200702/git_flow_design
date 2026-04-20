from __future__ import annotations

import subprocess
from pathlib import Path


class GitCommandError(RuntimeError):
    pass


def run_git(args: list[str], cwd: str | None = None) -> str:
    cmd = ["git", *args]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitCommandError(proc.stderr.strip() or f"git command failed: {' '.join(cmd)}")
    return proc.stdout


def git_dir() -> Path:
    return Path(run_git(["rev-parse", "--git-dir"]).strip())


def repo_root() -> Path:
    return Path(run_git(["rev-parse", "--show-toplevel"]).strip())
