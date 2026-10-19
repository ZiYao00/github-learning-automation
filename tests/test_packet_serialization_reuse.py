"""Stable same-revision immutable Packet reuse across JSON formatting changes."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.research_packet import (archive_runtime_packet, validate_packet, ResearchPacketError)
class PacketSerializationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="github-packet-compat-")
        self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name)
        self.research=base/"research";self.research.mkdir()
        self.job=base/"job";self.job.mkdir()
        self.write("job.json",{"version":8,"job_id":"owner__demo__1234",
          "repository":{"full_name":"owner/demo"},"collected_at":"2026-10-19T01:00:00Z",
          "revision":"abcd1234","default_branch":"main","source_profile":"software"})
        self.write("source_manifest.json",{"sources":[],"resources":[]})
        self.write("repository.json",{"name":"demo","full_name":"owner/demo","description":"Demo"})
        self.write("tree-index.json",{"revision":"abcd1234","entries":[{"path":"README.md","type":"blob","sha":"123"}]})
        self.write("media-index.json",{"revision":"abcd1234","entries":[]})
        self.write("observation.json",{"repository_metadata":{},"latest_release":{}})
    def write(self,name,value,pretty=True):
        path=self.job/name
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2 if pretty else None,sort_keys=not pretty)+"\n",encoding="utf-8")
    def reformat(self):
        for name in ("repository.json","tree-index.json","media-index.json"):
            self.write(name,json.loads((self.job/name).read_text(encoding="utf-8")),pretty=False)
    def test_equal_semantics_different_json_bytes_reuses_same_packet(self):
        first=archive_runtime_packet(self.research,self.job)
        target=Path(first["packet_path"])
        originals={p.name:p.read_bytes() for p in target.iterdir() if p.is_file()}
        self.reformat()
        result=archive_runtime_packet(self.research,self.job)
        self.assertEqual(result["status"],"packet_reused")
        self.assertEqual(result["content_fingerprint"],first["content_fingerprint"])
        self.assertEqual({p.name:p.read_bytes() for p in target.iterdir() if p.is_file()}, originals)
        self.assertEqual(validate_packet(target)["content_fingerprint"],first["content_fingerprint"])
    def test_changed_semantic_core_does_not_reuse(self):
        archive_runtime_packet(self.research,self.job)
        self.reformat()
        self.write("tree-index.json",{"revision":"abcd1234","entries":[{"path":"README.md","type":"blob","sha":"CHANGED"}]},pretty=False)
        with self.assertRaises(ResearchPacketError) as ctx:
            archive_runtime_packet(self.research,self.job)
        self.assertEqual(ctx.exception.code,"packet_conflict")
    def test_changed_source_manifest_does_not_reuse(self):
        archive_runtime_packet(self.research,self.job)
        self.reformat()
        self.write("source_manifest.json",{"sources":[{"id":"new","path":"README.md","sha256":"different"}],"resources":[]})
        with self.assertRaises(ResearchPacketError) as ctx:
            archive_runtime_packet(self.research,self.job)
        self.assertEqual(ctx.exception.code,"packet_conflict")
if __name__=="__main__":unittest.main()
