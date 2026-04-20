from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from safe_commit_guard.models import Finding
from safe_commit_guard.policy_loader import load_policy
from safe_commit_guard.report.formatters import format_text, format_json, summarize


class TestPolicyLoader(unittest.TestCase):
    def test_load_policy_from_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            policy = {
                "risky_extensions": [".env"],
                "risky_filenames": [".env.local"],
                "secret_patterns": [r"token=\w+"],
            }
            json.dump(policy, f)
            f.flush()
            try:
                loaded = load_policy(f.name)
                self.assertEqual(loaded["risky_extensions"], [".env"])
                self.assertEqual(loaded["risky_filenames"], [".env.local"])
            finally:
                Path(f.name).unlink()

    def test_load_policy_default(self) -> None:
        policy = load_policy()
        self.assertIsInstance(policy, dict)
        self.assertIn("risky_extensions", policy)
        self.assertIn("secret_patterns", policy)


class TestFormatters(unittest.TestCase):
    def test_format_text_empty_findings(self) -> None:
        text = format_text([])
        self.assertEqual(text, "SCG: no findings")

    def test_format_text_single_finding(self) -> None:
        findings = [
            Finding(
                rule_id="test.rule",
                severity="critical",
                message="Test finding",
                location="file.txt",
                evidence_hash="abc123",
                fix_hint="Fix this",
            )
        ]
        text = format_text(findings)
        self.assertIn("SCG findings:", text)
        self.assertIn("[critical]", text)
        self.assertIn("test.rule", text)
        self.assertIn("Test finding", text)

    def test_format_text_multiple_findings(self) -> None:
        findings = [
            Finding("rule1", "critical", "msg1", "loc1", "hash1", "hint1"),
            Finding("rule2", "high", "msg2", "loc2", "hash2", "hint2"),
        ]
        text = format_text(findings)
        self.assertIn("rule1", text)
        self.assertIn("rule2", text)
        self.assertIn("Summary:", text)

    def test_format_text_includes_summary(self) -> None:
        findings = [
            Finding("rule1", "critical", "msg1", "loc1", "hash1", "hint1"),
            Finding("rule2", "critical", "msg2", "loc2", "hash2", "hint2"),
            Finding("rule3", "high", "msg3", "loc3", "hash3", "hint3"),
        ]
        text = format_text(findings)
        self.assertIn("total", text)
        self.assertIn("by_severity", text)

    def test_format_json_empty_findings(self) -> None:
        json_str = format_json([])
        data = json.loads(json_str)
        self.assertEqual(data["findings"], [])
        self.assertEqual(data["summary"]["total"], 0)

    def test_format_json_valid_structure(self) -> None:
        findings = [
            Finding("rule1", "critical", "msg1", "loc1", "hash1", "hint1"),
            Finding("rule2", "high", "msg2", "loc2", "hash2", "hint2"),
        ]
        json_str = format_json(findings)
        data = json.loads(json_str)
        self.assertIn("findings", data)
        self.assertIn("summary", data)
        self.assertEqual(len(data["findings"]), 2)

    def test_format_json_finding_fields(self) -> None:
        findings = [Finding("rid", "high", "message", "location", "evhash", "hint")]
        json_str = format_json(findings)
        data = json.loads(json_str)
        f = data["findings"][0]
        self.assertEqual(f["rule_id"], "rid")
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["message"], "message")
        self.assertEqual(f["location"], "location")
        self.assertEqual(f["evidence_hash"], "evhash")
        self.assertEqual(f["fix_hint"], "hint")

    def test_format_json_summary_counts(self) -> None:
        findings = [
            Finding("r1", "critical", "m1", "l1", "h1", "hint1"),
            Finding("r2", "critical", "m2", "l2", "h2", "hint2"),
            Finding("r3", "high", "m3", "l3", "h3", "hint3"),
        ]
        json_str = format_json(findings)
        data = json.loads(json_str)
        summary = data["summary"]
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_severity"]["critical"], 2)
        self.assertEqual(summary["by_severity"]["high"], 1)


class TestSummarize(unittest.TestCase):
    def test_summarize_empty(self) -> None:
        summary = summarize([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["by_severity"], {})

    def test_summarize_single_finding(self) -> None:
        findings = [Finding("r1", "critical", "m1", "l1", "h1", "hint")]
        summary = summarize(findings)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["by_severity"]["critical"], 1)

    def test_summarize_multiple_severities(self) -> None:
        findings = [
            Finding("r1", "critical", "m1", "l1", "h1", "hint"),
            Finding("r2", "high", "m2", "l2", "h2", "hint"),
            Finding("r3", "high", "m3", "l3", "h3", "hint"),
        ]
        summary = summarize(findings)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_severity"]["critical"], 1)
        self.assertEqual(summary["by_severity"]["high"], 2)


class TestFinding(unittest.TestCase):
    def test_finding_creation(self) -> None:
        f = Finding(
            rule_id="test.rule",
            severity="critical",
            message="Test message",
            location="file.txt",
            evidence_hash="abc123",
            fix_hint="Fix this",
        )
        self.assertEqual(f.rule_id, "test.rule")
        self.assertEqual(f.severity, "critical")

    def test_finding_to_dict(self) -> None:
        f = Finding(
            rule_id="test.rule",
            severity="high",
            message="msg",
            location="loc",
            evidence_hash="hash",
            fix_hint="hint",
        )
        d = f.to_dict()
        self.assertEqual(d["rule_id"], "test.rule")
        self.assertEqual(d["severity"], "high")
        self.assertEqual(len(d), 6)


if __name__ == "__main__":
    unittest.main()
