from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

MAX_ADDITIONAL_SOURCES = 14
MAX_FILE_BYTES = 80_000
MAX_TOTAL_SOURCE_BYTES = 450_000
MAX_CANDIDATE_FILE_BYTES = 1_000_000

ROOT_MANIFESTS = {
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "environment.yml",
    "setup.py",
    "install.py",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "Cargo.toml",
    "go.mod",
}

_TEXT_SUFFIXES = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
}

_DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt"}
_DOC_DIR_NAMES = {"docs", "doc", "documentation"}
_NOISE_SEGMENTS = {
    "vendor",
    "node_modules",
    ".venv",
    "venv",
    "third_party",
    "third-party",
    "dist",
    "build",
}

_EXACT_PRIORITY = {
    "skill.md": (5, "skill"),
    "agents.md": (8, "agent_guidance"),
    "claude.md": (12, "agent_guidance"),
    "gemini.md": (14, "agent_guidance"),
    "quickstart.md": (18, "documentation"),
    "quickstart.rst": (18, "documentation"),
    "faq.md": (40, "documentation"),
    "contributing.md": (55, "maintenance"),
    "changelog.md": (58, "changelog"),
    "security.md": (42, "security"),
}

_KEYWORD_PRIORITY = {
    "quickstart": 20,
    "quick-start": 20,
    "getting-started": 22,
    "getting_started": 22,
    "install": 25,
    "setup": 28,
    "usage": 30,
    "support-matrix": 31,
    "support_matrix": 31,
    "architecture": 32,
    "hardware": 34,
    "validation": 35,
    "deployment": 36,
    "deploy": 36,
    "compatibility": 37,
    "configuration": 38,
    "troubleshooting": 39,
    "windows": 40,
    "macos": 41,
    "security": 42,
    "faq": 43,
    "extension": 44,
    "model-management": 45,
    "model_management": 45,
    "release-notes": 46,
    "release_notes": 46,
    "installer-trust": 47,
    "installer_trust": 47,
    "licensing": 50,
    "maintenance": 52,
    "agent-integration": 53,
    "agent_integration": 53,
    "release-checklist": 60,
}

_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


@dataclass(frozen=True)
class SourcePlanItem:
    path: str
    kind: str
    priority: int
    size: int
    sha: str


def _is_text_candidate(path: str) -> bool:
    pure = PurePosixPath(path)
    if pure.name == "Dockerfile":
        return True
    return pure.suffix.lower() in _TEXT_SUFFIXES


def _is_noise_path(path: str) -> bool:
    parts = {part.casefold() for part in PurePosixPath(path).parts}
    return bool(parts & _NOISE_SEGMENTS)


def _is_docs_path(path: str) -> bool:
    return any(part.casefold() in _DOC_DIR_NAMES for part in PurePosixPath(path).parts[:-1])


def _relative_readme_links(readme_content: str, readme_path: str) -> set[str]:
    if not readme_content:
        return set()
    readme_parent = posixpath.dirname(readme_path or "README.md")
    links: set[str] = set()
    for match in _MARKDOWN_LINK_RE.finditer(readme_content):
        target = match.group(1).strip()
        if not target:
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        target = target.split(" ", 1)[0].strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0].strip().replace("\\", "/")
        if not target:
            continue
        normalized = posixpath.normpath(posixpath.join(readme_parent, target)).lstrip("./")
        if normalized.startswith("../") or normalized == "..":
            continue
        suffix = PurePosixPath(normalized).suffix.lower()
        if suffix in _DOC_SUFFIXES:
            links.add(normalized.casefold())
    return links


def _keyword_priority(lower_path: str) -> int | None:
    priorities = [priority for keyword, priority in _KEYWORD_PRIORITY.items() if keyword in lower_path]
    return min(priorities) if priorities else None


def classify_repository(tree_entries: list[dict[str, Any]]) -> str:
    paths = [
        str(item.get("path") or "")
        for item in tree_entries
        if item.get("type") == "blob" and not _is_noise_path(str(item.get("path") or ""))
    ]
    if any(
        PurePosixPath(path).name.casefold() == "skill.md"
        or path.casefold().endswith("/agents/openai.yaml")
        or path.casefold().endswith("/agents/openai.yml")
        for path in paths
    ):
        return "agent-skill"

    container_names = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
    if any(
        (
            PurePosixPath(path).name.casefold() in container_names
            or PurePosixPath(path).name.casefold().startswith("docker-compose.")
        )
        and len(PurePosixPath(path).parts) <= 2
        for path in paths
    ):
        return "containerized"

    if any(PurePosixPath(path).name.casefold() == "package.json" and len(PurePosixPath(path).parts) <= 2 for path in paths):
        return "node-application"

    python_names = {"pyproject.toml", "requirements.txt", "setup.py"}
    if any(
        PurePosixPath(path).name.casefold() in python_names and len(PurePosixPath(path).parts) <= 2
        for path in paths
    ):
        return "python-project"

    return "generic"


def _candidate(
    item: dict[str, Any],
    *,
    readme_path: str,
    manifest_paths: set[str],
    readme_links: set[str],
    skill_repo: bool,
) -> SourcePlanItem | None:
    if item.get("type") != "blob":
        return None
    path = str(item.get("path") or "")
    if not path or path == readme_path or path in manifest_paths or _is_noise_path(path):
        return None

    size = int(item.get("size") or 0)
    if size > MAX_CANDIDATE_FILE_BYTES or not _is_text_candidate(path):
        return None

    pure = PurePosixPath(path)
    name = pure.name.casefold()
    lower_path = path.casefold()
    is_readme_linked = lower_path in readme_links
    is_doc_file = pure.suffix.lower() in _DOC_SUFFIXES
    is_docs_path = _is_docs_path(path)

    if skill_repo and len(pure.parts) == 1 and name == "universal.md":
        return SourcePlanItem(path, "skill_guidance", 7, size, str(item.get("sha") or ""))

    if (
        skill_repo
        and len(pure.parts) == 2
        and pure.parts[0].casefold() == "references"
        and is_doc_file
    ):
        match = re.match(r"^(\d+)[-_]", name)
        order = int(match.group(1)) if match else 50
        return SourcePlanItem(
            path,
            "skill_reference",
            20 + min(order, 50),
            size,
            str(item.get("sha") or ""),
        )

    priority_kind = _EXACT_PRIORITY.get(name)
    if priority_kind and (len(pure.parts) <= 3 or is_docs_path or is_readme_linked):
        priority, kind = priority_kind
        if is_readme_linked:
            priority = max(1, priority - 8)
        return SourcePlanItem(path, kind, priority, size, str(item.get("sha") or ""))

    if lower_path.endswith("/agents/openai.yaml") or lower_path.endswith("/agents/openai.yml") or lower_path in {
        "agents/openai.yaml",
        "agents/openai.yml",
    }:
        return SourcePlanItem(path, "agent_config", 10, size, str(item.get("sha") or ""))

    keyword_priority = _keyword_priority(lower_path)

    if is_readme_linked and is_doc_file:
        priority = keyword_priority if keyword_priority is not None else 45
        return SourcePlanItem(
            path,
            "documentation",
            max(12, priority - 8),
            size,
            str(item.get("sha") or ""),
        )

    if is_docs_path and is_doc_file:
        if keyword_priority is not None:
            return SourcePlanItem(path, "documentation", keyword_priority + 15, size, str(item.get("sha") or ""))
        if name in {"readme.md", "index.md"}:
            return SourcePlanItem(path, "documentation", 48, size, str(item.get("sha") or ""))

    if len(pure.parts) <= 2 and is_doc_file and keyword_priority is not None:
        return SourcePlanItem(path, "documentation", keyword_priority + 5, size, str(item.get("sha") or ""))

    return None


def plan_additional_sources(
    tree_entries: list[dict[str, Any]],
    *,
    readme_path: str = "",
    readme_content: str = "",
    manifest_paths: set[str] | None = None,
) -> list[SourcePlanItem]:
    manifest_paths = manifest_paths or set()
    readme_links = _relative_readme_links(readme_content, readme_path)
    skill_repo = any(
        item.get("type") == "blob"
        and str(item.get("path") or "").casefold() == "skill.md"
        for item in tree_entries
    )
    candidates = [
        planned
        for item in tree_entries
        if (
            planned := _candidate(
                item,
                readme_path=readme_path,
                manifest_paths=manifest_paths,
                readme_links=readme_links,
                skill_repo=skill_repo,
            )
        )
        is not None
    ]
    candidates.sort(key=lambda item: (item.priority, item.path.casefold()))

    selected: list[SourcePlanItem] = []
    budget = 0
    for item in candidates:
        estimated = min(max(item.size, 1), MAX_FILE_BYTES)
        if selected and budget + estimated > MAX_TOTAL_SOURCE_BYTES:
            continue
        selected.append(item)
        budget += estimated
        if len(selected) >= MAX_ADDITIONAL_SOURCES:
            break
    return selected
