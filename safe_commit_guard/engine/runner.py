from __future__ import annotations

from dataclasses import dataclass

from safe_commit_guard.git.commits import commit_message, commit_patch, rev_list_range
from safe_commit_guard.git.context import run_git
from safe_commit_guard.git.staged import staged_file_content, staged_files, staged_patch
from safe_commit_guard.models import Finding
from safe_commit_guard.scanners.commitmsg_scanner import scan_commit_message
from safe_commit_guard.scanners.diff_anomaly_scanner import scan_patch_anomalies
from safe_commit_guard.scanners.file_scanner import scan_risky_files
from safe_commit_guard.scanners.secret_scanner import scan_text_for_secrets
from safe_commit_guard.workflow.state_store import create_gate


@dataclass(slots=True)
class ScanResult:
    findings: list[Finding]
    blocked: bool
    gate_id: str | None = None


def _block_decision(findings: list[Finding], mode: str) -> bool:
    if mode == "commit-msg":
        return any(f.severity == "critical" for f in findings)
    return any(f.severity in {"critical", "high"} for f in findings)


def _index_fingerprint() -> str:
    return run_git(["write-tree"]).strip()


def scan_staged(policy: dict) -> ScanResult:
    findings: list[Finding] = []
    files = staged_files()
    patch = staged_patch()

    findings.extend(scan_risky_files(files, policy))
    findings.extend(scan_patch_anomalies(patch, "staged-diff", policy))
    findings.extend(scan_text_for_secrets("\n".join(patch.splitlines()), "staged-diff", policy))

    for path in files:
        try:
            content = staged_file_content(path)
        except Exception:
            continue
        findings.extend(scan_text_for_secrets(content, path, policy))

    blocked = _block_decision(findings, mode="staged")
    gate_id: str | None = None
    if blocked and any(f.severity == "high" for f in findings) and not any(
        f.severity == "critical" for f in findings
    ):
        ttl = int(policy.get("confirm_ttl_seconds", 180))
        gate_id = create_gate(ttl, {"total": len(findings)}, _index_fingerprint())
    return ScanResult(findings=findings, blocked=blocked, gate_id=gate_id)


def scan_commit_msg(msg: str, policy: dict) -> ScanResult:
    findings = scan_commit_message(msg, policy)
    return ScanResult(findings=findings, blocked=_block_decision(findings, mode="commit-msg"))


def scan_pre_push(local_sha: str, remote_sha: str, policy: dict) -> ScanResult:
    findings: list[Finding] = []
    commits = rev_list_range(local_sha, remote_sha)
    for sha in commits:
        msg = commit_message(sha)
        patch = commit_patch(sha)
        findings.extend(scan_commit_message(msg, policy))
        findings.extend(scan_patch_anomalies(patch, f"commit:{sha}", policy))
        findings.extend(scan_text_for_secrets(patch, f"commit:{sha}", policy))
    return ScanResult(findings=findings, blocked=_block_decision(findings, mode="pre-push"))
