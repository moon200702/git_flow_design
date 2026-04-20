from __future__ import annotations

from .context import run_git


def rev_list_range(local_sha: str, remote_sha: str) -> list[str]:
    if remote_sha == "0" * 40:
        rev = local_sha
    else:
        rev = f"{remote_sha}..{local_sha}"
    out = run_git(["rev-list", rev])
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_message(commit_sha: str) -> str:
    return run_git(["show", "-s", "--format=%B", commit_sha])


def commit_patch(commit_sha: str) -> str:
    return run_git(["show", "--format=", "--no-color", "-U0", commit_sha])
