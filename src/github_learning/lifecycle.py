from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .github_client import SourceBundle
from .input_resolver import ResolvedRepository
from .note_template import (
    extract_preserved_tail,
    find_notes_by_repository,
    has_managed_region,
    new_repository_note_path,
    render_note,
)


def preflight_publish(
    settings: Settings,
    full_name: str,
    *,
    publish_mode: str = "upsert",
    replace_legacy: bool = False,
) -> dict[str, Any]:
    if settings.notes_is_fallback:
        return {
            "status": "configuration_required",
            "message": "尚未显式配置笔记保存位置，拒绝创建采集任务。",
            "local_config": str(settings.local_config_path),
        }
    if publish_mode not in {"upsert", "new"}:
        raise ValueError(f"不支持的 publish_mode：{publish_mode}")
    if publish_mode == "new":
        return {"status": "ready", "operation": "create_new", "repository": full_name}

    matches = find_notes_by_repository(settings.notes_root, full_name)
    if len(matches) > 1:
        return {
            "status": "duplicate_repository_notes",
            "message": "同一 repository identity 找到多篇笔记，采集已停止，请先人工确认。",
            "repository": full_name,
            "matches": [str(path) for path in matches],
        }
    if not matches:
        return {"status": "ready", "operation": "create", "repository": full_name}

    path = matches[0]
    existing = path.read_text(encoding="utf-8")
    if not has_managed_region(existing) and not replace_legacy:
        return {
            "status": "legacy_note_refresh_blocked",
            "message": "现有笔记来自旧版或缺少 managed marker。为避免覆盖人工编辑，本次未开始采集。",
            "repository": full_name,
            "note_path": str(path),
            "next_action": "确认允许迁移后，重新 prepare 并显式使用 --replace-legacy；finalize 会先保存完整备份。",
        }
    return {
        "status": "ready",
        "operation": "replace_legacy" if not has_managed_region(existing) else "refresh",
        "repository": full_name,
        "note_path": str(path),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def _source_bundle_markdown(resolved: ResolvedRepository, bundle: SourceBundle) -> str:
    repo = bundle.repository
    lines = [
        f"# Source Bundle · {resolved.full_name}",
        "",
        "## Repository metadata",
        "",
        f"- Description: {repo.get('description') or ''}",
        f"- Topics: {', '.join(repo.get('topics') or [])}",
        f"- Language: {repo.get('language') or ''}",
        f"- License: {((repo.get('license') or {}).get('spdx_id') or '')}",
        f"- Homepage: {repo.get('homepage') or ''}",
        f"- Default branch: {repo.get('default_branch') or ''}",
        "",
        "## Root files",
        "",
    ]
    lines.extend(f"- {item.get('type')}: {item.get('name')}" for item in bundle.root_entries)
    lines.extend(["", "## README", "", bundle.readme.strip() or "(README unavailable)"])
    if bundle.manifests:
        lines.extend(["", "## Installation / package manifests"])
        for name, content in bundle.manifests.items():
            lines.extend(["", f"### {name}", "", "```text", content.strip(), "```"])
    if bundle.latest_release:
        lines.extend(
            [
                "",
                "## Latest Release",
                "",
                f"- Tag: {bundle.latest_release.get('tag_name') or ''}",
                f"- Name: {bundle.latest_release.get('name') or ''}",
                f"- Published: {bundle.latest_release.get('published_at') or ''}",
                f"- URL: {bundle.latest_release.get('html_url') or ''}",
            ]
        )
    if bundle.warnings:
        lines.extend(["", "## Collection warnings", ""])
        lines.extend(f"- {warning}" for warning in bundle.warnings)
    return "\n".join(lines).rstrip() + "\n"


def prepare_job(
    settings: Settings,
    resolved: ResolvedRepository,
    bundle: SourceBundle,
    *,
    publish_mode: str = "upsert",
    replace_legacy: bool = False,
) -> dict[str, Any]:
    preflight = preflight_publish(
        settings,
        resolved.full_name,
        publish_mode=publish_mode,
        replace_legacy=replace_legacy,
    )
    if preflight["status"] != "ready":
        return preflight

    job_id = f"{resolved.owner}__{resolved.repo}__{uuid.uuid4().hex[:8]}"
    job_dir = settings.runtime_root / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    repo = bundle.repository
    job = {
        "version": 3,
        "job_id": job_id,
        "publish_mode": publish_mode,
        "publish_operation": preflight["operation"],
        "replace_legacy_authorized": replace_legacy,
        "target_note": preflight.get("note_path", ""),
        "collected_at": _now(),
        "collected_local_date": _local_date(),
        "repository": {
            "name": repo.get("name") or resolved.repo,
            "full_name": repo.get("full_name") or resolved.full_name,
            "html_url": repo.get("html_url") or resolved.canonical_url,
            "description": repo.get("description") or "",
            "homepage": repo.get("homepage") or "",
            "language": repo.get("language") or "",
            "topics": repo.get("topics") or [],
            "license": repo.get("license") or {},
            "default_branch": repo.get("default_branch") or "",
        },
        "latest_release": {
            "tag_name": (bundle.latest_release or {}).get("tag_name") or "",
            "html_url": (bundle.latest_release or {}).get("html_url") or "",
            "published_at": (bundle.latest_release or {}).get("published_at") or "",
        },
        "collection_warnings": list(bundle.warnings),
    }
    analysis = {
        "source_status": "pending",
        "source_notes": "",
        "summary": "",
        "what_it_is": "",
        "capabilities": [],
        "use_cases": [],
        "install": "",
        "usage": "",
        "configuration": "",
        "source_conflicts": [],
        "caveats": [],
        "tags": [],
        "coverage_review": {"status": "pending", "notes": ""},
    }
    handoff = f"""# Agent Handoff · {resolved.full_name}

只基于 `source_bundle.md` 填写 `analysis.json`，不要使用模型记忆补全仓库事实。

目标不是复述 README，而是让读者快速回答：

1. 这个仓库是什么？
2. 它能干嘛、解决什么问题？
3. 适合什么场景？
4. 官方资料明确写了怎样安装和使用？
5. 有哪些重要注意事项？
6. 官方资料之间是否存在互相矛盾的版本、许可证、安装或状态说明？
7. 应给 3-5 个什么知识标签？

规则：

- `source_status`：资料足够支持可信笔记时填 `sufficient`；README 极少或关键信息缺失时填 `insufficient` 并说明原因。
- `summary`：1-3 句，适合 30 秒速读。
- `capabilities` / `use_cases` / `caveats`：只保留有长期检索价值的条目。
- `install` / `usage` / `configuration`：优先整理官方推荐的最短用户路径；来源没写就留空，禁止猜命令、版本、路径。
- `source_conflicts`：只记录当前官方来源之间明确存在的冲突；如 README 两处说法不一致，保留冲突事实，不替维护者裁决。没有冲突就留空。
- `tags`：3-5 个中文或常用技术标签；不要直接复制一长串 GitHub Topics。
- `Collection warnings` 代表采集覆盖不完整，不等于仓库本身有冲突；写作时不要把“没采到”误写成“不存在”。
- 最后重新对照来源复核是否遗漏关键用途、安装方式、限制或资源，并把 `coverage_review.status` 设为 `passed`。
"""
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (job_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (job_dir / "source_bundle.md").write_text(_source_bundle_markdown(resolved, bundle), encoding="utf-8")
    (job_dir / "agent_handoff.md").write_text(handoff, encoding="utf-8")
    return {
        "status": "analysis_required",
        "job_id": job_id,
        "job_dir": str(job_dir),
        "publish_mode": publish_mode,
        "analysis_path": str(job_dir / "analysis.json"),
        "handoff_path": str(job_dir / "agent_handoff.md"),
    }


def _validate_analysis(analysis: dict[str, Any]) -> None:
    if analysis.get("source_status") != "sufficient":
        raise ValueError("来源尚未被 Agent 判定为 sufficient，拒绝发布。")
    if not str(analysis.get("summary") or "").strip():
        raise ValueError("analysis.summary 为空。")
    if not str(analysis.get("what_it_is") or "").strip():
        raise ValueError("analysis.what_it_is 为空。")
    if not analysis.get("capabilities"):
        raise ValueError("analysis.capabilities 为空。")
    review = analysis.get("coverage_review") or {}
    if review.get("status") != "passed":
        raise ValueError("coverage_review 尚未通过。")
    tags = analysis.get("tags") or []
    if not 2 <= len(tags) <= 5:
        raise ValueError("analysis.tags 建议保持 2-5 个；程序会额外加入 GitHub 标签。")


def _write_note_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(path)


def finalize_job(settings: Settings, job_dir: Path, *, replace_legacy: bool = False) -> dict[str, Any]:
    if settings.notes_is_fallback:
        return {
            "status": "configuration_required",
            "message": "尚未显式配置笔记保存位置，拒绝发布。",
            "local_config": str(settings.local_config_path),
        }
    job_dir = job_dir.resolve()
    runtime_root = settings.runtime_root.resolve()
    if runtime_root not in job_dir.parents:
        raise ValueError("只允许 finalize 当前项目 .runtime/github-learning 下的 job。")

    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    analysis = json.loads((job_dir / "analysis.json").read_text(encoding="utf-8"))
    source_status = str(analysis.get("source_status") or "pending")
    if source_status == "pending":
        return {
            "status": "analysis_required",
            "message": "Agent 尚未完成来源充分性判断。",
            "job_dir": str(job_dir),
        }
    if source_status == "insufficient":
        return {
            "status": "source_insufficient",
            "reason": str(analysis.get("source_notes") or "官方资料不足，未生成笔记。"),
            "runtime_status": "retained_for_audit",
            "job_dir": str(job_dir),
        }
    if source_status != "sufficient":
        raise ValueError(f"不支持的 source_status：{source_status}")
    _validate_analysis(analysis)

    repo = job["repository"]
    full_name = str(repo["full_name"])
    owner, _repo_name = full_name.split("/", 1)
    publish_mode = str(job.get("publish_mode") or "upsert")
    matches = find_notes_by_repository(settings.notes_root, full_name)

    if publish_mode == "upsert" and len(matches) > 1:
        return {
            "status": "duplicate_repository_notes",
            "message": "同一 repository identity 找到多篇笔记，自动 refresh 已停止，请先人工确认。",
            "repository": full_name,
            "matches": [str(path) for path in matches],
            "job_dir": str(job_dir),
        }

    legacy_backup_path: Path | None = None
    if publish_mode == "upsert" and len(matches) == 1:
        path = matches[0]
        existing = path.read_text(encoding="utf-8")
        if not has_managed_region(existing):
            legacy_authorized = replace_legacy or bool(job.get("replace_legacy_authorized"))
            if not legacy_authorized:
                return {
                    "status": "legacy_note_refresh_blocked",
                    "message": "现有笔记来自旧版或缺少 managed marker。为避免覆盖人工编辑，本次没有刷新。",
                    "note_path": str(path),
                    "job_dir": str(job_dir),
                    "next_action": "推荐重新 prepare 并显式使用 --replace-legacy；兼容旧 job 时也可 finalize --replace-legacy。程序会先在 runtime 保存完整备份。",
                }
            legacy_backup_path = job_dir / "legacy_note_backup.md"
            if legacy_backup_path.exists():
                raise FileExistsError(f"legacy backup 已存在，拒绝覆盖：{legacy_backup_path}")
            legacy_backup_path.write_text(existing, encoding="utf-8", newline="\n")
            preserved_tail = None
        else:
            preserved_tail = extract_preserved_tail(existing)
        _write_note_atomic(path, render_note(job, analysis, preserved_tail=preserved_tail))
        action = "refreshed"
    else:
        force_new = publish_mode == "new"
        path = new_repository_note_path(
            settings.notes_root,
            str(repo["name"]),
            owner,
            full_name,
            force_new=force_new,
        )
        _write_note_atomic(path, render_note(job, analysis))
        action = "created"

    result: dict[str, Any] = {
        "status": "note_ready",
        "publish_action": action,
        "repository": full_name,
        "note_path": str(path),
        "runtime_status": "retained_for_audit",
        "job_dir": str(job_dir),
    }
    if legacy_backup_path is not None:
        result["legacy_backup_path"] = str(legacy_backup_path)
    return result
