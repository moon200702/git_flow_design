from __future__ import annotations

from pathlib import Path

from safe_commit_guard.models import Finding
from .common import mask_hash


def scan_risky_files(paths: list[str], policy: dict) -> list[Finding]:
    """Detect risky file names/extensions from staged paths.

    Notes:
    - Handles dotfiles like `.env` that do not have a conventional suffix.
    - Matching is case-insensitive for better cross-platform consistency.
    """

    findings: list[Finding] = []
    risky_ext = {item.lower() for item in policy.get("risky_extensions", [])}
    risky_names = {item.lower() for item in policy.get("risky_filenames", [])}

    for path in paths:
        p = Path(path)
        path_l = path.lower()
        name_l = p.name.lower()
        suffix_l = p.suffix.lower()

        by_name = name_l in risky_names
        by_suffix = suffix_l in risky_ext
        by_path_end = any(path_l.endswith(ext) for ext in risky_ext)

        if by_name or by_suffix or by_path_end:
            findings.append(
                Finding(
                    rule_id="file.risky",
                    severity="critical",
                    message="Risky file type/name staged",
                    location=path,
                    evidence_hash=mask_hash(path),
                    fix_hint="Unstage this file or add safe redacted version",
                )
            )

    return findings
