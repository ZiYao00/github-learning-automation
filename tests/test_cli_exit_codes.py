"""CLI status-to-exit-code contract for unattended Agents.

All network, repository and user-file interactions are mocked. JSON status is
the detail; shell exit codes must not mask a blocked or failed workflow.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from github_learning import cli
from github_learning.config import ConfigurationError
from github_learning.github_client import GitHubFetchError


class CliExitCodeTests(unittest.TestCase):
    def setUp(self):
        self._patches = [
            patch.object(cli, "_configure_stdio"),
            patch.object(cli, "_project_root", return_value=ROOT),
            patch.object(cli, "load_settings", return_value=SimpleNamespace(
                notes_is_fallback=False, research_is_fallback=False,
            )),
            patch.object(cli, "_print"),
            patch.object(cli, "resolve_github_auth", return_value=SimpleNamespace(
                authenticated=True, source="test",
            )),
        ]
        for item in self._patches:
            item.start()
            self.addCleanup(item.stop)

    def _run(self, args: list[str]) -> int:
        with patch.object(sys, "argv", ["github-learning"] + args):
            return cli.main()

    def test_only_explicitly_successful_workflow_states_return_zero(self):
        for command, states in (
            ("prepare", ("analysis_required", "analysis_complete", "no_change",
                         "update_available", "note_ready", "publish_retry_ready")),
            ("finalize", ("note_ready", "no_change", "analysis_required", "publish_retry_ready")),
        ):
            for status in states:
                with self.subTest(command=command, status=status):
                    self.assertEqual(cli._workflow_exit_code(command, {"status": status}), 0)
            for status in (
                "auth_invalid", "auth_required", "rate_limited_or_forbidden",
                "private_repository_blocked", "packet_conflict",
                "legacy_note_refresh_blocked", "invalid_job_state",
                "published_note_missing", "published_note_modified",
                "note_target_changed", "supplement_selection_required",
                "publish_interrupted", "repo_busy", "error", "unknown_status", "",
            ):
                with self.subTest(command=command, status=status):
                    self.assertEqual(cli._workflow_exit_code(command, {"status": status}), 2)

    def test_github_auth_and_privacy_errors_are_failures(self):
        for code in ("auth_required", "auth_invalid",
                     "rate_limited_or_forbidden", "private_repository_blocked"):
            with self.subTest(code=code):
                with patch.object(cli, "preflight_publish", return_value={"status": "ready"}), \
                     patch.object(cli, "fetch_repository_sources",
                                  side_effect=GitHubFetchError(code, "blocked", 403)):
                    self.assertEqual(self._run(["prepare", "editorial/demo"]), 2)

    def test_configuration_error_does_not_report_success(self):
        with patch.object(cli, "load_settings",
                          side_effect=ConfigurationError("invalid_settings", "bad settings")):
            self.assertEqual(self._run(["prepare", "editorial/demo"]), 2)

    def test_blocked_preflight_and_resumption_fail(self):
        for status in ("duplicate_repository_notes", "legacy_note_refresh_blocked",
                       "publish_in_progress", "legacy_job_restart_required"):
            with self.subTest(status=status):
                with patch.object(cli, "preflight_publish", return_value={"status": status}), \
                     patch.object(cli, "fetch_repository_sources") as fetch:
                    self.assertEqual(self._run(["prepare", "editorial/demo"]), 2)
                    fetch.assert_not_called()
        with patch.object(cli, "preflight_publish", return_value={
                "status": "in_progress", "job_dir": str(ROOT / ".runtime" / "fake_job"),
            }), patch.object(cli, "resume_prepare", return_value={
                "status": "invalid_job_state",
            }):
            self.assertEqual(self._run(["prepare", "editorial/demo"]), 2)

    def test_no_auth_and_storage_gate_fail(self):
        with patch.object(cli, "resolve_github_auth", return_value=SimpleNamespace(
                authenticated=False, source="anonymous",
            )):
            self.assertEqual(self._run(["prepare", "editorial/demo"]), 2)
        with patch.object(cli, "_needs_onboarding", return_value=True), \
             patch.object(cli, "_onboarding_required", return_value={
                 "status": "onboarding_required",
             }):
            self.assertEqual(self._run(["prepare", "editorial/demo"]), 2)
            self.assertEqual(self._run(["finalize", ".runtime/fake_job"]), 2)

    def test_finalize_refuses_cached_missing_or_conflicted_notes(self):
        for status in ("invalid_job_state", "published_note_missing",
                       "published_note_modified", "note_target_changed",
                       "publish_conflict", "legacy_note_refresh_blocked"):
            with self.subTest(status=status):
                with patch.object(cli, "finalize_job", return_value={"status": status}):
                    self.assertEqual(self._run(["finalize", ".runtime/fake_job"]), 2)
        with patch.object(cli, "finalize_job", return_value={"status": "note_ready"}):
            self.assertEqual(self._run(["finalize", ".runtime/fake_job"]), 0)


if __name__ == "__main__":
    unittest.main()
