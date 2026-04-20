from __future__ import annotations

import subprocess

from .state_store import load_gate, save_gate


def rollback_gate(gate_id: str) -> tuple[bool, str]:
    payload = load_gate(gate_id)
    proc = subprocess.run(
        ["git", "restore", "--staged", ":/"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip() or "failed to restore staged state"
    payload["status"] = "rolled_back"
    save_gate(payload)
    return True, "staged area rolled back; working tree unchanged"
