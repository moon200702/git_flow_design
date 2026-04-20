from __future__ import annotations

import json
from collections import Counter

from safe_commit_guard.models import Finding


def summarize(findings: list[Finding]) -> dict:
    counts = Counter(f.severity for f in findings)
    return {
        "total": len(findings),
        "by_severity": dict(counts),
    }


def format_text(findings: list[Finding]) -> str:
    if not findings:
        return "SCG: no findings"
    lines = ["SCG findings:"]
    for finding in findings:
        lines.append(
            f"- [{finding.severity}] {finding.rule_id} at {finding.location}: "
            f"{finding.message} (hint: {finding.fix_hint})"
        )
    lines.append(f"Summary: {summarize(findings)}")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    return json.dumps(
        {
            "findings": [f.to_dict() for f in findings],
            "summary": summarize(findings),
        },
        ensure_ascii=False,
        indent=2,
    )
