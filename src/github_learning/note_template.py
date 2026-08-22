from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MANAGED_START = "<!-- GITHUB_NOTE_MANAGED_START -->"
MANAGED_END = "<!-- GITHUB_NOTE_MANAGED_END -->"
DEFAULT_USER_TAIL = "## 我的记录\n\n<!-- 此处及其后的个人内容会在 refresh 时保留。 -->\n"
_REPO_LINE_RE = re.compile(r"^repo:\s*(.+?)\s*$", re.MULTILINE)


def safe_title(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]', "", value).strip().rstrip(".")
    return value or "GitHub 项目笔记"


def unique_note_path(root: Path, title: str) -> Path:
    stem = safe_title(title)
    candidate = root / f"{stem}.md"
    index = 2
    while candidate.exists():
        candidate = root / f"{stem}（{index}）.md"
        index += 1
    return candidate


def _yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _yaml_list(values: list[str]) -> str:
    return "\n".join(f"  - {_yaml_scalar(value)}" for value in values)


def _section(title: str, value: str | list[str] | None) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
        if not items:
            return ""
        body = "\n".join(f"- {x}" for x in items)
    else:
        body = str(value).strip()
        if not body:
            return ""
    return f"## {title}\n\n{body}\n"


def _callout_list(kind: str, title: str, values: list[str] | None) -> str:
    items = [str(x).strip() for x in values or [] if str(x).strip()]
    if not items:
        return ""
    lines = [f"> [!{kind}] {title}"]
    for item in items:
        normalized = " ".join(item.splitlines()).strip()
        lines.append(f"> - {normalized}")
    return "\n".join(lines)


def repository_identity_from_text(text: str) -> str | None:
    match = _REPO_LINE_RE.search(text[:12000])
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw.strip('"\'')
    value = str(value).strip()
    return value or None


def repository_identity_from_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    return repository_identity_from_text(text)


def find_notes_by_repository(root: Path, full_name: str) -> list[Path]:
    if not root.is_dir():
        return []
    target = full_name.casefold()
    matches: list[Path] = []
    for path in root.rglob("*.md"):
        identity = repository_identity_from_file(path)
        if identity and identity.casefold() == target:
            matches.append(path)
    return sorted(matches)


def new_repository_note_path(root: Path, name: str, owner: str, full_name: str, *, force_new: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    primary = root / f"{safe_title(name)}.md"
    if not primary.exists():
        return primary

    primary_identity = repository_identity_from_file(primary)
    if force_new and primary_identity and primary_identity.casefold() == full_name.casefold():
        return unique_note_path(root, name)

    owner_title = f"{name} · {owner}"
    return unique_note_path(root, owner_title)


def has_managed_region(text: str) -> bool:
    return MANAGED_START in text and MANAGED_END in text and text.index(MANAGED_START) < text.index(MANAGED_END)


def extract_preserved_tail(text: str) -> str | None:
    if not has_managed_region(text):
        return None
    tail = text.split(MANAGED_END, 1)[1].lstrip("\r\n")
    return tail.rstrip() + "\n" if tail.strip() else DEFAULT_USER_TAIL


def render_note(job: dict[str, Any], analysis: dict[str, Any], *, preserved_tail: str | None = None) -> str:
    repo = job["repository"]
    semantic_tags = [str(x).strip().lstrip("#") for x in analysis.get("tags", []) if str(x).strip()]
    tags: list[str] = []
    for tag in ["GitHub", *semantic_tags]:
        if tag and tag not in tags:
            tags.append(tag)
    tags = tags[:6]
    license_name = ((repo.get("license") or {}).get("spdx_id") or "").strip()
    language = str(repo.get("language") or "").strip()
    meta = [repo["full_name"]]
    if language:
        meta.append(language)
    if license_name and license_name != "NOASSERTION":
        meta.append(license_name)

    updated = str(job.get("collected_local_date") or job["collected_at"][:10])
    parts = [
        "---",
        f"repo: {_yaml_scalar(str(repo['full_name']))}",
        f"source: {_yaml_scalar(str(repo['html_url']))}",
        f"updated: {_yaml_scalar(updated)}",
        "tags:",
        _yaml_list(tags),
        "cssclasses:",
        "  - learning-page",
        "  - github-note",
        "---",
        "",
        MANAGED_START,
        "",
        f"# {repo['name']}",
        "",
        f"<small class=\"github-note-meta\">{' · '.join(meta)}</small>",
        "",
        "> [!summary] 先看结论",
        "> " + str(analysis["summary"]).strip().replace("\n", "\n> "),
        "",
    ]
    for title, key in [
        ("它是什么", "what_it_is"),
        ("能做什么", "capabilities"),
        ("适合什么场景", "use_cases"),
    ]:
        block = _section(title, analysis.get(key))
        if block:
            parts.extend([block.rstrip(), ""])

    how_to: list[str] = []
    for sub, key in [("安装", "install"), ("基本使用", "usage"), ("关键配置", "configuration")]:
        value = str(analysis.get(key) or "").strip()
        if value:
            how_to.extend([f"### {sub}", "", value, ""])
    if how_to:
        parts.extend(["## 如何使用", "", *how_to])

    conflicts = _callout_list("risk", "官方资料存在冲突", analysis.get("source_conflicts"))
    if conflicts:
        parts.extend([conflicts, ""])

    caveats = _section("注意事项", analysis.get("caveats"))
    if caveats:
        parts.extend([caveats.rstrip(), ""])

    parts.extend(["## 仓库资料", "", f"- [GitHub 仓库]({repo['html_url']})"])
    homepage = str(repo.get("homepage") or "").strip()
    if homepage:
        parts.append(f"- [项目主页 / 文档]({homepage})")
    release = job.get("latest_release") or {}
    if release.get("html_url") and release.get("tag_name"):
        parts.append(f"- [Latest Release · {release['tag_name']}]({release['html_url']})")

    warnings = _callout_list("meta", "采集覆盖提醒", job.get("collection_warnings"))
    if warnings:
        parts.extend(["", warnings])

    parts.extend(
        [
            "",
            "> [!meta] 来源边界",
            "> 本笔记只根据本次采集到的 GitHub 官方仓库资料整理；未在来源中明确出现的版本、路径、兼容性或安装步骤不自行补全。",
            "",
            MANAGED_END,
            "",
        ]
    )
    tail = preserved_tail if preserved_tail is not None else DEFAULT_USER_TAIL
    parts.append(tail.rstrip())
    return "\n".join(parts).rstrip() + "\n"
