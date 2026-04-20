from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    location: str
    evidence_hash: str
    fix_hint: str

    def to_dict(self) -> dict:
        return asdict(self)
