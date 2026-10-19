from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import __version__

PACKET_SCHEMA_VERSION = 1


class ResearchPacketError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ResearchPacketError("packet_invalid_json", f"JSON 必须是对象：{path}")
    return payload


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    if not cleaned:
        raise ResearchPacketError("packet_identity_invalid", f"无法生成安全目录名：{value!r}")
    return cleaned


def packet_id(full_name: str, revision: str) -> str:
    return f"{full_name}@{revision}"


def packet_path(research_root: Path, full_name: str, revision: str) -> Path:
    owner, repo = full_name.split("/", 1)
    return (
        research_root.resolve()
        / _safe_component(owner)
        / _safe_component(repo)
        / "snapshots"
        / _safe_component(revision)
    )


def _repository_root(research_root: Path, full_name: str) -> Path:
    owner, repo = full_name.split("/", 1)
    return research_root.resolve() / _safe_component(owner) / _safe_component(repo)


def _copy_file_checked(source: Path, target: Path) -> None:
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise ResearchPacketError(
                "packet_staging_conflict",
                f"staging 已存在不同内容，拒绝覆盖：{target}",
            )
        return
    target.write_bytes(data)


def _write_bytes_checked(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise ResearchPacketError(
                "packet_staging_conflict",
                f"staging 已存在不同内容，拒绝覆盖：{target}",
            )
        return
    target.write_bytes(data)


def _entry_fingerprint(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: entry.get(key)
        for key in (
            "id",
            "path",
            "kind",
            "repository_sha",
            "sha256",
            "original_bytes",
            "saved_bytes",
            "truncated",
            "archive_role",
            "analysis_mode",
            "authority",
            "coverage_required",
            "saved_as",
            "archive_saved_as",
            "archive_sha256",
            "archive_saved_bytes",
            "archive_truncated",
        )
    }


def _content_fingerprint(
    job: dict[str, Any],
    manifest: dict[str, Any],
    repository_bytes: bytes,
    tree_bytes: bytes,
    media_bytes: bytes,
) -> str:
    payload = {
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "repository": str((job.get("repository") or {}).get("full_name") or ""),
        "revision": str(job.get("revision") or ""),
        "default_branch": str(job.get("default_branch") or ""),
        "content_profile": str(job.get("source_profile") or "generic"),
        "repository_sha256": _sha256_bytes(repository_bytes),
        "tree_index_sha256": _sha256_bytes(tree_bytes),
        "media_index_sha256": _sha256_bytes(media_bytes),
        "sources": [_entry_fingerprint(item) for item in manifest.get("sources") or []],
        "resources": [_entry_fingerprint(item) for item in manifest.get("resources") or []],
    }
    return _sha256_bytes(_json_bytes(payload))


def _validate_entry_file(packet_dir: Path, entry: dict[str, Any]) -> None:
    saved_as = str(entry.get("saved_as") or "")
    expected_hash = str(entry.get("sha256") or "")
    if not saved_as or not expected_hash:
        raise ResearchPacketError("packet_manifest_invalid", "Packet entry 缺少 saved_as 或 sha256。")
    target = packet_dir / saved_as
    if not target.is_file():
        raise ResearchPacketError("packet_file_missing", f"Packet 文件不存在：{target}")
    actual_hash = _sha256_file(target)
    if actual_hash != expected_hash:
        raise ResearchPacketError(
            "packet_hash_mismatch",
            f"Packet 文件哈希不匹配：{target}",
        )


def validate_packet(packet_dir: Path) -> dict[str, Any]:
    packet_dir = packet_dir.resolve()
    packet = _read_json(packet_dir / "packet.json")
    if int(packet.get("packet_schema_version") or 0) != PACKET_SCHEMA_VERSION:
        raise ResearchPacketError("packet_schema_unsupported", f"不支持的 Packet schema：{packet_dir}")

    core_files = {
        "repository.json": "repository_sha256",
        "tree-index.json": "tree_index_sha256",
        "media-index.json": "media_index_sha256",
    }
    for required, hash_key in core_files.items():
        path = packet_dir / required
        if not path.is_file():
            raise ResearchPacketError("packet_file_missing", f"Packet 缺少：{path}")
        expected_hash = str(packet.get(hash_key) or "")
        if not expected_hash:
            raise ResearchPacketError("packet_manifest_invalid", f"Packet 缺少 {hash_key}：{packet_dir}")
        if _sha256_file(path) != expected_hash:
            raise ResearchPacketError("packet_hash_mismatch", f"Packet 核心文件哈希不匹配：{path}")

    for entry in packet.get("sources") or []:
        _validate_entry_file(packet_dir, entry)
    for entry in packet.get("resources") or []:
        _validate_entry_file(packet_dir, entry)

    seal = packet.get("archive_seal_sha256")
    if seal is not None:
        canonical = {key: value for key, value in packet.items() if key != "archive_seal_sha256"}
        if not isinstance(seal, str) or seal != _sha256_bytes(_json_bytes(canonical)):
            raise ResearchPacketError("packet_seal_mismatch", "归档清单的结构指纹不匹配。")

    content_fingerprint = str(packet.get("content_fingerprint") or "")
    if not content_fingerprint:
        raise ResearchPacketError("packet_manifest_invalid", "Packet 缺少 content_fingerprint。")
    return packet


def _runtime_entry_for_packet(entry: dict[str, Any], prefix: str, index: int) -> dict[str, Any]:
    suffix = Path(str(entry.get("path") or "")).suffix.lower()
    extension = suffix if suffix and len(suffix) <= 8 else ".txt"
    saved_as = f"{prefix}/{index:03d}{extension}"
    packet_entry = {
        **_entry_fingerprint(entry),
        "saved_as": saved_as,
    }
    if prefix == "sources" and entry.get("archive_sha256"):
        packet_entry["sha256"] = entry.get("archive_sha256")
        packet_entry["saved_bytes"] = entry.get("archive_saved_bytes")
        packet_entry["truncated"] = bool(entry.get("archive_truncated"))
    packet_entry.pop("archive_saved_as", None)
    packet_entry.pop("archive_sha256", None)
    packet_entry.pop("archive_saved_bytes", None)
    packet_entry.pop("archive_truncated", None)
    return packet_entry


def _archive_observation(
    research_root: Path,
    job: dict[str, Any],
    observation_path: Path,
) -> str | None:
    if not observation_path.is_file():
        return None
    observation = _read_json(observation_path)
    if not observation:
        return None

    full_name = str((job.get("repository") or {}).get("full_name") or "")
    collected_at = str(job.get("collected_at") or "")
    safe_time = re.sub(r"[^0-9A-Za-z]+", "", collected_at) or str(job.get("job_id") or "observation")
    destination = _repository_root(research_root, full_name) / "observations" / f"{safe_time}.json"
    payload = {
        "observation_schema_version": 1,
        "repository": full_name,
        "revision": str(job.get("revision") or ""),
        "observed_at": collected_at,
        **observation,
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    _write_bytes_checked(destination, data)
    return str(destination)


def archive_runtime_packet(research_root: Path, job_dir: Path) -> dict[str, Any]:
    research_root = research_root.resolve()
    if not research_root.is_dir():
        raise ResearchPacketError("research_root_missing", f"Research 目录不存在：{research_root}")

    job_dir = job_dir.resolve()
    job = _read_json(job_dir / "job.json")
    if int(job.get("version") or 0) < 6:
        raise ResearchPacketError(
            "legacy_job_restart_required",
            "v0.3 或更早的 runtime job 不包含完整 Research Packet 元数据，请使用 --restart-job 重新采集。",
        )

    repository = job.get("repository") or {}
    full_name = str(repository.get("full_name") or "")
    revision = str(job.get("revision") or "")
    if not full_name or "/" not in full_name or not revision:
        raise ResearchPacketError("packet_identity_invalid", "Job 缺少 repository full_name 或 revision。")

    manifest = _read_json(job_dir / "source_manifest.json")
    repository_path = job_dir / "repository.json"
    tree_path = job_dir / "tree-index.json"
    media_path = job_dir / "media-index.json"
    for required in (repository_path, tree_path, media_path):
        if not required.is_file():
            raise ResearchPacketError("packet_runtime_incomplete", f"Runtime 缺少 Packet 必需文件：{required}")

    repository_bytes = repository_path.read_bytes()
    tree_bytes = tree_path.read_bytes()
    media_bytes = media_path.read_bytes()
    fingerprint = _content_fingerprint(job, manifest, repository_bytes, tree_bytes, media_bytes)
    target = packet_path(research_root, full_name, revision)

    if target.exists():
        existing = validate_packet(target)
        if str(existing.get("content_fingerprint") or "") != fingerprint:
            # Older and newer collectors may serialize identical JSON with a
            # different whitespace/key order. The immutable Packet's *bytes*
            # remain authoritative, so recalculate using its verified core
            # only after checking that all parsed values match the new job.
            old_core = [(target / name).read_bytes()
                        for name in ("repository.json", "tree-index.json", "media-index.json")]
            try:
                same_core = all(
                    json.loads(now.decode("utf-8")) == json.loads(was.decode("utf-8"))
                    for now, was in zip((repository_bytes, tree_bytes, media_bytes), old_core)
                )
            except (ValueError, UnicodeError):
                same_core = False
            if same_core:
                canonical_fingerprint = _content_fingerprint(job, manifest, *old_core)
                if canonical_fingerprint == str(existing.get("content_fingerprint") or ""):
                    fingerprint = canonical_fingerprint
            if str(existing.get("content_fingerprint") or "") != fingerprint:
                raise ResearchPacketError(
                    "packet_conflict",
                    f"同一 repo@revision 已存在不同内容的 Research Packet，拒绝覆盖：{target}",
                )
        observation_result = _archive_observation(research_root, job, job_dir / "observation.json")
        return {
            "status": "packet_reused",
            "packet_id": packet_id(full_name, revision),
            "packet_path": str(target),
            "content_fingerprint": fingerprint,
            "observation_path": observation_result or "",
        }

    staging = research_root / ".staging" / _safe_component(str(job.get("job_id") or "job"))
    staging.mkdir(parents=True, exist_ok=True)
    _copy_file_checked(repository_path, staging / "repository.json")
    _copy_file_checked(tree_path, staging / "tree-index.json")
    _copy_file_checked(media_path, staging / "media-index.json")

    packet_sources: list[dict[str, Any]] = []
    for index, entry in enumerate(manifest.get("sources") or [], start=1):
        packet_entry = _runtime_entry_for_packet(entry, "sources", index)
        runtime_source = str(entry.get("archive_saved_as") or entry["saved_as"])
        _copy_file_checked(job_dir / runtime_source, staging / packet_entry["saved_as"])
        if _sha256_file(staging / packet_entry["saved_as"]) != str(packet_entry.get("sha256") or ""):
            raise ResearchPacketError("packet_hash_mismatch", f"staging source 哈希不匹配：{entry.get('path')}")
        packet_sources.append(packet_entry)

    packet_resources: list[dict[str, Any]] = []
    for index, entry in enumerate(manifest.get("resources") or [], start=1):
        packet_entry = _runtime_entry_for_packet(entry, "resources", index)
        _copy_file_checked(job_dir / str(entry["saved_as"]), staging / packet_entry["saved_as"])
        if _sha256_file(staging / packet_entry["saved_as"]) != str(packet_entry.get("sha256") or ""):
            raise ResearchPacketError("packet_hash_mismatch", f"staging resource 哈希不匹配：{entry.get('path')}")
        packet_resources.append(packet_entry)

    packet = {
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "producer": {
            "name": "github-learning-automation",
            "version": __version__,
        },
        "packet_id": packet_id(full_name, revision),
        "repository": full_name,
        "revision": revision,
        "default_branch": str(job.get("default_branch") or ""),
        "content_profile": str(job.get("source_profile") or "generic"),
        "archived_at": str(job.get("collected_at") or ""),
        "content_fingerprint": fingerprint,
        "repository_file": "repository.json",
        "repository_sha256": _sha256_bytes(repository_bytes),
        "tree_index": "tree-index.json",
        "tree_index_sha256": _sha256_bytes(tree_bytes),
        "media_index": "media-index.json",
        "media_index_sha256": _sha256_bytes(media_bytes),
        "sources": packet_sources,
        "resources": packet_resources,
    }
    # New V1 archives carry a verifiable seal of the Packet manifest itself.
    # Pre-existing V1 snapshots without this optional field remain readable.
    packet["archive_seal_sha256"] = _sha256_bytes(_json_bytes(packet))
    _write_bytes_checked(
        staging / "packet.json",
        json.dumps(packet, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
    )
    validate_packet(staging)

    target.parent.mkdir(parents=True, exist_ok=True)
    staging.replace(target)
    validate_packet(target)
    observation_result = _archive_observation(research_root, job, job_dir / "observation.json")
    return {
        "status": "packet_archived",
        "packet_id": packet_id(full_name, revision),
        "packet_path": str(target),
        "content_fingerprint": fingerprint,
        "observation_path": observation_result or "",
    }


def resolve_packet(research_root: Path, logical_packet_id: str) -> Path:
    if "@" not in logical_packet_id:
        raise ResearchPacketError("packet_id_invalid", f"无效 packet_id：{logical_packet_id}")
    full_name, revision = logical_packet_id.rsplit("@", 1)
    if "/" not in full_name or not revision:
        raise ResearchPacketError("packet_id_invalid", f"无效 packet_id：{logical_packet_id}")
    target = packet_path(research_root, full_name, revision)
    validate_packet(target)
    return target
