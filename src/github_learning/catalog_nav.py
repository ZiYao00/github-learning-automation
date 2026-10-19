"""Derived catalog views and independently recoverable index publication.

Capture Notes remain the archive authority. Catalog state never proves research.
No collector calls, source execution, Packet mutation, or migration occurs here.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .catalog import (
    CATALOG_NAME, NAV_NAME, PRIORITIES, STATES, CatalogDocument, CatalogError,
    catalog_lock, checked_path, commit_bytes, normalize_repository, read_document,
    require_expected, sha256, text_cell, unified_diff,
)
from .config import Settings
from .note_template import MANAGED_END, MANAGED_START

NAV_MARKER = "<!-- GITHUB_CATALOG_NAV_V1 -->"
_FIELDS = {"repo", "source", "revision", "packet_id", "capture_status", "analysis_status"}


def mapping(settings: Settings) -> tuple[Path | None, str]:
    if settings.vault_root is None or settings.notes_subdir is None:
        return None, "not_configured"
    prefix = settings.notes_subdir
    if prefix.is_absolute() or ".." in prefix.parts or prefix == Path("."):
        return None, "mapping_mismatch"
    display = settings.vault_root / prefix
    if not display.is_dir():
        return None, "mapping_missing"
    if display.resolve() != settings.notes_root.resolve():
        return None, "mapping_mismatch"
    return prefix, "direct_vault" if display == settings.notes_root else "ok"


def note_link(settings: Settings, path: Path, *, table: bool = False, label: str = "查看笔记") -> str | None:
    prefix, _ = mapping(settings)
    if prefix is None:
        return None
    root = settings.notes_root.resolve()
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
        raise CatalogError("catalog_note_path_invalid", "笔记不在已确认的 notes_root 内或已经消失。")
    relative = path.resolve().relative_to(root)
    target = (prefix / relative.with_suffix("")).as_posix()
    if any(ch in target for ch in "[]#|^\\\r\n"):
        # WikiLink reserved characters cannot be escaped reliably. A relative,
        # percent-encoded native Markdown link safely retains the exact filename.
        return f"[{text_cell(label)}](<./{quote(relative.as_posix(), safe='/')}>)"
    separator = "\\|" if table else "|"
    return f"[[{target}{separator}{label}]]"


def _note_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    def fail(exc: OSError) -> None:
        raise CatalogError("catalog_scan_incomplete", "笔记目录无法完整扫描；不会更新完成状态。") from exc
    for current, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        base = Path(current)
        retained = []
        for directory in sorted(dirs):
            if directory.startswith(".") or directory == "_repo-data":
                continue
            child = base / directory
            if (child.is_symlink() or getattr(child, "is_junction", lambda: False)()
                    or not child.resolve().is_relative_to(root)):
                raise CatalogError("catalog_scan_incomplete", "阅读目录内存在额外链接目录，不能静默漏扫；请先核对。")
            retained.append(directory)
        dirs[:] = retained
        for name in sorted(files):
            if name in {CATALOG_NAME, NAV_NAME} or name.startswith(".") or not name.lower().endswith(".md"):
                continue
            path = base / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise CatalogError("catalog_scan_incomplete", "笔记链接指向未授权路径；请先核对。")
            paths.append(path)
    return sorted(paths)


def _scalars(text: str) -> tuple[dict[str, str], list[str]]:
    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.DOTALL)
    if not match:
        return {}, []
    result: dict[str, str] = {}
    errors = []
    for line in match.group(1).splitlines():
        field = re.match(r"^([a-z_]+):[ \t]*(.*)$", line)
        if not field or field.group(1) not in _FIELDS:
            continue
        key, raw = field.groups()
        if key in result:
            errors.append("duplicate_frontmatter:" + key)
            continue
        try:
            if raw.startswith('"'):
                value = json.loads(raw)
                if not isinstance(value, str):
                    raise ValueError("not a string")
            elif raw.startswith("'") and raw.endswith("'"):
                value = raw[1:-1].replace("''", "'")
            elif raw.startswith(("[", "{", "&", "*", "!", "|", ">")):
                raise ValueError("not a scalar")
            else:
                value = raw.split(" #", 1)[0].strip()
            result[key] = value
        except ValueError:
            errors.append("invalid_frontmatter:" + key)
            result[key] = ""
    return result, errors


@dataclass(frozen=True)
class NoteRecord:
    repository: str
    path: Path
    state: str
    reasons: tuple[str, ...] = ()


@dataclass
class NoteIndex:
    root: Path
    records: dict[str, list[NoteRecord]]
    hashes: dict[Path, str]
    ignored: list[str]

    def assert_unchanged(self) -> None:
        if set(_note_paths(self.root)) != set(self.hashes):
            raise CatalogError("catalog_sources_changed", "扫描后笔记集合发生变化；请重新预览，不自动重试。")
        for path, expected in self.hashes.items():
            try:
                actual = sha256(path.read_bytes())
            except OSError as exc:
                raise CatalogError("catalog_sources_changed", "扫描后笔记发生移动或消失。") from exc
            if actual != expected:
                raise CatalogError("catalog_sources_changed", "扫描后笔记被编辑；请重新核对。")


def scan_notes(settings: Settings) -> NoteIndex:
    root = checked_path(settings, CATALOG_NAME).parent
    index = NoteIndex(root, {}, {}, [])
    for path in _note_paths(root):
        try:
            if path.stat().st_size > 4 * 1024 * 1024:
                raise CatalogError("catalog_scan_incomplete", "存在超过 4 MiB 的笔记，需人工核对后再同步。")
            data = path.read_bytes()
            text = data.decode("utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise CatalogError("catalog_scan_incomplete", "存在不可读取或非 UTF-8 笔记，未发布不完整索引。") from exc
        index.hashes[path] = sha256(data)
        meta, reasons = _scalars(text)
        if "repo" not in meta:
            index.ignored.append(path.relative_to(root).as_posix())
            continue
        try:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", meta["repo"]):
                raise ValueError("invalid identity")
            repository = normalize_repository(meta["repo"]).full_name
        except ValueError as exc:
            raise CatalogError("catalog_note_identity_invalid", "笔记含无效 repo 字段，无法安全排除重复身份。") from exc
        revision = meta.get("revision", "")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            reasons.append("revision_missing_or_invalid")
        if meta.get("packet_id", "").casefold() != f"{repository}@{revision}".casefold():
            reasons.append("packet_identity_missing_or_mismatched")
        try:
            source = normalize_repository(meta.get("source", "")).full_name
            if source.casefold() != repository.casefold():
                reasons.append("source_identity_mismatched")
        except ValueError:
            reasons.append("source_missing_or_invalid")
        if meta.get("capture_status") != "saved":
            reasons.append("capture_status_missing_or_invalid")
        if meta.get("analysis_status") not in {"sufficient", "insufficient"}:
            reasons.append("analysis_status_missing_or_invalid")
        lines = text.splitlines()
        if (text.count(MANAGED_START) != 1 or text.count(MANAGED_END) != 1
                or MANAGED_START not in lines or MANAGED_END not in lines
                or text.index(MANAGED_START) >= text.index(MANAGED_END)):
            reasons.append("managed_region_missing_or_invalid")
        state = "legacy" if reasons else meta["analysis_status"]
        record = NoteRecord(repository, path, state, tuple(reasons))
        index.records.setdefault(repository.casefold(), []).append(record)
    return index


def _derived_entry(settings: Settings, repository: str, candidates: list[NoteRecord]) -> dict[str, Any]:
    entry: dict[str, Any] = {"repository": repository, "archive_state": "none", "complete": False,
                             "note_link": None, "table_link": None, "diagnostics": []}
    if len(candidates) > 1:
        entry["archive_state"] = "conflict"
        entry["diagnostics"].append({"code": "duplicate_repository_notes", "repository": repository,
                                     "paths": [p.path.relative_to(settings.notes_root.resolve()).as_posix() for p in candidates]})
        return entry
    if not candidates:
        return entry
    note = candidates[0]
    entry.update(archive_state=note.state, complete=note.state == "sufficient",
                 note_path=note.path.relative_to(settings.notes_root.resolve()).as_posix(),
                 note_link=note_link(settings, note.path, label="历史笔记（待核验）" if note.state == "legacy" else "查看笔记"))
    if note.state == "legacy":
        entry["diagnostics"].append({"code": "legacy_note_needs_review", "repository": repository,
                                     "path": entry["note_path"], "reasons": list(note.reasons)})
    else:
        entry["table_link"] = note_link(settings, note.path, table=True)
    return entry


def build_view(settings: Settings, doc: CatalogDocument, index: NoteIndex) -> dict[str, Any]:
    _, mapping_status = mapping(settings)
    entries = []
    changes: dict[str, dict[int, str]] = {}
    diagnostics: list[dict[str, Any]] = []
    if mapping_status not in {"direct_vault", "ok"}:
        diagnostics.append({"code": "obsidian_" + mapping_status,
                            "message": "映射未就绪，禁止写入导航或生成假链接；不自动迁移。"})
    for row in doc.rows:
        entry = _derived_entry(settings, row.repository, index.records.get(row.key, []))
        entry.update(priority=row.priority, status=row.status, description=row.cells[1], proposed_status=row.status)
        # A historical sufficient note is not proof the specifically requested
        # rework has been completed. Only an explicitly verified new publish
        # may transition this human-owned queue state.
        if row.status == "待重制":
            entry["complete"] = False
        state = entry["archive_state"]
        if row.status not in STATES:
            entry["diagnostics"].append({"code": "catalog_unknown_state", "repository": row.repository, "status": row.status})
        if row.status in {"已归档", "已实测"} and state not in {"sufficient"}:
            entry["diagnostics"].append({"code": "catalog_status_conflict", "repository": row.repository,
                                         "message": "人工状态已保留，但没有可证实完整研究的唯一正式笔记。"})
        if not entry["diagnostics"] and state in {"sufficient", "insufficient"}:
            next_status = row.status if row.status in {"暂缓", "已实测", "待重制"} else ("已归档" if state == "sufficient" else "待补研究")
            entry["proposed_status"] = next_status
            update: dict[int, str] = {}
            if next_status != row.status:
                update[3] = next_status
            link = entry["table_link"]
            if link and link != row.cells[4]:
                current = row.cells[4]
                if current in {"—", "-"} or re.fullmatch(r"\[\[.+\]\]|\[[^\]]+\]\(<[^>]+>\)", current):
                    update[4] = link
                else:
                    entry["diagnostics"].append({"code": "catalog_link_has_manual_content", "repository": row.repository,
                                                 "message": "正式笔记列含人工文字，未覆盖。"})
                    update = {}
            if update and mapping_status in {"direct_vault", "ok"}:
                changes[row.key] = update
        diagnostics.extend(entry["diagnostics"])
        entries.append(entry)
    keys = {row.key for row in doc.rows}
    unlisted = []
    for key, candidates in sorted(index.records.items()):
        if key not in keys:
            entry = _derived_entry(settings, candidates[0].repository, candidates)
            unlisted.append(entry)
            diagnostics.extend(entry["diagnostics"])
    counts = {"catalog_total": len(entries), "catalog_sufficient": sum(e["complete"] for e in entries),
              "catalog_minimal": sum(e["archive_state"] == "insufficient" for e in entries),
              "catalog_deferred": sum(e["status"] == "暂缓" for e in entries),
              "catalog_rework_pending": sum(e["status"] == "待重制" for e in entries),
              "unlisted_formal": sum(e["archive_state"] in {"sufficient", "insufficient"} for e in unlisted),
              "unlisted_legacy": sum(e["archive_state"] == "legacy" for e in unlisted),
              "ignored_nonformal": len(index.ignored)}
    return {"entries": entries, "unlisted": unlisted, "counts": counts,
            "recorded_states": dict(Counter(row.status for row in doc.rows)),
            "mapping": mapping_status, "can_write": mapping_status in {"direct_vault", "ok"},
            "diagnostics": diagnostics, "changes": changes, "ignored_notes": index.ignored}


def inspect_catalog(settings: Settings) -> dict[str, Any]:
    doc, digest = read_document(settings)
    view = build_view(settings, doc, scan_notes(settings))
    return {"status": "catalog_ready", "catalog_sha256": digest, **view, "network_used": False}


def render_navigation(settings: Settings, view: dict[str, Any]) -> bytes:
    catalog = note_link(settings, checked_path(settings, CATALOG_NAME), label="收藏清单与重点推荐") or CATALOG_NAME
    counts = view["counts"]
    lines = [NAV_MARKER, "# GitHub 导航", "",
             "> 自动生成：请在收藏清单维护原因、优先级和暂缓状态，不在本页手动勾选。",
             "> 完成勾只表示已核验的充分研究，不表示安装或实测；Minimal Note 仍需补研究。",
             "> 待重制表示已有旧稿但本轮尚未验收新版，不能凭旧稿的 sufficient 自动勾选。", "",
             catalog, "",
             f"收藏 **{counts['catalog_total']}** 项 · 已核验充分研究 **{counts['catalog_sufficient']}** 项 · "
             f"待补研究 **{counts['catalog_minimal']}** 项 · 待重制 **{counts['catalog_rework_pending']}** 项 · "
             f"暂缓 **{counts['catalog_deferred']}** 项", ""]
    groups: dict[str, list[dict[str, Any]]] = {name: [] for name in ["待研究", "待重制", "待补研究", "已归档 / 已实测", "暂缓", "收藏中的待核对项"]}
    for entry in view["entries"]:
        if entry["status"] == "待重制":
            group = "待重制"
        elif entry["diagnostics"]:
            group = "收藏中的待核对项"
        elif entry["status"] == "暂缓":
            group = "暂缓"
        elif entry["complete"]:
            group = "已归档 / 已实测"
        elif entry["archive_state"] == "insufficient":
            group = "待补研究"
        else:
            group = "待研究"
        groups[group].append(entry)
    for title, items in groups.items():
        lines.extend([f"## {title}（{len(items)}）", ""])
        if not items:
            lines.extend(["暂无。", ""])
            continue
        items = sorted(items, key=lambda e: PRIORITIES.index(e["priority"]) if e["priority"] in PRIORITIES else 3)
        for entry in items:
            repo = entry["repository"]
            link = f" · {entry['note_link']}" if entry["note_link"] else ""
            lines.append(f"- [{'x' if entry['complete'] else ' '}] [{repo}](https://github.com/{repo}) · {text_cell(entry['priority'])}{link}")
            # Existing editorial prose is retained in its source table; navigation
            # treats it as text rather than reactivating arbitrary Markdown/HTML.
            prose = re.sub(r"\\([\\`\[\]*_|!])", r"\1", entry["description"])
            lines.append("  " + text_cell(prose))
        lines.append("")
    formal = [e for e in view["unlisted"] if e["archive_state"] in {"sufficient", "insufficient"}]
    legacy = [e for e in view["unlisted"] if e["archive_state"] not in {"sufficient", "insufficient"}]
    for title, items in [("已有正式笔记 · 未列入收藏清单", formal), ("历史笔记 / 身份冲突 · 待核验", legacy)]:
        lines.extend([f"## {title}（{len(items)}）", ""])
        if not items:
            lines.extend(["暂无。", ""])
        for entry in items:
            link = f" · {entry['note_link']}" if entry["note_link"] else ""
            state = "充分研究" if entry["complete"] else ("待补研究" if entry["archive_state"] == "insufficient" else "待核验")
            lines.append(f"- [{'x' if entry['complete'] else ' '}] {entry['repository']} · {state}{link}")
        lines.append("")
    if view["diagnostics"]:
        lines.extend(["## 核对提示", ""])
        for item in view["diagnostics"]:
            label = item.get("repository", "索引")
            code = item["code"]
            detail = item.get("message") or ("历史字段或结构不完整，未自动标记完成。" if code == "legacy_note_needs_review" else "请先检查冲突，不自动关联。")
            lines.append(f"- {text_cell(label)}：{text_cell(detail)}")
        lines.append("")
    lines.extend(["## 更新方式", "",
                  "正式研究仍走原有流程；收藏不会自动研究所有仓库。发布后的索引同步失败时，先预览再补齐：", "",
                  "```powershell", "python scripts/github_learning.py catalog reconcile --dry-run",
                  "python scripts/github_learning.py catalog reconcile", "```", "",
                  "未带有效仓库身份的预览不参与完成判定。导航可重建，正式笔记与 Research Packet 不会因此重写。", ""])
    return "\n".join(lines).encode("utf-8")


def _navigation_before(settings: Settings) -> tuple[Path, bytes, str | None]:
    path = checked_path(settings, NAV_NAME)
    if not path.exists():
        return path, b"", None
    data = path.read_bytes()
    if not data.decode("utf-8-sig").splitlines() or data.decode("utf-8-sig").splitlines()[0] != NAV_MARKER:
        raise CatalogError("catalog_navigation_unowned", "同名导航不是本工具生成，未覆盖。")
    return path, data, sha256(data)


def navigation(settings: Settings, *, dry_run: bool = False, expected_sha: str | None = None,
               expected_nav_sha: str | None = None) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        doc, digest = read_document(settings)
        require_expected(digest, expected_sha)
        index = scan_notes(settings)
        view = build_view(settings, doc, index)
        target, before, old_sha = _navigation_before(settings)
        require_expected(old_sha, expected_nav_sha)
        output = render_navigation(settings, view)
        result = {"status": "catalog_preview" if dry_run else "no_change", "dry_run": dry_run,
                  "catalog_sha256": digest, "navigation_sha256": old_sha,
                  "proposed_navigation_sha256": sha256(output), "written": False, **view}
        if dry_run:
            result.update(preview=output.decode("utf-8"), diff=unified_diff(before, output, NAV_NAME))
            return result
        if not view["can_write"]:
            raise CatalogError("catalog_mapping_not_ready", "Obsidian 映射未就绪，未写入导航。")
        index.assert_unchanged()
        require_expected(sha256(checked_path(settings, CATALOG_NAME).read_bytes()), digest)
        result["written"] = commit_bytes(target, output, old_sha)
        result["status"] = "catalog_navigation_written" if result["written"] else "no_change"
        result["navigation_sha256"] = sha256(output)
        return result
    if dry_run:
        return run()
    with catalog_lock(settings):
        return run()


def _validate_publication(index: NoteIndex, result: dict[str, Any]) -> None:
    """Even no_change must be tied to the actual, unique, validated target note."""
    value = result.get("note_path")
    if not isinstance(value, str) or not value:
        raise CatalogError("catalog_publication_unverified", "发布结果缺少实际笔记路径，未猜测或同步。")
    path = Path(value).resolve()
    if not path.is_relative_to(index.root) or path not in index.hashes:
        raise CatalogError("catalog_publication_unverified", "发布目标未在当前笔记目录找到。")
    records = [record for items in index.records.values() for record in items if record.path == path]
    if len(records) != 1 or records[0].state not in {"sufficient", "insufficient"}:
        raise CatalogError("catalog_publication_unverified", "发布目标不是结构有效的正式笔记。")
    record = records[0]
    if len(index.records[record.repository.casefold()]) != 1:
        raise CatalogError("duplicate_repository_notes", "发布后发现同仓库多篇笔记，未自动同步。")
    repository = result.get("repository")
    if repository and (not isinstance(repository, str) or repository.casefold() != record.repository.casefold()):
        raise CatalogError("catalog_publication_unverified", "发布结果和实际笔记的仓库身份不一致。")
    if result.get("analysis_status") and result["analysis_status"] != record.state:
        raise CatalogError("catalog_publication_unverified", "发布结果和实际笔记的分析状态不一致。")
    if result.get("note_sha256") and result["note_sha256"] != index.hashes[path]:
        raise CatalogError("catalog_sources_changed", "正式发布后笔记已发生变化；原发布结果保留，索引需重新核对。")


def reconcile(settings: Settings, *, dry_run: bool = False, expected_sha: str | None = None,
              expected_nav_sha: str | None = None,
              published_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Commit catalog then navigation, with visible partial failure and safe replay.

    This is deliberately NOT a transaction with the original note publication.
    Never acquire a repository publication lock while holding the catalog lock.
    """
    def run() -> dict[str, Any]:
        doc, old_sha = read_document(settings)
        require_expected(old_sha, expected_sha)
        index = scan_notes(settings)
        if published_result is not None:
            _validate_publication(index, published_result)
        view = build_view(settings, doc, index)
        nav_target, nav_before, old_nav_sha = _navigation_before(settings)
        require_expected(old_nav_sha, expected_nav_sha)
        output = doc.updated(view["changes"])
        after_doc = CatalogDocument.parse(output)
        after_view = build_view(settings, after_doc, index)
        nav_output = render_navigation(settings, after_view)
        result = {"status": "catalog_preview" if dry_run else "no_change", "dry_run": dry_run,
                  "can_write": view["can_write"], "mapping": view["mapping"],
                  "catalog_sha256": old_sha, "proposed_catalog_sha256": sha256(output),
                  "navigation_sha256": old_nav_sha, "proposed_navigation_sha256": sha256(nav_output),
                  "changes": view["changes"], "counts": after_view["counts"],
                  "diagnostics": view["diagnostics"], "catalog_written": False, "navigation_written": False,
                  "catalog_write_attempted": False, "navigation_write_attempted": False,
                  "index_sync_success": None, "network_used": False}
        if dry_run:
            result["catalog_diff"] = unified_diff(doc.raw, output, CATALOG_NAME)
            result["navigation_diff"] = unified_diff(nav_before, nav_output, NAV_NAME)
            return result
        if not view["can_write"]:
            raise CatalogError("catalog_mapping_not_ready", "映射未就绪，未回写清单或导航。")
        target = checked_path(settings, CATALOG_NAME)
        index.assert_unchanged()
        try:
            result["catalog_write_attempted"] = output != doc.raw
            result["catalog_written"] = commit_bytes(target, output, old_sha)
            result["catalog_sha256"] = sha256(output)
            # Notes can change after the first write. Do not publish a misleading
            # navigation snapshot; leave the partial result visible for reconcile.
            index.assert_unchanged()
            require_expected(sha256(target.read_bytes()), sha256(output))
            result["navigation_write_attempted"] = nav_before != nav_output
            result["navigation_written"] = commit_bytes(nav_target, nav_output, old_nav_sha)
            result["navigation_sha256"] = sha256(nav_output)
        except Exception as exc:
            result.update(status="index_sync_failed", index_sync_success=False,
                          error_code=getattr(exc, "code", "index_write_failed"), error=str(exc),
                          recovery="python scripts/github_learning.py catalog reconcile --dry-run")
            return result
        result["index_sync_success"] = True
        if result["catalog_written"] or result["navigation_written"]:
            result["status"] = "catalog_reconciled"
        return result
    if dry_run:
        return run()
    with catalog_lock(settings):
        return run()


def postprocess_catalog(settings: Settings, result: dict[str, Any]) -> dict[str, Any]:
    """CLI-only optional postprocessing, after the original publish lock is released.

    Preserve all original result fields and the original CLI success semantics.
    Absence of a catalog keeps legacy workflows byte-for-byte protocol compatible.
    """
    if result.get("status") not in {"note_ready", "no_change"}:
        return result
    try:
        if not (settings.notes_root / CATALOG_NAME).exists():
            return result
        synced = reconcile(settings, published_result=result)
        detail = {k: synced[k] for k in ("status", "index_sync_success", "catalog_written", "navigation_written", "diagnostics")}
        detail["publish_success"] = True
        if not detail["index_sync_success"]:
            detail.update(error_code=synced.get("error_code"), error=synced.get("error"), recovery=synced.get("recovery"))
    except Exception as exc:
        detail = {"status": "index_sync_failed", "publish_success": True, "index_sync_success": False,
                  "error_code": getattr(exc, "code", "index_sync_failed"), "error": str(exc),
                  "recovery": "python scripts/github_learning.py catalog reconcile --dry-run"}
    return {**result, "catalog_sync": detail}
