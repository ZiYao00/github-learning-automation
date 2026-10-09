"""Collect explicitly selected, revision-pinned Markdown supplements for an archived Job.

This is an append-only *separate* evidence set, NOT a replacement Research
Packet. Each item must be present in the job's pinned git tree with exact blob
SHA-1 and original byte size; fetched bytes are checked against that tree.
Never execute repository content or read arbitrary URLs.

Usage:
 py -3.12 scripts/collect_pinned_supplement.py <runtime-job-dir> CHATGPT_PROMPT.md CODEX_PROMPT.md README_ZH.md
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from github_learning.config import load_settings
from github_learning.github_client import _raw_url, _request_text
from github_learning.auth import resolve_github_auth
from github_learning.research_packet import resolve_packet


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def capture(job_path: Path, paths: list[str]) -> dict:
    cfg = load_settings(ROOT)
    job_path = job_path.resolve()
    if cfg.runtime_root.resolve() not in job_path.parents:
        raise RuntimeError("Job is outside configured runtime root")
    job = json.loads((job_path / "job.json").read_text(encoding="utf-8"))
    if int(job.get("version") or 0) < 7 or job.get("state") != "analysis_required":
        raise RuntimeError("Only active V2.2 v7+ jobs accept provenance supplements")
    repo = str(job["repository"]["full_name"])
    rev = str(job["revision"])
    if not re.fullmatch(r"[0-9a-f]{40}", rev):
        raise RuntimeError("Unpinned revision")
    packet = resolve_packet(cfg.research_root, str(job["packet_id"]))
    if packet.resolve() != Path(job["packet_path"]).resolve():
        raise RuntimeError("Job is not bound to the verified immutable Packet")
    manifest = json.loads((job_path / "source_manifest.json").read_text(encoding="utf-8"))
    already = {item["path"] for item in manifest.get("sources", []) + manifest.get("resources", [])}
    index = json.loads((job_path / "tree-index.json").read_text(encoding="utf-8"))
    path_index = {item["path"]: item for item in index["entries"]}
    if not 1 <= len(paths) <= 6 or len(set(paths)) != len(paths):
        raise ValueError("Supply 1–6 distinct Markdown supplement paths")
    for path in paths:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+){0,2}\.md", path, re.I):
            raise ValueError("Unsafe or unsupported Markdown path: " + path)
        if path in already:
            raise ValueError("Already captured in the immutable Packet: " + path)
        entry = path_index.get(path)
        if not entry or entry.get("type") != "blob":
            raise ValueError("File not in the pinned Git tree: " + path)
        if not re.fullmatch(r"[a-f0-9]{40}", str(entry.get("sha") or "")):
            raise ValueError("Pinned Git blob is missing: " + path)
        if not 0 < int(entry.get("size") or 0) <= 80_000:
            raise ValueError("File exceeds the 80 KB evidence limit: " + path)

    path_hash = sha256("\n".join(sorted(paths)).encode())[:16]
    dest = cfg.research_root / repo.split("/")[0] / repo.split("/")[1] / "supplements" / rev / path_hash
    auth = resolve_github_auth()
    rows = []
    texts = []
    for i, path in enumerate(paths, 1):
        content = _request_text(_raw_url(repo, rev, path), auth)
        raw = content.encode("utf-8")
        expected = path_index[path]
        if len(raw) != int(expected["size"]) or git_blob(raw) != expected["sha"]:
            raise RuntimeError("Pinned Git tree blob did not match downloaded source: " + path)
        relative_file = f"{i:03d}_{sha256(path.encode())[:12]}.md"
        texts.append((relative_file, raw))
        rows.append({
            "source_id": f"supp-{i:03d}",
            "path": path,
            "kind": "author_original_supplement",
            "repository_sha": expected["sha"],
            "sha256": sha256(raw),
            "bytes": len(raw),
            "stored_as": "files/" + relative_file,
            "source_url": f"https://github.com/{repo}/blob/{rev}/" + "/".join(quote(t) for t in path.split("/")),
            "authority": "repository_authored",
        })
    payload = {
        "schema_version": 1,
        "kind": "append_only_pinned_supplement",
        "repository": repo,
        "revision": rev,
        "packet_id": job["packet_id"],
        "packet_content_fingerprint": job["packet_content_fingerprint"],
        "scope_notice": "This supplements, never mutates, the immutable Research Packet.",
        "sources": rows,
    }
    bytes_manifest = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    if dest.exists():
        if not dest.is_dir() or (dest / "manifest.json").read_bytes() != bytes_manifest:
            raise FileExistsError("Supplement ID collision or content change; refusing overwrite")
        for filename, raw in texts:
            if (dest / "files" / filename).read_bytes() != raw:
                raise RuntimeError("Stored supplement hash mismatch")
        action = "reused"
    else:
        tmp = cfg.research_root / ".supplement-staging" / (job["job_id"] + "-" + uuid.uuid4().hex[:10])
        (tmp / "files").mkdir(parents=True, exist_ok=False)
        try:
            for filename, raw in texts:
                (tmp / "files" / filename).write_bytes(raw)
            (tmp / "manifest.json").write_bytes(bytes_manifest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                raise FileExistsError("Supplement created concurrently; refuse overwrite")
            tmp.replace(dest)
        except Exception:
            # Only remove staging created by this invocation, never any existing
            # supplement or immutable Packet.
            import shutil
            if tmp.exists():
                shutil.rmtree(tmp)
            raise
        action = "archived"
    return {
        "status": action, "manifest": str(dest / "manifest.json"),
        "supplement_id": repo + "@" + rev + ":" + path_hash,
        "source_count": len(rows),
        "sources": [{"id": r["source_id"], "path": r["path"], "sha256": r["sha256"]} for r in rows],
        "immutable_packet_unchanged": True,
    }


if __name__ == "__main__":
    try:
        if len(sys.argv) < 3:
            raise ValueError("Usage: collect_pinned_supplement.py <job-dir> <path> [path...]")
        print(json.dumps(capture(Path(sys.argv[1]), sys.argv[2:]), ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError, KeyError) as e:
        print("PINNED_SUPPLEMENT_BLOCKED: " + str(e), file=sys.stderr)
        raise SystemExit(2)
