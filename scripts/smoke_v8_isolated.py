"""Opt-in real GitHub Job-v8 release smoke isolated from the user's Vault.

Run from the repository root:
  py -3.12 scripts/smoke_v8_isolated.py prepare
  # An Agent reads the pinned Job sources and fills analysis.json.
  py -3.12 scripts/smoke_v8_isolated.py finalize <job_dir>
  py -3.12 scripts/smoke_v8_isolated.py verify <job_dir>

Only a public GitHub repository is fetched; no target code or dependencies run.
All generated data stays inside ignored .runtime/closeout-v8, never Obsidian.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from github_learning.auth import resolve_github_auth
from github_learning.config import Settings
from github_learning.github_client import fetch_repository_sources
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import finalize_job, prepare_job
from github_learning.note_template import capture_metadata_from_file, find_notes_by_repository
from github_learning.research_packet import packet_path, validate_packet


BOUNDARY = (ROOT / ".runtime" / "closeout-v8").resolve()
PUBLIC_REPO = "psf/requests"


def settings_for(run: Path) -> Settings:
    if BOUNDARY not in run.resolve().parents:
        raise ValueError("Smoke run must be inside the ignored closeout-v8 boundary")
    notes = run / "notes"
    research = run / "research"
    runtime = run / "runtime"
    for folder in (notes, research, runtime):
        folder.mkdir(parents=True, exist_ok=True)
    return Settings(
        project_root=ROOT,
        notes_root=notes,
        runtime_root=runtime,
        local_config_path=ROOT / "config" / "local.json",
        notes_is_fallback=False,
        notes_source="test_isolated",
        research_root=research,
        research_source="test_isolated",
        research_is_fallback=False,
    )


def prepare() -> dict:
    run = BOUNDARY / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    run.mkdir(parents=True, exist_ok=False)
    cfg = settings_for(run)
    resolved = resolve_repository(PUBLIC_REPO)
    bundle = fetch_repository_sources(resolved.full_name, resolve_github_auth())
    if bundle.repository.get("private") or not bundle.revision:
        raise ValueError("Unexpected private/unpinned public repository response")
    result = prepare_job(cfg, resolved, bundle)
    if result.get("status") != "analysis_required" or not Path(result["packet_path"]).is_dir():
        raise ValueError("Could not prepare archived V8 job: " + str(result.get("status")))
    job = json.loads((Path(result["job_dir"]) / "job.json").read_text(encoding="utf-8"))
    if job.get("version") != 8 or job.get("editorial_contract_version") != "2.2":
        raise ValueError("Unexpected Job version or editorial contract")
    validate_packet(Path(result["packet_path"]))
    return {**result, "isolated_run_root": str(run), "not_user_vault": True}


def _job_and_settings(job_dir_arg: str) -> tuple[Settings, Path, dict]:
    job_dir = Path(job_dir_arg).resolve()
    run = job_dir.parent.parent
    if run.parent.resolve() != BOUNDARY or job_dir.parent.name != "runtime":
        raise ValueError("Refuse to access a Job outside the isolated smoke runtime")
    cfg = settings_for(run)
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    if (job.get("version") != 8
            or (job.get("repository") or {}).get("full_name") != PUBLIC_REPO):
        raise ValueError("Smoke Job identity or version mismatch")
    return cfg, job_dir, job


def finalize(job_dir_arg: str) -> dict:
    cfg, job_dir, _ = _job_and_settings(job_dir_arg)
    return finalize_job(cfg, job_dir)


def verify(job_dir_arg: str) -> dict:
    cfg, job_dir, job = _job_and_settings(job_dir_arg)
    if job.get("state") != "published":
        raise ValueError("Job not successfully published")
    result = job.get("final_result") or {}
    if result.get("status") != "note_ready":
        raise ValueError("Missing note_ready result")
    notes = find_notes_by_repository(cfg.notes_root, PUBLIC_REPO)
    if len(notes) != 1 or Path(result["note_path"]).resolve() != notes[0].resolve():
        raise ValueError("Missing or duplicated published note")
    meta = capture_metadata_from_file(notes[0])
    if meta.get("evidence_set_id") != job.get("evidence_set_id"):
        raise ValueError("Published evidence-set identity mismatch")
    validate_packet(Path(job["packet_path"]))
    existing = finalize_job(cfg, job_dir)
    if existing.get("status") != "note_ready" or not existing.get("idempotent"):
        raise ValueError("Idempotent finalization check failed")
    resolved = resolve_repository(PUBLIC_REPO)
    auth = resolve_github_auth()
    bundle = fetch_repository_sources(
        PUBLIC_REPO, auth,
        pinned_packet_loader=lambda revision: (
            validate_packet(packet_path(cfg.research_root, PUBLIC_REPO, revision))
            if packet_path(cfg.research_root, PUBLIC_REPO, revision).is_dir() else None
        ),
    )
    if bundle.revision != job.get("revision"):
        raise ValueError("Public branch HEAD changed mid-smoke; repeat at a stable revision")
    repeated = prepare_job(cfg, resolved, bundle)
    if repeated.get("status") != "no_change":
        raise ValueError("Expected v8 no_change, got " + str(repeated.get("status")))
    return {
        "status": "passed", "repository": PUBLIC_REPO,
        "revision": bundle.revision,
        "job_version": 8, "editorial_contract": "2.2",
        "note_path": str(notes[0]), "not_user_vault": True,
        "original_packet_unchanged": True,
        "finalize_idempotent": True, "second_prepare": "no_change",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "finalize", "verify"])
    p.add_argument("job_dir", nargs="?")
    args = p.parse_args()
    if args.action != "prepare" and not args.job_dir:
        p.error("finalize/verify requires an explicit isolated Job path")
    result = prepare() if args.action == "prepare" else (
        finalize(args.job_dir) if args.action == "finalize" else verify(args.job_dir)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") not in {"passed", "analysis_required", "note_ready"}:
        raise SystemExit(2)
