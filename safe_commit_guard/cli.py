from __future__ import annotations

import argparse
import sys
from pathlib import Path

from safe_commit_guard.engine.runner import scan_commit_msg, scan_pre_push, scan_staged
from safe_commit_guard.policy_loader import load_policy
from safe_commit_guard.report.formatters import format_json, format_text
from safe_commit_guard.workflow.confirm_gate import confirm_gate
from safe_commit_guard.workflow.rollback import rollback_gate


def _print_result(findings, fmt: str) -> None:
    if fmt == "json":
        print(format_json(findings))
    else:
        print(format_text(findings))


def cmd_scan(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy_file)

    if args.scan_target == "staged":
        result = scan_staged(policy)
    elif args.scan_target == "commit-msg":
        msg = Path(args.msg_file).read_text(encoding="utf-8")
        result = scan_commit_msg(msg, policy)
    elif args.scan_target == "pre-push":
        result = scan_pre_push(args.local_sha, args.remote_sha, policy)
    else:
        raise ValueError(f"unsupported scan target: {args.scan_target}")

    _print_result(result.findings, args.format)

    if result.gate_id:
        print(
            f"SCG gate required. Confirm within TTL: scg confirm --id {result.gate_id}",
            file=sys.stderr,
        )

    return 1 if result.blocked else 0


def cmd_confirm(args: argparse.Namespace) -> int:
    ok, message = confirm_gate(args.id)
    print(message)
    return 0 if ok else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    ok, message = rollback_gate(args.id)
    print(message)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scg", description="Safe Commit Guard policy engine")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="run policy scans")
    scan.add_argument("scan_target", choices=["staged", "commit-msg", "pre-push"])
    scan.add_argument("--format", choices=["text", "json"], default="text")
    scan.add_argument("--policy-file")
    scan.add_argument("--msg-file", help="commit message file path")
    scan.add_argument("--local-sha", help="local commit SHA for pre-push")
    scan.add_argument("--remote-sha", help="remote commit SHA for pre-push")
    scan.set_defaults(func=cmd_scan)

    confirm = sub.add_parser("confirm", help="confirm a pending gate")
    confirm.add_argument("--id", required=True)
    confirm.set_defaults(func=cmd_confirm)

    rollback = sub.add_parser("rollback", help="rollback staged state for a gate")
    rollback.add_argument("--id", required=True)
    rollback.set_defaults(func=cmd_rollback)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        if args.scan_target == "commit-msg" and not args.msg_file:
            parser.error("--msg-file is required for scan commit-msg")
        if args.scan_target == "pre-push" and (not args.local_sha or not args.remote_sha):
            parser.error("--local-sha and --remote-sha are required for scan pre-push")

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
