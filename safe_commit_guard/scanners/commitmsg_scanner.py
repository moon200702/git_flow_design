from __future__ import annotations

import re

from safe_commit_guard.models import Finding
from .common import mask_hash


def scan_commit_message(message: str, policy: dict) -> list[Finding]:
    findings: list[Finding] = []
    patterns = policy.get("commit_message_patterns", [])
    for pattern in patterns:
        for m in re.finditer(pattern, message, flags=re.IGNORECASE):
            token = m.group(0)
            findings.append(
                Finding(
                    rule_id="commitmsg.sensitive",
                    severity="critical",
                    message="Sensitive data pattern in commit message",
                    location="commit-message",
                    evidence_hash=mask_hash(token),
                    fix_hint="Rewrite commit message and remove sensitive details",
                )
            )
    return findings
