import json
from pathlib import Path

import pytest

from github_learning.research_packet import ResearchPacketError, archive_runtime_packet, validate_packet


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _runtime_job(tmp_path: Path) -> tuple[Path, Path]:
    research = tmp_path / "research"
    research.mkdir()
    job_dir = tmp_path / "jobs" / "owner__demo__1234"
    (job_dir / "sources").mkdir(parents=True)
    (job_dir / "archive_sources").mkdir(parents=True)
    (job_dir / "resources").mkdir(parents=True)

    analysis_text = "short"
    archive_text = "full archive source content"
    resource_text = "resource body"
    (job_dir / "sources/001_README.md.txt").write_text(analysis_text, encoding="utf-8")
    (job_dir / "archive_sources/001_README.md.txt").write_text(archive_text, encoding="utf-8")
    (job_dir / "resources/001_template.md.txt").write_text(resource_text, encoding="utf-8")

    import hashlib

    sha = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()

    _write_json(
        job_dir / "job.json",
        {
            "version": 6,
            "job_id": "owner__demo__1234",
            "state": "collected",
            "collected_at": "2026-10-07T12:00:00+00:00",
            "revision": "abc123",
            "default_branch": "main",
            "source_profile": "agent-skill",
            "repository": {"full_name": "owner/demo"},
        },
    )
    _write_json(
        job_dir / "source_manifest.json",
        {
            "schema_version": 2,
            "sources": [
                {
                    "id": "src-001",
                    "path": "README.md",
                    "kind": "readme",
                    "repository_sha": "gitsha",
                    "sha256": sha(analysis_text),
                    "original_bytes": len(archive_text),
                    "saved_bytes": len(analysis_text),
                    "truncated": True,
                    "archive_role": "source",
                    "analysis_mode": "full",
                    "authority": "repository_authored",
                    "coverage_required": True,
                    "saved_as": "sources/001_README.md.txt",
                    "archive_saved_as": "archive_sources/001_README.md.txt",
                    "archive_sha256": sha(archive_text),
                    "archive_saved_bytes": len(archive_text),
                    "archive_truncated": False,
                }
            ],
            "resources": [
                {
                    "id": "res-001",
                    "path": "assets/template.md",
                    "kind": "archived_resource",
                    "repository_sha": "resgit",
                    "sha256": sha(resource_text),
                    "original_bytes": len(resource_text),
                    "saved_bytes": len(resource_text),
                    "truncated": False,
                    "archive_role": "resource",
                    "analysis_mode": "index_only",
                    "authority": "repository_authored",
                    "coverage_required": False,
                    "saved_as": "resources/001_template.md.txt",
                }
            ],
        },
    )
    _write_json(job_dir / "repository.json", {"full_name": "owner/demo", "revision": "abc123"})
    _write_json(job_dir / "tree-index.json", {"schema_version": 1, "revision": "abc123", "entries": []})
    _write_json(job_dir / "media-index.json", {"schema_version": 1, "revision": "abc123", "entries": []})
    _write_json(job_dir / "observation.json", {"repository_metadata": {}, "latest_release": {}})
    return research, job_dir


def test_packet_archives_full_source_and_reuses_same_revision(tmp_path: Path):
    research, job_dir = _runtime_job(tmp_path)

    first = archive_runtime_packet(research, job_dir)
    packet_dir = Path(first["packet_path"])
    packet = validate_packet(packet_dir)
    second = archive_runtime_packet(research, job_dir)

    assert first["status"] == "packet_archived"
    assert second["status"] == "packet_reused"
    assert (packet_dir / packet["sources"][0]["saved_as"]).read_text(encoding="utf-8") == "full archive source content"
    assert packet["sources"][0]["saved_bytes"] > len("short")
    assert packet["resources"][0]["path"] == "assets/template.md"


def test_packet_validation_detects_core_file_tampering(tmp_path: Path):
    research, job_dir = _runtime_job(tmp_path)
    result = archive_runtime_packet(research, job_dir)
    packet_dir = Path(result["packet_path"])

    (packet_dir / "tree-index.json").write_text('{"changed": true}\n', encoding="utf-8")

    with pytest.raises(ResearchPacketError) as exc_info:
        validate_packet(packet_dir)

    assert exc_info.value.code == "packet_hash_mismatch"
