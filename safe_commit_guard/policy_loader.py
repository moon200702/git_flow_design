from __future__ import annotations

import json
from pathlib import Path


DEFAULT_POLICY_FILE = Path(__file__).resolve().parent / "policy" / "rules.json"


def load_policy(policy_file: str | None = None) -> dict:
    source = Path(policy_file) if policy_file else DEFAULT_POLICY_FILE
    with source.open("r", encoding="utf-8") as fp:
        return json.load(fp)
