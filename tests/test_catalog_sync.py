"""Offline synchronization, CLI boundary, and real cross-process locking tests."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import test_catalog as fixtures
from github_learning import cli
from github_learning.catalog import CATALOG_NAME, NAV_NAME, CatalogError, catalog_lock, read_document, sha256
from github_learning.catalog_nav import navigation, postprocess_catalog, reconcile


class CatalogSyncTests(unittest.TestCase):
    setUp = fixtures.CatalogTests.setUp
    note = fixtures.CatalogTests.note
    set_state = fixtures.CatalogTests.set_state

    def publication(self, path: Path, *, status: str = "note_ready", state: str | None = "sufficient") -> dict:
        result = {"status": status, "note_path": str(path), "repository": "example/r0"}
        if state is not None:
            result["analysis_status"] = state
        return result

    def run_cli(self, *args: str) -> tuple[int, dict]:
        stream = io.StringIO()
        with patch.object(sys, "argv", ["github-learning", *args]), patch.object(cli, "load_settings", return_value=self.settings), redirect_stdout(stream):
            code = cli.main()
        return code, json.loads(stream.getvalue())

    def test_reconcile_only_updates_derived_columns_and_is_idempotent(self) -> None:
        path = self.note("example/r0")
        note_bytes = path.read_bytes()
        before, _ = read_document(self.settings)
        preview = reconcile(self.settings, dry_run=True)
        self.assertIn("已归档", preview["catalog_diff"])
        self.assertFalse(preview["catalog_written"])
        self.assertEqual(before.raw, self.catalog.read_bytes())
        result = reconcile(self.settings, expected_sha=preview["catalog_sha256"], expected_nav_sha="absent")
        self.assertTrue(result["index_sync_success"])
        self.assertTrue(result["catalog_written"])
        after, _ = read_document(self.settings)
        self.assertEqual(after.rows[0].status, "已归档")
        self.assertIn(r"\|查看笔记", after.rows[0].cells[4])
        self.assertEqual(before.outside_table, after.outside_table)
        self.assertEqual([r.cells[:3] for r in before.rows], [r.cells[:3] for r in after.rows])
        self.assertEqual(note_bytes, path.read_bytes())
        stat = self.catalog.stat().st_mtime_ns
        second = reconcile(self.settings)
        self.assertEqual(second["status"], "no_change")
        self.assertFalse(second["catalog_written"] or second["navigation_written"])
        self.assertEqual(self.catalog.stat().st_mtime_ns, stat)

    def test_minimal_note_is_linked_but_not_checked(self) -> None:
        self.note("example/r0", state="insufficient")
        result = reconcile(self.settings)
        self.assertTrue(result["index_sync_success"])
        doc, _ = read_document(self.settings)
        self.assertEqual(doc.rows[0].status, "待补研究")
        self.assertIn("r0", doc.rows[0].cells[4])
        self.assertNotIn("- [x]", (self.notes / NAV_NAME).read_text(encoding="utf-8"))

    def test_no_change_rereads_actual_analysis_status(self) -> None:
        path = self.note("example/r0", state="insufficient")
        result = postprocess_catalog(self.settings, self.publication(path, status="no_change", state=None))
        self.assertEqual(result["status"], "no_change")
        self.assertTrue(result["catalog_sync"]["index_sync_success"])
        self.assertEqual(read_document(self.settings)[0].rows[0].status, "待补研究")

    def test_false_publication_status_cannot_override_note(self) -> None:
        path = self.note("example/r0", state="insufficient")
        before = self.catalog.read_bytes()
        result = postprocess_catalog(self.settings, self.publication(path, state="sufficient"))
        self.assertEqual(result["status"], "note_ready")
        self.assertFalse(result["catalog_sync"]["index_sync_success"])
        self.assertEqual(before, self.catalog.read_bytes())

    def test_blocked_and_intermediate_results_do_not_sync(self) -> None:
        for status in ["update_available", "analysis_required", "in_progress", "supplement_selection_required",
                       "legacy_note_refresh_blocked", "error"]:
            result = {"status": status}
            with patch("github_learning.catalog_nav.reconcile", side_effect=AssertionError("must not run")):
                self.assertIs(postprocess_catalog(self.settings, result), result)

    def test_published_note_survives_navigation_failure_and_reconcile_repairs(self) -> None:
        from github_learning.catalog_nav import commit_bytes
        path = self.note("example/r0")
        original = path.read_bytes()
        def fail_navigation(target, data, expected):
            if target.name == NAV_NAME:
                raise OSError("simulated disk write failure")
            return commit_bytes(target, data, expected)
        with patch("github_learning.catalog_nav.commit_bytes", side_effect=fail_navigation):
            result = reconcile(self.settings)
        self.assertEqual(result["status"], "index_sync_failed")
        self.assertTrue(result["catalog_written"])
        self.assertFalse(result["navigation_written"])
        self.assertEqual(read_document(self.settings)[0].rows[0].status, "已归档")
        self.assertEqual(original, path.read_bytes())
        recovered = reconcile(self.settings)
        self.assertTrue(recovered["index_sync_success"])
        self.assertFalse(recovered["catalog_written"])
        self.assertTrue(recovered["navigation_written"])
        self.assertEqual(reconcile(self.settings)["status"], "no_change")

    def test_interrupt_between_files_keeps_publish_success_and_can_replay(self) -> None:
        from github_learning.catalog_nav import commit_bytes
        path = self.note("example/r0")
        original = path.read_bytes()
        def interrupt(target, data, expected):
            if target.name == NAV_NAME:
                raise KeyboardInterrupt("simulated process interruption")
            return commit_bytes(target, data, expected)
        with patch("github_learning.catalog_nav.commit_bytes", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            reconcile(self.settings)
        self.assertEqual(path.read_bytes(), original)
        self.assertTrue(reconcile(self.settings)["index_sync_success"])

    def test_editor_change_before_commit_is_preserved(self) -> None:
        from github_learning.catalog_nav import commit_bytes
        self.note("example/r0")
        original = self.catalog.read_bytes()
        edited = original + "\n人工新备注\n".encode("utf-8")
        def edit_before_commit(target, data, expected):
            if target.name == CATALOG_NAME:
                target.write_bytes(edited)
            return commit_bytes(target, data, expected)
        with patch("github_learning.catalog_nav.commit_bytes", side_effect=edit_before_commit):
            result = reconcile(self.settings)
        self.assertEqual(result["status"], "index_sync_failed")
        self.assertFalse(result["catalog_written"])
        self.assertEqual(self.catalog.read_bytes(), edited)
        self.assertFalse((self.notes / NAV_NAME).exists())

    def test_note_change_after_first_write_is_not_hidden(self) -> None:
        self.note("example/r0")
        failure = CatalogError("catalog_sources_changed", "simulated concurrent note edit")
        with patch("github_learning.catalog_nav.NoteIndex.assert_unchanged", side_effect=[None, failure]):
            result = reconcile(self.settings)
        self.assertEqual(result["status"], "index_sync_failed")
        self.assertTrue(result["catalog_written"])
        self.assertFalse(result["navigation_written"])
        self.assertTrue(reconcile(self.settings)["index_sync_success"])

    def test_defer_tested_and_manual_link_comments_survive_sync(self) -> None:
        for repo, state in [("example/r0", "暂缓"), ("example/r1", "已实测")]:
            self.set_state(repo, state)
            self.note(repo)
        self.note("example/r2")
        doc, _ = read_document(self.settings)
        self.catalog.write_bytes(doc.updated({"example/r2": {4: "人工说明，不要覆盖"}}))
        result = reconcile(self.settings)
        after, _ = read_document(self.settings)
        self.assertEqual(after.rows[0].status, "暂缓")
        self.assertEqual(after.rows[1].status, "已实测")
        self.assertEqual(after.rows[2].cells[4], "人工说明，不要覆盖")
        self.assertNotIn("example/r2", result["changes"])

    def test_moved_note_link_is_repaired_without_research(self) -> None:
        path = self.note("example/r0")
        reconcile(self.settings)
        path.rename(self.notes / "移动后的名字.md")
        result = reconcile(self.settings)
        self.assertTrue(result["catalog_written"])
        self.assertIn("移动后的名字", read_document(self.settings)[0].rows[0].cells[4])

    def test_cli_catalog_does_not_resolve_auth(self) -> None:
        with patch.object(cli, "resolve_github_auth", side_effect=AssertionError("auth not needed")):
            code, result = self.run_cli("catalog", "list", "--summary")
        self.assertEqual(code, 0)
        self.assertEqual(result["counts"]["catalog_total"], 34)

    def test_cli_json_batch_and_partial_exit_are_explicit(self) -> None:
        batch = self.base / "batch.json"
        batch.write_text(json.dumps([{"repository": "new/repo", "description": "初步判断：中文介绍", "priority": "高"}, "unclear"], ensure_ascii=False), encoding="utf-8-sig")
        code, result = self.run_cli("catalog", "add", "--input-file", str(batch))
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "catalog_partial")
        self.assertEqual(result["added"], 1)

    def test_cli_finalize_exit_code_survives_postprocess_failure(self) -> None:
        path = self.note("example/r0")
        primary = self.publication(path)
        with patch.object(cli, "finalize_job", return_value=primary), patch("github_learning.catalog_nav.reconcile", side_effect=OSError("simulated sync failure")):
            code, result = self.run_cli("finalize", "fake-job")
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "note_ready")
        self.assertTrue(result["catalog_sync"]["publish_success"])
        self.assertFalse(result["catalog_sync"]["index_sync_success"])
        self.assertEqual(primary, {k: v for k, v in result.items() if k != "catalog_sync"})

    def test_cli_reconcile_failure_has_nonzero_exit(self) -> None:
        self.note("example/r0")
        with patch("github_learning.catalog_nav.commit_bytes", side_effect=OSError("simulated write failure")):
            code, result = self.run_cli("catalog", "reconcile")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "index_sync_failed")

    def test_no_catalog_keeps_original_protocol_and_does_not_create_one(self) -> None:
        standalone = self.base / "without-catalog"
        standalone.mkdir()
        from dataclasses import replace
        settings = replace(self.settings, notes_root=standalone)
        result = {"status": "note_ready", "note_path": "not-inspected-when-catalog-absent"}
        self.assertIs(postprocess_catalog(settings, result), result)
        self.assertFalse((standalone / CATALOG_NAME).exists())

    def test_invalid_or_changed_published_target_is_not_trusted(self) -> None:
        path = self.note("example/r0")
        for primary in [{"status": "no_change"}, self.publication(self.base / "outside.md"),
                        {**self.publication(path), "note_sha256": "0" * 64}]:
            result = postprocess_catalog(self.settings, primary)
            self.assertFalse(result["catalog_sync"]["index_sync_success"])
            self.assertEqual(primary["status"], result["status"])

    def test_generated_navigation_remains_owned_after_crlf_save(self) -> None:
        navigation(self.settings)
        path = self.notes / NAV_NAME
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(reconcile(self.settings)["index_sync_success"])

    def test_nested_junction_is_not_silently_omitted(self) -> None:
        outside = self.base / "extra-notes"
        outside.mkdir()
        link = self.notes / "linked-notes"
        if os.name == "nt":
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
            self.assertEqual(result.returncode, 0)
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(CatalogError):
            reconcile(self.settings)

    def child_code(self) -> str:
        return (
            "import sys,time,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
            "from github_learning.config import Settings; from github_learning.catalog import add_catalog,catalog_lock,CatalogError; "
            "notes=Path(sys.argv[2]); project=Path(sys.argv[3]); "
            "s=Settings(project,notes,project/'runtime',project/'local.json',False); "
        )

    def test_two_processes_and_two_project_roots_cannot_lose_rows(self) -> None:
        gate = self.base / "gate"
        code = self.child_code() + "\ngate=Path(sys.argv[5])\nlimit=time.monotonic()+10\nwhile not gate.exists():\n if time.monotonic()>limit: raise RuntimeError('gate timeout')\n time.sleep(.01)\nprint(json.dumps(add_catalog(s,[sys.argv[4]])))\n"
        workers = []
        try:
            for i in range(2):
                args = [sys.executable, "-B", "-c", code, str(ROOT / "src"), str(self.notes), str(self.base / f"project-{i}"), f"worker/repo{i}", str(gate)]
                workers.append(subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            gate.write_text("go", encoding="utf-8")
            for worker in workers:
                out, err = worker.communicate(timeout=20)
                self.assertEqual(worker.returncode, 0, err.decode("utf-8", errors="replace"))
                self.assertEqual(json.loads(out)["added"], 1)
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate()
        doc, _ = read_document(self.settings)
        self.assertEqual(len(doc.rows), 36)
        self.assertTrue({"worker/repo0", "worker/repo1"} <= {r.key for r in doc.rows})
        self.assertEqual(doc.outside_table[0].count(b"https://github.com"), 10)

    def test_real_v8_engine_publishes_then_syncs_and_verifies_no_change(self) -> None:
        import test_editorial_contract_v7 as engine
        from github_learning.catalog import add_catalog
        from github_learning.input_resolver import resolve_repository
        from github_learning.lifecycle import prepare_job
        self.settings = engine.settings(self.base / "real-engine-full")
        add_catalog(self.settings, ["editorial/demo"])
        prepared = prepare_job(self.settings, resolve_repository("editorial/demo"), engine.bundle())
        self.assertEqual(prepared["status"], "analysis_required")
        engine.finish_analysis(Path(prepared["job_dir"]))
        code, published = self.run_cli("finalize", prepared["job_dir"])
        self.assertEqual(code, 0)
        self.assertEqual(published["status"], "note_ready")
        self.assertTrue(published["catalog_sync"]["index_sync_success"])
        self.assertEqual(read_document(self.settings)[0].rows[0].status, "已归档")
        original = Path(published["note_path"]).read_bytes()
        repeated = prepare_job(self.settings, resolve_repository("editorial/demo"), engine.bundle())
        self.assertEqual(repeated["status"], "no_change")
        synced = postprocess_catalog(self.settings, repeated)
        self.assertTrue(synced["catalog_sync"]["index_sync_success"])
        self.assertEqual(original, Path(published["note_path"]).read_bytes())

    def test_real_v8_minimal_engine_never_checks_completion(self) -> None:
        import test_editorial_contract_v7 as engine
        from github_learning.catalog import add_catalog
        from github_learning.input_resolver import resolve_repository
        from github_learning.lifecycle import prepare_job
        self.settings = engine.settings(self.base / "real-engine-minimal")
        add_catalog(self.settings, ["editorial/demo"])
        prepared = prepare_job(self.settings, resolve_repository("editorial/demo"), engine.bundle())
        analysis_path = Path(prepared["job_dir"]) / "analysis.json"
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        data.update(source_status="insufficient", source_notes="合成来源不足，保留以后研究。")
        analysis_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code, result = self.run_cli("finalize", prepared["job_dir"])
        self.assertEqual(code, 0)
        self.assertEqual(result["analysis_status"], "insufficient")
        self.assertTrue(result["catalog_sync"]["index_sync_success"])
        self.assertEqual(read_document(self.settings)[0].rows[0].status, "待补研究")
        self.assertNotIn("- [x]", (self.settings.notes_root / NAV_NAME).read_text(encoding="utf-8"))

    def test_lock_contention_is_a_visible_error(self) -> None:
        code = self.child_code() + "\ntry:\n with catalog_lock(s,timeout=.1): print('unexpected')\nexcept CatalogError as e: print(e.code)\n"
        with catalog_lock(self.settings):
            result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT / "src"), str(self.notes), str(self.base / "other-project")], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.decode().strip(), "catalog_busy")


if __name__ == "__main__":
    unittest.main()
