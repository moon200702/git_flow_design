from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from safe_commit_guard.engine.runner import _block_decision, ScanResult
from safe_commit_guard.models import Finding


class TestBlockDecision(unittest.TestCase):
    def test_block_decision_staged_no_findings(self) -> None:
        blocked = _block_decision([], "staged")
        self.assertFalse(blocked)

    def test_block_decision_staged_critical(self) -> None:
        findings = [Finding("r1", "critical", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "staged")
        self.assertTrue(blocked)

    def test_block_decision_staged_high_only(self) -> None:
        findings = [Finding("r1", "high", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "staged")
        self.assertTrue(blocked)

    def test_block_decision_staged_low_only(self) -> None:
        findings = [Finding("r1", "low", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "staged")
        self.assertFalse(blocked)

    def test_block_decision_commit_msg_critical(self) -> None:
        findings = [Finding("r1", "critical", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "commit-msg")
        self.assertTrue(blocked)

    def test_block_decision_commit_msg_high_not_blocking(self) -> None:
        findings = [Finding("r1", "high", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "commit-msg")
        self.assertFalse(blocked)

    def test_block_decision_prepush_critical(self) -> None:
        findings = [Finding("r1", "critical", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "pre-push")
        self.assertTrue(blocked)

    def test_block_decision_prepush_high(self) -> None:
        findings = [Finding("r1", "high", "m1", "l1", "h1", "hint")]
        blocked = _block_decision(findings, "pre-push")
        self.assertTrue(blocked)

    def test_block_decision_mixed_severities_staged(self) -> None:
        findings = [
            Finding("r1", "low", "m1", "l1", "h1", "hint"),
            Finding("r2", "high", "m2", "l2", "h2", "hint"),
        ]
        blocked = _block_decision(findings, "staged")
        self.assertTrue(blocked)


class TestScanResult(unittest.TestCase):
    def test_scan_result_creation(self) -> None:
        findings = [Finding("r1", "critical", "m1", "l1", "h1", "hint")]
        result = ScanResult(findings=findings, blocked=True)
        self.assertEqual(len(result.findings), 1)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.gate_id)

    def test_scan_result_with_gate_id(self) -> None:
        findings = []
        result = ScanResult(findings=findings, blocked=False, gate_id="gate123")
        self.assertEqual(result.gate_id, "gate123")

    def test_scan_result_empty(self) -> None:
        result = ScanResult(findings=[], blocked=False)
        self.assertEqual(result.findings, [])
        self.assertFalse(result.blocked)


class TestEngineIntegration(unittest.TestCase):
    """Integration tests for scanner engine with mocked git functions."""

    @patch("safe_commit_guard.engine.runner.staged_files")
    @patch("safe_commit_guard.engine.runner.staged_patch")
    @patch("safe_commit_guard.engine.runner.scan_risky_files")
    @patch("safe_commit_guard.engine.runner.scan_patch_anomalies")
    @patch("safe_commit_guard.engine.runner.scan_text_for_secrets")
    @patch("safe_commit_guard.engine.runner.staged_file_content")
    def test_scan_staged_calls_all_scanners(
        self,
        mock_file_content,
        mock_text_secrets,
        mock_patch_anomalies,
        mock_risky_files,
        mock_patch,
        mock_files,
    ) -> None:
        """Verify scan_staged invokes all scanner functions."""
        from safe_commit_guard.engine.runner import scan_staged

        mock_files.return_value = ["file1.py"]
        mock_patch.return_value = "+line1\n+line2"
        mock_risky_files.return_value = []
        mock_patch_anomalies.return_value = []
        mock_text_secrets.return_value = []
        mock_file_content.return_value = "content"

        policy = {
            "confirm_ttl_seconds": 180,
            "risky_extensions": [],
            "risky_filenames": [],
            "secret_patterns": [],
            "entropy_threshold": 4.2,
            "min_entropy_length": 20,
            "max_added_lines": 800,
        }

        result = scan_staged(policy)

        mock_files.assert_called_once()
        mock_patch.assert_called_once()
        mock_risky_files.assert_called_once()
        mock_patch_anomalies.assert_called_once()
        self.assertIsInstance(result, ScanResult)

    @patch("safe_commit_guard.engine.runner.scan_commit_message")
    def test_scan_commit_msg_integration(self, mock_scan_msg) -> None:
        """Verify scan_commit_msg calls scanner and returns result."""
        from safe_commit_guard.engine.runner import scan_commit_msg

        mock_scan_msg.return_value = []
        policy = {"commit_message_patterns": []}

        result = scan_commit_msg("test message", policy)

        self.assertIsInstance(result, ScanResult)
        self.assertEqual(result.findings, [])
        self.assertFalse(result.blocked)

    @patch("safe_commit_guard.engine.runner.rev_list_range")
    @patch("safe_commit_guard.engine.runner.commit_message")
    @patch("safe_commit_guard.engine.runner.commit_patch")
    @patch("safe_commit_guard.engine.runner.scan_commit_message")
    @patch("safe_commit_guard.engine.runner.scan_patch_anomalies")
    @patch("safe_commit_guard.engine.runner.scan_text_for_secrets")
    def test_scan_pre_push_scans_commits(
        self,
        mock_text_secrets,
        mock_patch_anomalies,
        mock_scan_msg,
        mock_patch,
        mock_message,
        mock_rev_list,
    ) -> None:
        """Verify scan_pre_push scans all commits in range."""
        from safe_commit_guard.engine.runner import scan_pre_push

        mock_rev_list.return_value = ["commit1", "commit2"]
        mock_message.return_value = "commit message"
        mock_patch.return_value = "+line1"
        mock_scan_msg.return_value = []
        mock_patch_anomalies.return_value = []
        mock_text_secrets.return_value = []

        policy = {
            "commit_message_patterns": [],
            "secret_patterns": [],
            "entropy_threshold": 4.2,
            "min_entropy_length": 20,
            "max_added_lines": 800,
        }

        result = scan_pre_push("abc123", "def456", policy)

        # Should process both commits
        self.assertEqual(mock_message.call_count, 2)
        self.assertEqual(mock_patch.call_count, 2)
        self.assertIsInstance(result, ScanResult)


class TestEngineBlockingLogic(unittest.TestCase):
    """Test blocking decision logic for different severity levels."""

    @patch("safe_commit_guard.engine.runner.staged_files")
    @patch("safe_commit_guard.engine.runner.staged_patch")
    @patch("safe_commit_guard.engine.runner.scan_risky_files")
    @patch("safe_commit_guard.engine.runner.scan_patch_anomalies")
    @patch("safe_commit_guard.engine.runner.scan_text_for_secrets")
    @patch("safe_commit_guard.engine.runner.staged_file_content")
    def test_scan_staged_high_severity_creates_gate(
        self,
        mock_file_content,
        mock_text_secrets,
        mock_patch_anomalies,
        mock_risky_files,
        mock_patch,
        mock_files,
    ) -> None:
        """Verify gate creation when high-severity findings exist without critical."""
        from safe_commit_guard.engine.runner import scan_staged

        mock_files.return_value = []
        mock_patch.return_value = ""
        mock_risky_files.return_value = [
            Finding("r1", "high", "m1", "l1", "h1", "hint")
        ]
        mock_patch_anomalies.return_value = []
        mock_text_secrets.return_value = []

        policy = {"confirm_ttl_seconds": 180}

        with patch("safe_commit_guard.engine.runner.create_gate") as mock_create:
            mock_create.return_value = "gate123"
            result = scan_staged(policy)

            self.assertTrue(result.blocked)
            self.assertEqual(result.gate_id, "gate123")
            mock_create.assert_called_once()

    @patch("safe_commit_guard.engine.runner.staged_files")
    @patch("safe_commit_guard.engine.runner.staged_patch")
    @patch("safe_commit_guard.engine.runner.scan_risky_files")
    @patch("safe_commit_guard.engine.runner.scan_patch_anomalies")
    @patch("safe_commit_guard.engine.runner.scan_text_for_secrets")
    @patch("safe_commit_guard.engine.runner.staged_file_content")
    def test_scan_staged_critical_no_gate(
        self,
        mock_file_content,
        mock_text_secrets,
        mock_patch_anomalies,
        mock_risky_files,
        mock_patch,
        mock_files,
    ) -> None:
        """Verify no gate created when critical findings exist."""
        from safe_commit_guard.engine.runner import scan_staged

        mock_files.return_value = []
        mock_patch.return_value = ""
        mock_risky_files.return_value = [
            Finding("r1", "critical", "m1", "l1", "h1", "hint")
        ]
        mock_patch_anomalies.return_value = []
        mock_text_secrets.return_value = []

        policy = {"confirm_ttl_seconds": 180}

        result = scan_staged(policy)

        self.assertTrue(result.blocked)
        self.assertIsNone(result.gate_id)


if __name__ == "__main__":
    unittest.main()
