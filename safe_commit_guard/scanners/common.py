from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


def mask_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def added_lines_from_patch(patch: str) -> list[str]:
    lines: list[str] = []
    for line in patch.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return lines


def regex_hits(patterns: list[str], text: str) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append(match.group(0))
    return hits
