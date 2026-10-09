"""Append-only source supplementation regression on synthetic pinned tree data."""
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
TESTS=Path(__file__).resolve().parent
sys.path.insert(0,str(TESTS))
from test_editorial_contract_v7 import bundle,settings,finish_analysis
from github_learning.lifecycle import prepare_job,_validate_analysis
from github_learning.input_resolver import resolve_repository
from github_learning.research_packet import validate_packet


def blob(content: bytes)->str:
    return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()


_SPEC=importlib.util.spec_from_file_location("supplement_capture",ROOT/"scripts"/"collect_pinned_supplement.py")
assert _SPEC and _SPEC.loader
capture_mod=importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(capture_mod)


class AppendOnlySupplementTests(unittest.TestCase):
    def test_pinned_original_is_append_only_and_packet_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=settings(Path(tmp))
            prompt=b"Use CodexPro.\n"
            source=bundle()
            source=replace(source,tree_entries=source.tree_entries+({
                "path":"CHATGPT_PROMPT.md","type":"blob",
                "sha":blob(prompt),"size":len(prompt)},))
            prepared=prepare_job(cfg,resolve_repository("editorial/demo"),source)
            self.assertEqual(prepared["status"],"analysis_required")
            job=Path(prepared["job_dir"])
            immutable=validate_packet(Path(prepared["packet_path"]))["content_fingerprint"]
            with patch.object(capture_mod,"load_settings",return_value=cfg), \
                 patch.object(capture_mod,"resolve_github_auth",return_value=object()), \
                 patch.object(capture_mod,"_request_text",return_value=prompt.decode()):
                first=capture_mod.capture(job,["CHATGPT_PROMPT.md"])
                again=capture_mod.capture(job,["CHATGPT_PROMPT.md"])
            self.assertEqual(first["status"],"archived")
            self.assertEqual(again["status"],"reused")
            self.assertEqual(validate_packet(Path(prepared["packet_path"]))["content_fingerprint"],immutable)
            supplemental=Path(first["manifest"])
            written=json.loads(supplemental.read_text(encoding="utf-8"))["sources"][0]
            self.assertEqual((supplemental.parent / written["stored_as"]).read_bytes(),prompt)
            self.assertEqual(written["repository_sha"],blob(prompt))
            # Evidence added after prepare needs a fresh v8 analysis job, not
            # silent mutation of the previous Job's evidence contract.
            updated=prepare_job(cfg,resolve_repository("editorial/demo"),
                                source,restart_job=True)
            self.assertEqual(updated["status"],"analysis_required")
            refreshed=Path(updated["job_dir"])
            analysis=finish_analysis(refreshed)
            self.assertEqual(analysis["supplemental_evidence"]["supplement_id"],
                             first["supplement_id"])
            _validate_analysis(refreshed,analysis)
            analysis["supplemental_evidence"]["paths"]=["MALICIOUS.md"]
            with self.assertRaisesRegex(ValueError,"path list mismatch"):
                _validate_analysis(refreshed,analysis)
            with patch.object(capture_mod,"load_settings",return_value=cfg), \
                 patch.object(capture_mod,"resolve_github_auth",return_value=object()), \
                 patch.object(capture_mod,"_request_text",return_value="Tampered text\n"):
                with self.assertRaisesRegex(RuntimeError,"blob did not match"):
                    capture_mod.capture(refreshed,["CHATGPT_PROMPT.md"])

    def test_rejects_unpinned_or_already_captured_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=settings(Path(tmp))
            prepared=prepare_job(cfg,resolve_repository("editorial/demo"),bundle())
            job=Path(prepared["job_dir"])
            with patch.object(capture_mod,"load_settings",return_value=cfg):
                with self.assertRaisesRegex(ValueError,"not in the pinned Git tree"):
                    capture_mod.capture(job,["CHATGPT_PROMPT.md"])
                with self.assertRaisesRegex(ValueError,"Already captured"):
                    capture_mod.capture(job,["README.md"])

if __name__=="__main__":
    unittest.main()
