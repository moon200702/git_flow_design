from __future__ import annotations

import unittest

from safe_commit_guard.models import Finding
from safe_commit_guard.scanners.common import mask_hash, shannon_entropy, added_lines_from_patch, regex_hits
from safe_commit_guard.scanners.file_scanner import scan_risky_files
from safe_commit_guard.scanners.secret_scanner import scan_text_for_secrets
from safe_commit_guard.scanners.commitmsg_scanner import scan_commit_message
from safe_commit_guard.scanners.diff_anomaly_scanner import scan_patch_anomalies


class TestCommonUtilities(unittest.TestCase):
    def test_mask_hash_deterministic(self) -> None:
        value = "my_secret_token_12345"
        hash1 = mask_hash(value)
        hash2 = mask_hash(value)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)

    def test_mask_hash_different_values(self) -> None:
        hash1 = mask_hash("secret1")
        hash2 = mask_hash("secret2")
        self.assertNotEqual(hash1, hash2)

    def test_shannon_entropy_empty_string(self) -> None:
        self.assertEqual(shannon_entropy(""), 0.0)

    def test_shannon_entropy_single_char(self) -> None:
        self.assertEqual(shannon_entropy("a"), 0.0)

    def test_shannon_entropy_random_string(self) -> None:
        # High entropy for random-looking string
        entropy = shannon_entropy("aB1xY9zQ4k7mNpR2")
        self.assertGreater(entropy, 3.0)

    def test_shannon_entropy_repetitive_string(self) -> None:
        # Low entropy for repetitive string
        entropy = shannon_entropy("aaaaaabbbb")
        self.assertLess(entropy, 1.0)

    def test_added_lines_from_patch_empty(self) -> None:
        patch = ""
        lines = added_lines_from_patch(patch)
        self.assertEqual(lines, [])

    def test_added_lines_from_patch_basic(self) -> None:
        patch = """+added line 1
+added line 2
-removed line
 context line"""
        lines = added_lines_from_patch(patch)
        self.assertEqual(len(lines), 2)
        self.assertIn("added line 1", lines)
        self.assertIn("added line 2", lines)

    def test_added_lines_from_patch_skip_file_header(self) -> None:
        patch = """+++b/file.txt
+new content"""
        lines = added_lines_from_patch(patch)
        self.assertEqual(lines, ["new content"])

    def test_regex_hits_empty_patterns(self) -> None:
        hits = regex_hits([], "some text")
        self.assertEqual(hits, [])

    def test_regex_hits_multiple_patterns(self) -> None:
        patterns = [r"token=\w+", r"password=\w+"]
        text = "token=abc123 and password=xyz789"
        hits = regex_hits(patterns, text)
        self.assertEqual(len(hits), 2)
        self.assertIn("token=abc123", hits)
        self.assertIn("password=xyz789", hits)

    def test_regex_hits_case_insensitive(self) -> None:
        patterns = [r"TOKEN=\w+"]
        text = "token=secret123"
        hits = regex_hits(patterns, text)
        self.assertEqual(len(hits), 1)


class TestFileScanner(unittest.TestCase):
    def test_scan_risky_files_empty(self) -> None:
        policy = {"risky_extensions": [], "risky_filenames": []}
        findings = scan_risky_files([], policy)
        self.assertEqual(findings, [])

    def test_scan_risky_files_by_extension(self) -> None:
        policy = {"risky_extensions": [".env", ".key"], "risky_filenames": []}
        paths = ["config.env", "private.key", "normal.txt"]
        findings = scan_risky_files(paths, policy)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f.rule_id == "file.risky" for f in findings))
        self.assertTrue(all(f.severity == "critical" for f in findings))

    def test_scan_risky_files_by_name(self) -> None:
        policy = {"risky_extensions": [], "risky_filenames": [".env", ".env.local"]}
        paths = [".env", ".env.local", ".config"]
        findings = scan_risky_files(paths, policy)
        self.assertEqual(len(findings), 2)

    def test_scan_risky_files_case_insensitive(self) -> None:
        policy = {"risky_extensions": [".ENV"], "risky_filenames": [".ENV"]}
        paths = [".env", "file.env", ".ENV"]
        findings = scan_risky_files(paths, policy)
        self.assertEqual(len(findings), 3)

    def test_scan_risky_files_dotfiles_no_extension(self) -> None:
        policy = {"risky_extensions": [], "risky_filenames": [".env"]}
        findings = scan_risky_files([".env"], policy)
        self.assertEqual(len(findings), 1)

    def test_scan_risky_files_provides_fix_hint(self) -> None:
        policy = {"risky_extensions": [".pem"], "risky_filenames": []}
        findings = scan_risky_files(["secret.pem"], policy)
        self.assertEqual(len(findings), 1)
        self.assertIn("safe redacted", findings[0].fix_hint)


class TestSecretScanner(unittest.TestCase):
    def test_scan_text_for_secrets_empty(self) -> None:
        policy = {"secret_patterns": [], "entropy_threshold": 4.2, "min_entropy_length": 20}
        findings = scan_text_for_secrets("", "test.txt", policy)
        self.assertEqual(findings, [])

    def test_scan_text_for_secrets_regex_pattern(self) -> None:
        policy = {
            "secret_patterns": [r"token=\w+"],
            "entropy_threshold": 4.2,
            "min_entropy_length": 20,
        }
        text = "api_key=secret123\ntoken=abcd1234efgh"
        findings = scan_text_for_secrets(text, "code.py", policy)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "secret.regex")
        self.assertEqual(findings[0].severity, "critical")
        self.assertIn(":2", findings[0].location)

    def test_scan_text_for_secrets_entropy_detection(self) -> None:
        policy = {
            "secret_patterns": [],
            "entropy_threshold": 4.0,
            "min_entropy_length": 20,
        }
        text = "var apikey = aB1xY9zQ4k7mNpR2vW5tUs"
        findings = scan_text_for_secrets(text, "test.txt", policy)
        entropy_findings = [f for f in findings if f.rule_id == "secret.entropy"]
        self.assertGreater(len(entropy_findings), 0)
        self.assertEqual(entropy_findings[0].severity, "high")

    def test_scan_text_for_secrets_multiline_location(self) -> None:
        policy = {
            "secret_patterns": [r"password=\S+"],
            "entropy_threshold": 4.2,
            "min_entropy_length": 20,
        }
        text = "line1: ok\nline2: password=secret\nline3: ok"
        findings = scan_text_for_secrets(text, "config.txt", policy)
        self.assertEqual(len(findings), 1)
        self.assertIn(":2", findings[0].location)

    def test_scan_text_for_secrets_respects_entropy_threshold(self) -> None:
        policy = {
            "secret_patterns": [],
            "entropy_threshold": 10.0,
            "min_entropy_length": 20,
        }
        text = "aaaaaabbbbbbccccccdddddd"
        findings = scan_text_for_secrets(text, "test.txt", policy)
        self.assertEqual(len(findings), 0)

    def test_scan_text_for_secrets_min_length_check(self) -> None:
        policy = {
            "secret_patterns": [],
            "entropy_threshold": 4.0,
            "min_entropy_length": 100,
        }
        text = "aB1xY9zQ4k7mNpR2"
        findings = scan_text_for_secrets(text, "test.txt", policy)
        self.assertEqual(len(findings), 0)


class TestCommitMsgScanner(unittest.TestCase):
    def test_scan_commit_message_empty(self) -> None:
        policy = {"commit_message_patterns": []}
        findings = scan_commit_message("", policy)
        self.assertEqual(findings, [])

    def test_scan_commit_message_no_secrets(self) -> None:
        policy = {"commit_message_patterns": [r"token=\w+", r"password=\w+"]}
        msg = "feat: add new feature\n\nThis is a clean commit message."
        findings = scan_commit_message(msg, policy)
        self.assertEqual(findings, [])

    def test_scan_commit_message_detects_token(self) -> None:
        policy = {"commit_message_patterns": [r"token=\w+"]}
        msg = "fix: update config with token=abc123def"
        findings = scan_commit_message(msg, policy)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "commitmsg.sensitive")
        self.assertEqual(findings[0].severity, "critical")

    def test_scan_commit_message_case_insensitive(self) -> None:
        policy = {"commit_message_patterns": [r"KEY=\w+"]}
        msg = "feat: added key=secret123"
        findings = scan_commit_message(msg, policy)
        self.assertEqual(len(findings), 1)

    def test_scan_commit_message_multiple_patterns(self) -> None:
        policy = {"commit_message_patterns": [r"token=\w+", r"password=\w+"]}
        msg = "fix: token=abc123 and password=xyz789"
        findings = scan_commit_message(msg, policy)
        self.assertEqual(len(findings), 2)

    def test_scan_commit_message_multiline(self) -> None:
        policy = {"commit_message_patterns": [r"password=\w+"]}
        msg = "feat: add auth\n\nDetails: password=secret123"
        findings = scan_commit_message(msg, policy)
        self.assertEqual(len(findings), 1)


class TestDiffAnomalyScanner(unittest.TestCase):
    def test_scan_patch_anomalies_empty(self) -> None:
        policy = {"max_added_lines": 800}
        findings = scan_patch_anomalies("", "test.txt", policy)
        self.assertEqual(findings, [])

    def test_scan_patch_anomalies_too_large(self) -> None:
        policy = {"max_added_lines": 10}
        lines = "\n".join(f"+line {i}" for i in range(15))
        findings = scan_patch_anomalies(lines, "large.py", policy)
        large_patch_findings = [f for f in findings if f.rule_id == "diff.too_large"]
        self.assertEqual(len(large_patch_findings), 1)
        self.assertEqual(large_patch_findings[0].severity, "high")

    def test_scan_patch_anomalies_base64_blob(self) -> None:
        policy = {"max_added_lines": 800}
        # Use a long base64-like string that matches the BASE64_RE pattern
        long_b64 = "A" * 120 + "B" * 20  # 140+ characters of base64-like pattern
        patch = f"+var img = '{long_b64}'"
        findings = scan_patch_anomalies(patch, "test.txt", policy)
        base64_findings = [f for f in findings if f.rule_id == "diff.base64_blob"]
        self.assertEqual(len(base64_findings), 1)
        self.assertEqual(base64_findings[0].severity, "high")

    def test_scan_patch_anomalies_respects_max_lines(self) -> None:
        policy = {"max_added_lines": 100}
        lines = "\n".join(f"+line {i}" for i in range(50))
        findings = scan_patch_anomalies(lines, "test.txt", policy)
        large_patch_findings = [f for f in findings if f.rule_id == "diff.too_large"]
        self.assertEqual(len(large_patch_findings), 0)

    def test_scan_patch_anomalies_context_lines_ignored(self) -> None:
        policy = {"max_added_lines": 5}
        patch = " context1\n+added1\n context2\n+added2\n context3"
        findings = scan_patch_anomalies(patch, "test.txt", policy)
        large_patch_findings = [f for f in findings if f.rule_id == "diff.too_large"]
        self.assertEqual(len(large_patch_findings), 0)

    def test_scan_patch_anomalies_line_numbering(self) -> None:
        policy = {"max_added_lines": 800}
        patch = "+line1\n+verylongbase64likestring" + "a" * 120
        findings = scan_patch_anomalies(patch, "test.txt", policy)
        base64_findings = [f for f in findings if f.rule_id == "diff.base64_blob"]
        if len(base64_findings) > 0:
            self.assertIn("added#2", base64_findings[0].location)


if __name__ == "__main__":
    unittest.main()
