from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MANAGED_START = "<!-- GITHUB_NOTE_MANAGED_START -->"
MANAGED_END = "<!-- GITHUB_NOTE_MANAGED_END -->"
DEFAULT_USER_TAIL = "## 我的记录\n\n<!-- 此处及其后的个人内容会在 refresh 时保留。 -->\n"
_REPO_LINE_RE = re.compile(r"^repo:\s*(.+?)\s*$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


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


def _frontmatter_value(text: str, key: str) -> str | None:
    frontmatter = _FRONTMATTER_RE.match(text)
    if not frontmatter:
        return None
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(frontmatter.group("body"))
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw.strip('"\'')
    value = str(value).strip()
    return value or None


def repository_identity_from_text(text: str) -> str | None:
    return _frontmatter_value(text, "repo")


def capture_metadata_from_text(text: str) -> dict[str, str]:
    keys = (
        "repo",
        "revision",
        "packet_id",
        "content_profile",
        "capture_status",
        "analysis_status",
        "observation_fingerprint",
        "note_style",
        "editorial_contract_version",
    )
    return {
        key: value
        for key in keys
        if (value := _frontmatter_value(text, key)) is not None
    }


def capture_metadata_from_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    return capture_metadata_from_text(text)


def repository_identity_from_file(path: Path) -> str | None:
    metadata = capture_metadata_from_file(path)
    return metadata.get("repo")


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


def new_repository_note_path(
    root: Path,
    name: str,
    owner: str,
    full_name: str,
    *,
    force_new: bool = False,
) -> Path:
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


def _content_profile(job: dict[str, Any], analysis: dict[str, Any]) -> str:
    value = str(analysis.get("content_profile") or job.get("content_profile") or "").strip()
    if value:
        return value
    source_profile = str(job.get("source_profile") or "generic")
    if source_profile == "agent-skill":
        return "agent-skill"
    if source_profile in {"containerized", "node-application", "python-project"}:
        return "software"
    return "generic"


def _frontmatter(
    job: dict[str, Any],
    analysis: dict[str, Any],
    *,
    analysis_status: str,
) -> list[str]:
    repo = job["repository"]
    semantic_tags = [str(x).strip().lstrip("#") for x in analysis.get("tags", []) if str(x).strip()]
    tags: list[str] = []
    for tag in ["GitHub", *semantic_tags]:
        if tag and tag not in tags:
            tags.append(tag)
    tags = tags[:6]

    updated = str(job.get("collected_local_date") or str(job.get("collected_at") or "")[:10])
    revision = str(job.get("revision") or "").strip()
    packet = str(job.get("packet_id") or "").strip()
    observation_fingerprint = str(job.get("observation_fingerprint") or "").strip()
    profile = _content_profile(job, analysis)

    lines = [
        "---",
        f"repo: {_yaml_scalar(str(repo['full_name']))}",
        f"source: {_yaml_scalar(str(repo['html_url']))}",
        f"updated: {_yaml_scalar(updated)}",
    ]
    if revision:
        lines.append(f"revision: {_yaml_scalar(revision)}")
    if packet:
        lines.append(f"packet_id: {_yaml_scalar(packet)}")
    lines.extend(
        [
            f"content_profile: {_yaml_scalar(profile)}",
            'capture_status: "saved"',
            f"analysis_status: {_yaml_scalar(analysis_status)}",
        ]
    )
    if observation_fingerprint:
        lines.append(f"observation_fingerprint: {_yaml_scalar(observation_fingerprint)}")
    if str(analysis.get("editorial_body") or "").strip():
        lines.append('note_style: "natural-product-v2.2"')
        if int(job.get("version") or 0) >= 7:
            lines.append('editorial_contract_version: "2.2"')
    lines.extend(
        [
            "tags:",
            _yaml_list(tags),
            "cssclasses:",
            "  - learning-page",
            "  - github-note",
            "---",
        ]
    )
    return lines


def _repo_meta(repo: dict[str, Any]) -> str:
    license_name = ((repo.get("license") or {}).get("spdx_id") or "").strip()
    language = str(repo.get("language") or "").strip()
    meta = [str(repo["full_name"])]
    if language:
        meta.append(language)
    if license_name and license_name != "NOASSERTION":
        meta.append(license_name)
    return " · ".join(meta)


def _knowledge_map(analysis: dict[str, Any], profile: str) -> str:
    entries = analysis.get("knowledge_map") or []
    if not isinstance(entries, list) or not entries:
        return ""
    title = "内容地图" if profile in {"agent-skill", "knowledge"} else "项目地图"
    lines = [f"## {title}", ""]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        item_title = str(entry.get("title") or "").strip()
        summary = str(entry.get("summary") or "").strip()
        if not item_title:
            continue
        lines.append(f"### {item_title}")
        lines.append("")
        if summary:
            lines.append(summary)
            lines.append("")
    return "\n".join(lines).rstrip()


def _resource_index(analysis: dict[str, Any]) -> str:
    entries = analysis.get("resource_index") or []
    if not isinstance(entries, list) or not entries:
        return ""
    lines = ["## 可复用资源", ""]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or entry.get("name") or "").strip()
        purpose = str(entry.get("purpose") or entry.get("summary") or "").strip()
        path = str(entry.get("path") or "").strip()
        if not title:
            continue
        detail = purpose
        if path:
            detail = f"{detail} · `{path}`" if detail else f"`{path}`"
        lines.append(f"- **{title}**" + (f" — {detail}" if detail else ""))
    return "\n".join(lines).rstrip()


def _research_entry(job: dict[str, Any]) -> str:
    packet = str(job.get("packet_id") or "").strip()
    revision = str(job.get("revision") or "").strip()
    if not packet and not revision:
        return ""
    lines = ["## 深入研究入口", ""]
    if packet:
        lines.append(f"- Research Packet：`{packet}`")
    if revision:
        lines.append(f"- Repository revision：`{revision}`")
    lines.append("- 需要深度学习、项目对比或制作介绍内容时，应回到 Research Packet 核对原始证据，而不是只基于本篇摘要继续摘要。")
    return "\n".join(lines)


def _repository_links(job: dict[str, Any]) -> list[str]:
    repo = job["repository"]
    lines = ["## 仓库资料", "", f"- [GitHub 仓库]({repo['html_url']})"]
    homepage = str(repo.get("homepage") or "").strip()
    if homepage:
        lines.append(f"- [项目主页 / 文档]({homepage})")
    release = job.get("latest_release") or {}
    if release.get("html_url") and release.get("tag_name"):
        lines.append(f"- [Latest Release · {release['tag_name']}]({release['html_url']})")
    return lines


def _source_boundary() -> list[str]:
    return [
        "> [!meta] 来源边界",
        "> 本笔记以当前 Research Packet 中的仓库原始资料为事实底座，并可参考本次 GitHub 平台 Observation。仓库作者经验不等同于外部平台官方规则；未在证据中明确出现的版本、路径、兼容性、安装步骤或政策不自行补全。",
    ]


def _render_editorial_note(
    job: dict[str, Any],
    analysis: dict[str, Any],
    *,
    preserved_tail: str | None,
) -> str:
    """Human-first editorial mode; retain the managed-note identity and user tail."""
    repo = job["repository"]
    headline = str(analysis.get("editorial_headline") or "").strip() or str(repo["name"])
    body = str(analysis["editorial_body"]).strip()
    parts = [
        *_frontmatter(job, analysis, analysis_status="sufficient"),
        "",
        MANAGED_START,
        "",
        f"# {headline}",
        "",
        f'<small class="github-note-meta">{_repo_meta(repo)}</small>',
        "",
    ]
    image = str(job.get("first_readme_image") or "").strip()
    if image:
        parts.extend([image, ""])
    parts.extend([body, ""])
    resources = _resource_index(analysis)
    if resources:
        parts.extend([resources, ""])
    conflicts = _callout_list("risk", "仓库资料存在冲突", analysis.get("source_conflicts"))
    if conflicts:
        parts.extend([conflicts, ""])
    research = _research_entry(job)
    if research:
        parts.extend([research, ""])
    parts.extend(_repository_links(job))
    warnings = _callout_list("meta", "采集覆盖提醒", job.get("collection_warnings"))
    if warnings:
        parts.extend(["", warnings])
    parts.extend(["", *_source_boundary(), "", MANAGED_END, ""])
    tail = preserved_tail if preserved_tail is not None else DEFAULT_USER_TAIL
    parts.append(tail.rstrip())
    return "\n".join(parts).rstrip() + "\n"


def render_note(
    job: dict[str, Any],
    analysis: dict[str, Any],
    *,
    preserved_tail: str | None = None,
) -> str:
    if int(job.get("version") or 0) >= 7 and not str(analysis.get("editorial_body") or "").strip():
        raise ValueError("新 Job v7 必须生成 V2.2 自然产品正文，禁止使用旧模板。")
    if str(analysis.get("editorial_body") or "").strip():
        return _render_editorial_note(job, analysis, preserved_tail=preserved_tail)
    repo = job["repository"]
    profile = _content_profile(job, analysis)
    parts = [
        *_frontmatter(job, analysis, analysis_status="sufficient"),
        "",
        MANAGED_START,
        "",
        f"# {repo['name']}",
        "",
        f"<small class=\"github-note-meta\">{_repo_meta(repo)}</small>",
        "",
        "> [!summary] 先看结论",
        "> " + str(analysis["summary"]).strip().replace("\n", "\n> "),
        "",
    ]

    why_save = _section("为什么值得保存", analysis.get("why_save"))
    if why_save:
        parts.extend([why_save.rstrip(), ""])

    for title, key in [
        ("它是什么", "what_it_is"),
        ("能做什么", "capabilities"),
        ("适合什么场景", "use_cases"),
    ]:
        block = _section(title, analysis.get(key))
        if block:
            parts.extend([block.rstrip(), ""])

    knowledge = _knowledge_map(analysis, profile)
    if knowledge:
        parts.extend([knowledge, ""])

    for title, key in [
        ("运行要求", "requirements"),
        ("兼容性", "compatibility"),
        ("部署方式", "deployment"),
        ("核心结构", "architecture"),
        ("项目状态", "project_status"),
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

    resources = _resource_index(analysis)
    if resources:
        parts.extend([resources, ""])

    conflicts = _callout_list("risk", "仓库资料存在冲突", analysis.get("source_conflicts"))
    if conflicts:
        parts.extend([conflicts, ""])

    caveats = _section("注意事项", analysis.get("caveats"))
    if caveats:
        parts.extend([caveats.rstrip(), ""])

    research_entry = _research_entry(job)
    if research_entry:
        parts.extend([research_entry, ""])

    parts.extend(_repository_links(job))
    warnings = _callout_list("meta", "采集覆盖提醒", job.get("collection_warnings"))
    if warnings:
        parts.extend(["", warnings])

    parts.extend(["", *_source_boundary(), "", MANAGED_END, ""])
    tail = preserved_tail if preserved_tail is not None else DEFAULT_USER_TAIL
    parts.append(tail.rstrip())
    return "\n".join(parts).rstrip() + "\n"


def render_minimal_note(
    job: dict[str, Any],
    analysis: dict[str, Any],
    *,
    preserved_tail: str | None = None,
) -> str:
    repo = job["repository"]
    description = str(repo.get("description") or "").strip()
    reason = str(analysis.get("source_notes") or "当前仓库资料不足以生成可信的完整学习笔记。").strip()
    why_save = str(analysis.get("why_save") or "").strip()
    source_paths = [str(item).strip() for item in job.get("source_paths") or [] if str(item).strip()]
    resource_paths = [str(item).strip() for item in job.get("resource_paths") or [] if str(item).strip()]

    parts = [
        *_frontmatter(job, analysis, analysis_status="insufficient"),
        "",
        MANAGED_START,
        "",
        f"# {repo['name']}",
        "",
        f"<small class=\"github-note-meta\">{_repo_meta(repo)}</small>",
        "",
        "> [!warning] 待进一步研究",
        "> Research Packet 已保存，但当前资料不足以生成可信的完整学习笔记。本页先作为长期收藏入口。",
        "",
    ]
    if description:
        parts.extend(["## 仓库基本信息", "", description, ""])
    if why_save:
        parts.extend(["## 为什么值得保存", "", why_save, ""])

    if source_paths or resource_paths:
        parts.extend(["## 已发现内容", ""])
        for path in source_paths[:20]:
            parts.append(f"- 分析来源：`{path}`")
        for path in resource_paths[:20]:
            parts.append(f"- 归档资源：`{path}`")
        parts.append("")

    parts.extend(["## 当前不足", "", reason, ""])

    research_entry = _research_entry(job)
    if research_entry:
        parts.extend([research_entry, ""])

    parts.extend(_repository_links(job))
    warnings = _callout_list("meta", "采集覆盖提醒", job.get("collection_warnings"))
    if warnings:
        parts.extend(["", warnings])

    parts.extend(["", *_source_boundary(), "", MANAGED_END, ""])
    tail = preserved_tail if preserved_tail is not None else DEFAULT_USER_TAIL
    parts.append(tail.rstrip())
    return "\n".join(parts).rstrip() + "\n"
