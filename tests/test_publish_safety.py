"""Negative publication regressions; synthetic Vault only, never user notes."""
from __future__ import annotations
import json
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from github_learning.lifecycle import finalize_job, prepare_job
from github_learning.input_resolver import resolve_repository
from github_learning.publish_safety import PublishSafetyError,repository_lock,publish_bytes
from test_editorial_contract_v7 import settings,bundle,finish_analysis


def _competing_process(root: str, out: multiprocessing.Queue) -> None:
    from github_learning.publish_safety import PublishSafetyError, repository_lock
    try:
        with repository_lock(Path(root), "editorial/demo", timeout=0.5):
            out.put("acquired")
    except PublishSafetyError as exc:
        out.put(exc.code)


class PublishSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg=settings(Path(self.tmp.name))
        prepared=prepare_job(self.cfg,resolve_repository("editorial/demo"),bundle())
        self.jobdir=Path(prepared["job_dir"])

    def test_terminal_failure_never_publishes(self):
        job=self.jobdir/"job.json"
        for state in ("superseded","packet_archive_failed","unknown"):
            record=json.loads(job.read_text(encoding="utf-8"))
            record["state"]=state
            job.write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
            result=finalize_job(self.cfg,self.jobdir)
            self.assertEqual(result["status"],"invalid_job_state")
            self.assertFalse(list(self.cfg.notes_root.rglob("demo.md")))

    def test_cached_success_rechecks_file(self):
        finish_analysis(self.jobdir)
        done=finalize_job(self.cfg,self.jobdir)
        self.assertEqual(done["status"],"note_ready")
        path=Path(done["note_path"])
        self.assertEqual(finalize_job(self.cfg,self.jobdir)["verification"],"sha256")
        path.write_text(path.read_text(encoding="utf-8")+"\nmanual edit\n",encoding="utf-8")
        self.assertEqual(finalize_job(self.cfg,self.jobdir)["status"],"published_note_modified")
        path.unlink()
        self.assertEqual(finalize_job(self.cfg,self.jobdir)["status"],"published_note_missing")

    def test_mid_commit_crash_recovers_written_file(self):
        finish_analysis(self.jobdir)
        import github_learning.lifecycle as lifecycle
        orig=lifecycle._persist_job_state
        def crash_after_write(jobdir,job,state,**extra):
            if state=="published":
                raise RuntimeError("simulated abrupt termination after file commit")
            return orig(jobdir,job,state,**extra)
        with patch.object(lifecycle,"_persist_job_state",side_effect=crash_after_write):
            with self.assertRaisesRegex(RuntimeError,"abrupt termination"):
                finalize_job(self.cfg,self.jobdir)
        record=json.loads((self.jobdir/"job.json").read_text(encoding="utf-8"))
        self.assertEqual(record["state"],"publishing")
        notes=list(self.cfg.notes_root.rglob("demo.md"))
        self.assertEqual(len(notes),1)
        note_sha=notes[0].read_bytes()
        outcome=finalize_job(self.cfg,self.jobdir)
        self.assertTrue(outcome["recovered"])
        self.assertEqual(outcome["status"],"note_ready")
        self.assertEqual(notes[0].read_bytes(),note_sha)

    def test_crash_before_commit_retries_without_overwriting(self):
        finish_analysis(self.jobdir)
        with patch("github_learning.lifecycle.publish_bytes",side_effect=RuntimeError("test crash")):
            with self.assertRaisesRegex(RuntimeError,"test crash"):
                finalize_job(self.cfg,self.jobdir)
        self.assertEqual(finalize_job(self.cfg,self.jobdir)["status"],"publish_retry_ready")
        self.assertEqual(finalize_job(self.cfg,self.jobdir)["status"],"note_ready")

    def test_second_writer_uses_repo_busy_not_fake_lock_cleanup(self):
        with repository_lock(self.cfg.runtime_root,"editorial/demo"):
            with self.assertRaisesRegex(PublishSafetyError,"另一个 Agent"):
                with repository_lock(self.cfg.runtime_root,"editorial/demo",timeout=0.2):
                    pass

    def test_os_lock_is_shared_across_processes(self):
        context = multiprocessing.get_context("spawn")
        out = context.Queue()
        with repository_lock(self.cfg.runtime_root, "editorial/demo"):
            process = context.Process(
                target=_competing_process, args=(str(self.cfg.runtime_root),out),
            )
            process.start()
            process.join(timeout=9)
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)
            self.assertEqual(process.exitcode,0)
            self.assertEqual(out.get(timeout=2),"repo_busy")

    def test_atomic_create_never_overwrites_other_file(self):
        target=self.cfg.notes_root/"test.md"
        target.write_bytes(b"someone else")
        with self.assertRaises(PublishSafetyError) as error:
            publish_bytes(target,b"ours",expected_old_sha=None)
        self.assertEqual(error.exception.code,"note_target_changed")
        self.assertEqual(target.read_bytes(),b"someone else")


if __name__=="__main__":
    unittest.main()
