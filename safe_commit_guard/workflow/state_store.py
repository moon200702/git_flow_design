from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from safe_commit_guard.git.context import git_dir


def scg_dir() -> Path:
    path = git_dir() / "scg"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_gate(ttl_seconds: int, risk_summary: dict, staged_fingerprint: str) -> str:
    gate_id = uuid.uuid4().hex[:12]
    now = int(time.time())
    payload = {
        "gate_id": gate_id,
        "created_at": now,
        "expires_at": now + ttl_seconds,
        "status": "pending",
        "risk_summary": risk_summary,
        "staged_fingerprint": staged_fingerprint,
    }
    (scg_dir() / f"{gate_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return gate_id


def load_gate(gate_id: str) -> dict:
    path = scg_dir() / f"{gate_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"gate not found: {gate_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_gate(payload: dict) -> None:
    gate_id = payload["gate_id"]
    (scg_dir() / f"{gate_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
