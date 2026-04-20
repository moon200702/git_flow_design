from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from safe_commit_guard.workflow.state_store import create_gate, load_gate, save_gate, scg_dir
from safe_commit_guard.workflow.confirm_gate import confirm_gate
from safe_commit_guard.workflow.rollback import rollback_gate


class TestStateStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="scg-state-"))
        self.git_dir = self.tmpdir / ".git"
        self.git_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    def test_scg_dir_creates_directory(self, mock_git_dir) -> None:
        """Verify scg_dir creates the .git/scg directory."""
        mock_git_dir.return_value = self.git_dir
        result = scg_dir()
        self.assertTrue(result.exists())
        self.assertTrue(result.is_dir())

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    def test_create_gate(self, mock_git_dir) -> None:
        """Verify create_gate generates valid gate file."""
        mock_git_dir.return_value = self.git_dir
        
        gate_id = create_gate(180, {"total": 3}, "abc123def456")
        
        gate_file = self.git_dir / "scg" / f"{gate_id}.json"
        self.assertTrue(gate_file.exists())
        
        payload = json.loads(gate_file.read_text())
        self.assertEqual(payload["gate_id"], gate_id)
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["risk_summary"]["total"], 3)
        self.assertEqual(payload["staged_fingerprint"], "abc123def456")
        self.assertIn("created_at", payload)
        self.assertIn("expires_at", payload)

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    def test_create_gate_ttl(self, mock_git_dir) -> None:
        """Verify create_gate respects TTL."""
        mock_git_dir.return_value = self.git_dir
        
        now = int(time.time())
        gate_id = create_gate(300, {}, "fingerprint")
        
        payload = json.loads((self.git_dir / "scg" / f"{gate_id}.json").read_text())
        self.assertAlmostEqual(payload["expires_at"] - payload["created_at"], 300, delta=1)

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    def test_load_gate(self, mock_git_dir) -> None:
        """Verify load_gate retrieves gate payload."""
        mock_git_dir.return_value = self.git_dir
        
        gate_id = create_gate(180, {"total": 5}, "fingerprint123")
        payload = load_gate(gate_id)
        
        self.assertEqual(payload["gate_id"], gate_id)
        self.assertEqual(payload["risk_summary"]["total"], 5)

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    def test_load_gate_not_found(self, mock_git_dir) -> None:
        """Verify load_gate raises for missing gate."""
        mock_git_dir.return_value = self.git_dir
        
        with self.assertRaises(FileNotFoundError):
            load_gate("nonexistent_gate_id")

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    def test_save_gate(self, mock_git_dir) -> None:
        """Verify save_gate updates gate payload."""
        mock_git_dir.return_value = self.git_dir
        
        gate_id = create_gate(180, {"total": 1}, "fp")
        payload = load_gate(gate_id)
        
        payload["status"] = "confirmed"
        payload["custom_field"] = "test_value"
        save_gate(payload)
        
        updated = load_gate(gate_id)
        self.assertEqual(updated["status"], "confirmed")
        self.assertEqual(updated["custom_field"], "test_value")


class TestConfirmGate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="scg-confirm-"))
        self.git_dir = self.tmpdir / ".git"
        self.git_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("safe_commit_guard.workflow.confirm_gate.load_gate")
    @patch("safe_commit_guard.workflow.confirm_gate.save_gate")
    def test_confirm_gate_pending(self, mock_save, mock_load) -> None:
        """Verify confirm_gate updates pending gate to confirmed."""
        now = int(time.time())
        mock_load.return_value = {
            "gate_id": "gate123",
            "status": "pending",
            "expires_at": now + 300,
        }
        
        ok, message = confirm_gate("gate123")
        
        self.assertTrue(ok)
        self.assertIn("confirmed", message)
        mock_save.assert_called_once()
        saved_payload = mock_save.call_args[0][0]
        self.assertEqual(saved_payload["status"], "confirmed")
        self.assertIn("confirmed_at", saved_payload)

    @patch("safe_commit_guard.workflow.confirm_gate.load_gate")
    @patch("safe_commit_guard.workflow.confirm_gate.save_gate")
    def test_confirm_gate_expired(self, mock_save, mock_load) -> None:
        """Verify confirm_gate rejects expired gate."""
        now = int(time.time())
        mock_load.return_value = {
            "gate_id": "gate123",
            "status": "pending",
            "expires_at": now - 10,
        }
        
        ok, message = confirm_gate("gate123")
        
        self.assertFalse(ok)
        self.assertIn("expired", message)
        saved_payload = mock_save.call_args[0][0]
        self.assertEqual(saved_payload["status"], "expired")

    @patch("safe_commit_guard.workflow.confirm_gate.load_gate")
    @patch("safe_commit_guard.workflow.confirm_gate.save_gate")
    def test_confirm_gate_not_pending(self, mock_save, mock_load) -> None:
        """Verify confirm_gate rejects already-processed gate."""
        mock_load.return_value = {
            "gate_id": "gate123",
            "status": "confirmed",
            "expires_at": int(time.time()) + 300,
        }
        
        ok, message = confirm_gate("gate123")
        
        self.assertFalse(ok)
        self.assertIn("confirmed", message)
        mock_save.assert_not_called()

    @patch("safe_commit_guard.workflow.confirm_gate.load_gate")
    @patch("safe_commit_guard.workflow.confirm_gate.save_gate")
    def test_confirm_gate_boundary_ttl(self, mock_save, mock_load) -> None:
        """Verify confirm_gate rejects just-expired gate."""
        now = int(time.time())
        mock_load.return_value = {
            "gate_id": "gate123",
            "status": "pending",
            "expires_at": now - 1,  # Expired 1 second ago
        }
        
        ok, message = confirm_gate("gate123")
        
        self.assertFalse(ok)
        self.assertIn("expired", message)


class TestRollbackGate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="scg-rollback-"))
        self.git_dir = self.tmpdir / ".git"
        self.git_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("safe_commit_guard.workflow.rollback.load_gate")
    @patch("safe_commit_guard.workflow.rollback.save_gate")
    @patch("safe_commit_guard.workflow.rollback.subprocess.run")
    def test_rollback_gate_success(self, mock_run, mock_save, mock_load) -> None:
        """Verify rollback_gate executes git restore and updates state."""
        mock_load.return_value = {"gate_id": "gate123", "status": "pending"}
        mock_run.return_value = MagicMock(returncode=0)
        
        ok, message = rollback_gate("gate123")
        
        self.assertTrue(ok)
        self.assertIn("rolled back", message)
        mock_run.assert_called_once()
        args = mock_run.call_args[1]
        self.assertIn("git", str(mock_run.call_args[0]))
        self.assertIn("restore", str(mock_run.call_args[0]))
        
        saved_payload = mock_save.call_args[0][0]
        self.assertEqual(saved_payload["status"], "rolled_back")

    @patch("safe_commit_guard.workflow.rollback.load_gate")
    @patch("safe_commit_guard.workflow.rollback.save_gate")
    @patch("safe_commit_guard.workflow.rollback.subprocess.run")
    def test_rollback_gate_git_failure(self, mock_run, mock_save, mock_load) -> None:
        """Verify rollback_gate reports git command failure."""
        mock_load.return_value = {"gate_id": "gate123"}
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: not a git repository"
        )
        
        ok, message = rollback_gate("gate123")
        
        self.assertFalse(ok)
        self.assertIn("fatal", message)
        mock_save.assert_not_called()

    @patch("safe_commit_guard.workflow.rollback.load_gate")
    @patch("safe_commit_guard.workflow.rollback.save_gate")
    @patch("safe_commit_guard.workflow.rollback.subprocess.run")
    def test_rollback_gate_preserves_working_tree(self, mock_run, mock_save, mock_load) -> None:
        """Verify rollback_gate only restores staged area."""
        mock_load.return_value = {"gate_id": "gate123"}
        mock_run.return_value = MagicMock(returncode=0)
        
        rollback_gate("gate123")
        
        cmd = mock_run.call_args[0][0]
        self.assertIn("--staged", cmd)


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete gate workflow."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="scg-workflow-"))
        self.git_dir = self.tmpdir / ".git"
        self.git_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("safe_commit_guard.workflow.state_store.git_dir")
    @patch("safe_commit_guard.workflow.confirm_gate.load_gate")
    @patch("safe_commit_guard.workflow.confirm_gate.save_gate")
    def test_gate_create_and_confirm_flow(
        self, mock_save, mock_load, mock_git_dir
    ) -> None:
        """Verify complete gate creation and confirmation."""
        mock_git_dir.return_value = self.git_dir
        
        # Create gate
        gate_id = create_gate(180, {"total": 2}, "fp123")
        self.assertIsNotNone(gate_id)
        
        # Simulate gate loading for confirmation
        now = int(time.time())
        mock_load.return_value = {
            "gate_id": gate_id,
            "status": "pending",
            "expires_at": now + 300,
        }
        
        ok, message = confirm_gate(gate_id)
        
        self.assertTrue(ok)
        mock_load.assert_called_with(gate_id)


if __name__ == "__main__":
    unittest.main()
