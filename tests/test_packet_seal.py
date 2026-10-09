"""Packet V1 optional seal: tampering is detected without rewriting old Snapshots."""
from __future__ import annotations
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_editorial_contract_v7 import settings,bundle
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import prepare_job
from github_learning.research_packet import ResearchPacketError,validate_packet


class PacketSealTests(unittest.TestCase):
    def test_new_packet_seal_verifies_and_detects_manifest_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=settings(Path(td))
            prepared=prepare_job(cfg,resolve_repository("editorial/demo"),bundle())
            source=Path(prepared["packet_path"])
            canonical=validate_packet(source)
            self.assertRegex(canonical["archive_seal_sha256"],r"^[0-9a-f]{64}$")
            copy=Path(td)/"isolated-modified-copy"
            shutil.copytree(source,copy)
            packetfile=copy/"packet.json"
            obj=json.loads(packetfile.read_text(encoding="utf-8"))
            obj["archived_at"]="2099-01-01T00:00:00+00:00"
            packetfile.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
            with self.assertRaises(ResearchPacketError) as e:
                validate_packet(copy)
            self.assertEqual(e.exception.code,"packet_seal_mismatch")
            self.assertEqual(validate_packet(source)["content_fingerprint"],canonical["content_fingerprint"])


if __name__=="__main__":
    unittest.main()
