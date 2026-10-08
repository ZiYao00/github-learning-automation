"""One-off ODS pilot: materialize the README's first image from the pinned Packet.

No source repository code is executed. Does not change any immutable snapshot.
Defaults to a project-local reading preview; publication into the Vault is a
separate, guarded step.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from github_learning.config import load_settings
from github_learning.first_image import materialize_first_image

REPO = "Osmantic/ODS"
REV = "9e59b2b86c96a9590b27b14219b070007093fad1"


def main() -> int:
    snapshot = ROOT / "research" / "github" / "Osmantic" / "ODS" / "snapshots" / REV
    packet = json.loads((snapshot / "packet.json").read_text(encoding="utf-8"))
    if packet.get("packet_id") != f"{REPO}@{REV}":
        raise RuntimeError("ODS pinned Packet identity does not match")
    readmes = [source for source in packet.get("sources", []) if source.get("kind") == "readme"]
    if len(readmes) != 1:
        raise RuntimeError("Expected exactly one README source in snapshot")
    entry = readmes[0]
    readme = snapshot / str(entry["saved_as"])
    expected = str(entry["sha256"])
    import hashlib
    if hashlib.sha256(readme.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Research Packet README checksum mismatch")
    settings = load_settings(ROOT)
    preview_settings = replace(settings, notes_root=ROOT / "notes" / "github")
    with tempfile.TemporaryDirectory(prefix="ods-first-image-") as temp:
        job_dir = Path(temp)
        (job_dir / "sources").mkdir()
        shutil.copyfile(readme, job_dir / "sources" / "001.md")
        shutil.copyfile(snapshot / "media-index.json", job_dir / "media-index.json")
        (job_dir / "source_manifest.json").write_text(
            json.dumps({"sources": [{"kind": "readme", "path": entry["path"], "saved_as": "sources/001.md"}]}),
            encoding="utf-8",
        )
        result = materialize_first_image(
            preview_settings, job_dir,
            {"repository": {"full_name": REPO}, "revision": REV}
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "saved" else 1


if __name__ == "__main__":
    sys.exit(main())
