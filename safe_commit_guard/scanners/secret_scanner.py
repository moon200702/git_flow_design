from __future__ import annotations

import re

from safe_commit_guard.models import Finding
from .common import mask_hash, shannon_entropy


def scan_text_for_secrets(text: str, location: str, policy: dict) -> list[Finding]:
    findings: list[Finding] = []
    patterns = policy.get("secret_patterns", [])
    entropy_threshold = float(policy.get("entropy_threshold", 4.2))
    min_entropy_len = int(policy.get("min_entropy_length", 20))

    for idx, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            for m in re.finditer(pattern, line, flags=re.IGNORECASE):
                token = m.group(0)
                findings.append(
                    Finding(
                        rule_id="secret.regex",
                        severity="critical",
                        message="Possible secret pattern detected",
                        location=f"{location}:{idx}",
                        evidence_hash=mask_hash(token),
                        fix_hint="Move secret to secure vault or environment secret manager",
                    )
                )

        for token in re.findall(r"[A-Za-z0-9_\-/+=]{20,}", line):
            if len(token) >= min_entropy_len and shannon_entropy(token) >= entropy_threshold:
                findings.append(
                    Finding(
                        rule_id="secret.entropy",
                        severity="high",
                        message="High-entropy token detected",
                        location=f"{location}:{idx}",
                        evidence_hash=mask_hash(token),
                        fix_hint="Review if this token should be in source control",
                    )
                )
    return findings
