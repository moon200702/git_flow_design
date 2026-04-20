from __future__ import annotations

import re

from safe_commit_guard.models import Finding
from .common import added_lines_from_patch, mask_hash


BASE64_RE = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")


def scan_patch_anomalies(patch: str, location: str, policy: dict) -> list[Finding]:
    findings: list[Finding] = []
    lines = added_lines_from_patch(patch)

    max_added_lines = int(policy.get("max_added_lines", 800))
    if len(lines) > max_added_lines:
        findings.append(
            Finding(
                rule_id="diff.too_large",
                severity="high",
                message=f"Large patch detected ({len(lines)} added lines)",
                location=location,
                evidence_hash=mask_hash(str(len(lines))),
                fix_hint="Split commit into smaller reviewable chunks",
            )
        )

    for idx, line in enumerate(lines, start=1):
        if BASE64_RE.search(line):
            findings.append(
                Finding(
                    rule_id="diff.base64_blob",
                    severity="high",
                    message="Long base64-like string detected in added line",
                    location=f"{location}:added#{idx}",
                    evidence_hash=mask_hash(line[:120]),
                    fix_hint="Remove embedded secret/blob and use secure artifact storage",
                )
            )
    return findings
