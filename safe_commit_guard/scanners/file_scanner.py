from __future__ import annotations

from pathlib import Path

from safe_commit_guard.models import Finding
from .common import mask_hash


def scan_risky_files(paths: list[str], policy: dict) -> list[Finding]:
    findings: list[Finding] = []
    risky_ext = set(policy.get("risky_extensions", []))
    risky_names = set(policy.get("risky_filenames", []))

    for path in paths:
        p = Path(path)
        by_name = p.name in risky_names
        by_suffix = p.suffix in risky_ext
        by_path_end = any(path.endswith(ext) for ext in risky_ext)

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
