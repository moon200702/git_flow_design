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
        if p.suffix in risky_ext or p.name in risky_names:
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
