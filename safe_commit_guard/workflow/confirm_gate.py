from __future__ import annotations

import time

from .state_store import load_gate, save_gate


def confirm_gate(gate_id: str) -> tuple[bool, str]:
    payload = load_gate(gate_id)
    now = int(time.time())
    if payload.get("status") != "pending":
        return False, f"gate status is {payload.get('status')}"
    if now > int(payload["expires_at"]):
        payload["status"] = "expired"
        save_gate(payload)
        return False, "gate expired"
    payload["status"] = "confirmed"
    payload["confirmed_at"] = now
    save_gate(payload)
    return True, "gate confirmed"
