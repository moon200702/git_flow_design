from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


class TestSCGSmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="scg-smoke-"))
        run(["git", "init"], self.tmpdir)
        run(["git", "config", "user.email", "test@example.com"], self.tmpdir)
        run(["git", "config", "user.name", "Tester"], self.tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def scg(self, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            ["python3", "-m", "safe_commit_guard.cli", *args],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_staged_scan_detects_risky_file(self) -> None:
        target = self.tmpdir / ".env"
        target.write_text("HELLO=world\n", encoding="utf-8")
        run(["git", "add", ".env"], self.tmpdir)

        proc = self.scg("scan", "staged", "--format", "text")

        self.assertEqual(proc.returncode, 1)
        self.assertIn("file.risky", proc.stdout)

    def test_commit_msg_scan_blocks_secret(self) -> None:
        msg = self.tmpdir / "COMMIT_EDITMSG"
        msg.write_text("fix: token=abcd1234\n", encoding="utf-8")

        proc = self.scg("scan", "commit-msg", "--msg-file", str(msg), "--format", "text")

        self.assertEqual(proc.returncode, 1)
        self.assertIn("commitmsg.sensitive", proc.stdout)

    def test_commit_msg_scan_passes_clean_message(self) -> None:
        msg = self.tmpdir / "COMMIT_EDITMSG"
        msg.write_text("feat: add new parser\n", encoding="utf-8")

        proc = self.scg("scan", "commit-msg", "--msg-file", str(msg), "--format", "text")

        self.assertEqual(proc.returncode, 0)
        self.assertIn("SCG: no findings", proc.stdout)


if __name__ == "__main__":
    unittest.main()
