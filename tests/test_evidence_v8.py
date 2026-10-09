"""Evidence-set changes must request reanalysis, not silently rewrite Capture Notes."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_editorial_contract_v7 import settings,bundle,finish_analysis
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import finalize_job,prepare_job
from github_learning.note_template import capture_metadata_from_file

SPEC=importlib.util.spec_from_file_location("supplement_capture",ROOT/"scripts"/"collect_pinned_supplement.py")
assert SPEC and SPEC.loader
supp=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supp)


def blob(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


class EvidenceV8Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg=settings(Path(self.tmp.name))
        self.src=b"Use the original Prompt verbatim.\n"
        b=bundle()
        self.b=replace(b,tree_entries=b.tree_entries+(
            {"path":"CHATGPT_PROMPT.md","type":"blob","sha":blob(self.src),"size":len(self.src)},
        ))
        self.repo=resolve_repository("editorial/demo")

    def test_append_only_supplement_offers_update_and_requires_confirmation(self):
        first=prepare_job(self.cfg,self.repo,self.b)
        self.assertEqual(first["status"],"analysis_required")
        self.assertEqual(json.loads((Path(first["job_dir"])/"job.json").read_text())["version"],8)
        finish_analysis(Path(first["job_dir"]))
        created=finalize_job(self.cfg,Path(first["job_dir"]))
        self.assertEqual(created["status"],"note_ready")
        original=Path(created["note_path"]).read_bytes()
        original_set=capture_metadata_from_file(Path(created["note_path"]))["evidence_set_id"]

        # Create a separately verifiable supplement from another active v8 Job.
        temporary=prepare_job(self.cfg,self.repo,self.b,publish_mode="new")
        self.assertEqual(temporary["status"],"analysis_required")
        with patch.object(supp,"load_settings",return_value=self.cfg), \
             patch.object(supp,"resolve_github_auth",return_value=object()), \
             patch.object(supp,"_request_text",return_value=self.src.decode()):
            supplemental=supp.capture(Path(temporary["job_dir"]),["CHATGPT_PROMPT.md"])
        self.assertEqual(supplemental["status"],"archived")

        pending=prepare_job(self.cfg,self.repo,self.b,restart_job=True)
        self.assertEqual(pending["status"],"update_available")
        self.assertNotEqual(pending["evidence_set_id"],original_set)
        self.assertEqual(Path(created["note_path"]).read_bytes(),original)

        approved=prepare_job(self.cfg,self.repo,self.b,refresh_evidence=True)
        self.assertEqual(approved["status"],"analysis_required")
        nextjob=Path(approved["job_dir"])
        jobdata=json.loads((nextjob/"job.json").read_text(encoding="utf-8"))
        nextanalysis=finish_analysis(nextjob)
        self.assertEqual(nextanalysis["evidence_set_id"],jobdata["evidence_set_id"])
        self.assertEqual(nextanalysis["supplemental_evidence"]["supplement_id"],
                         supplemental["supplement_id"])
        committed=finalize_job(self.cfg,nextjob)
        self.assertEqual(committed["status"],"note_ready")
        self.assertEqual(capture_metadata_from_file(Path(committed["note_path"]))["evidence_set_id"],
                         jobdata["evidence_set_id"])
        unchanged=prepare_job(self.cfg,self.repo,self.b)
        self.assertEqual(unchanged["status"],"no_change")

    def test_note_modified_after_prepare_is_not_overwritten(self):
        first=prepare_job(self.cfg,self.repo,self.b)
        finish_analysis(Path(first["job_dir"]))
        published=finalize_job(self.cfg,Path(first["job_dir"]))
        refreshed=prepare_job(
            self.cfg,self.repo,replace(self.b,revision="cccc"*10),restart_job=True,
        )
        self.assertEqual(refreshed["status"],"analysis_required")
        target=Path(published["note_path"])
        user_edit=target.read_text(encoding="utf-8")+"\nuser change"
        target.write_text(user_edit,encoding="utf-8")
        finish_analysis(Path(refreshed["job_dir"]))
        result=finalize_job(self.cfg,Path(refreshed["job_dir"]))
        self.assertEqual(result["status"],"note_target_changed")
        self.assertEqual(target.read_text(encoding="utf-8"),user_edit)


if __name__=="__main__":
    unittest.main()
