"""Local, human-owned repository catalog. No network, LLM, or collector calls.

Only the five-column main table is writable. All other bytes are preserved.
The lock is shared by physical notes root, even across different project clones.
"""
from __future__ import annotations

import difflib
import html
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import urlsplit

from .config import Settings
from .input_resolver import ResolvedRepository, resolve_repository
from .publish_safety import PublishSafetyError, publish_bytes, repository_lock, sha256

CATALOG_NAME = "00-仓库收藏清单.md"
NAV_NAME = "00-GitHub导航.md"
CATALOG_CONTRACT_VERSION = 1
HEADER = ("仓库", "收藏原因 / 可能用途", "优先级", "状态", "正式笔记")
STATES = {"待归档", "待重制", "暂缓", "待补研究", "已归档", "已实测"}
PRIORITIES = ("高", "中", "低")
_URL = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)
_ID = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_RESERVED = {"settings", "orgs", "users", "search", "topics", "collections", "marketplace",
             "features", "sponsors", "login", "signup", "notifications", "explore", "about"}
DEFAULT_CATALOG = """# GitHub 仓库收藏清单

> 轻量候选收藏，不代表已经归档、安装或实测。原因和优先级由用户维护。

## 收藏列表

| 仓库 | 收藏原因 / 可能用途 | 优先级 | 状态 | 正式笔记 |
| --- | --- | :---: | :---: | --- |

## 状态说明

- **待归档**：已收藏，尚无已核验的完整研究笔记。
- **待补研究**：只有来源不足的 Minimal Note，不表示研究完成。
- **已归档**：存在身份和结构有效、analysis_status=sufficient 的正式笔记。
- **已实测**：只由用户根据实际使用结果确认，程序不得推断。
- **暂缓**：人工意愿，同步默认保留。

## 维护约定

收藏不触发正式采集。正式研究沿用 prepare → 分析 → finalize。
导航是自动生成的视图，不在导航中手动勾选；冲突应先核对，不覆盖人工决定。
""".encode("utf-8")


class CatalogError(ValueError):
    def __init__(self, code: str, message: str, *, line: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.line = line


def normalize_repository(value: str) -> ResolvedRepository:
    """Validate exactly one supplied identity; this does NOT verify existence/publicity."""
    value = value.strip()
    if re.match(r"https?://", value, re.IGNORECASE):
        parsed = urlsplit(value)
        if (parsed.scheme.lower() not in {"http", "https"}
                or parsed.netloc.lower() != "github.com" or "\\" in value or "%" in parsed.path):
            raise CatalogError("candidate_unverified", "只接受不含凭据、端口或编码路径的 github.com 仓库地址。")
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2 or any(p in {"", ".", ".."} for p in parts):
            raise CatalogError("candidate_unverified", "地址缺少明确的 owner/repo，或含不安全路径。")
        identity = "/".join(parts[:2])
    else:
        identity = value
    if identity.lower().endswith(".git"):
        identity = identity[:-4]
    if not _ID.fullmatch(identity):
        raise CatalogError("candidate_unverified", "需要唯一、明确的 owner/repo；不会根据项目名称猜地址。")
    owner, repo = identity.split("/")
    if owner in {".", ".."} or repo in {".", ".."} or owner.casefold() in _RESERVED:
        raise CatalogError("candidate_unverified", "不是可识别的仓库身份。")
    return resolve_repository(identity)


def text_cell(value: str) -> str:
    """Store supplied prose as one inert Markdown table cell, not executable markup."""
    value = html.escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`\[\]*_|!])", r"\\\1", value)


def table_cells(line: str, number: int) -> tuple[tuple[str, ...], tuple[tuple[int, int], ...]]:
    raw = line.rstrip("\r\n")
    pipes: list[int] = []
    slashes = 0
    for i, ch in enumerate(raw):
        if ch == "|" and slashes % 2 == 0:
            pipes.append(i)
        slashes = slashes + 1 if ch == "\\" else 0
    if (len(pipes) != 6 or raw[:pipes[0]].strip() or raw[pipes[-1] + 1:].strip()):
        raise CatalogError("catalog_format_invalid", f"第 {number} 行必须是五列表格；请检查未转义的管道符。", line=number)
    spans = tuple((a + 1, b) for a, b in zip(pipes, pipes[1:]))
    return tuple(raw[a:b].strip() for a, b in spans), spans


@dataclass(frozen=True)
class CatalogRow:
    repository: str
    line_index: int
    cells: tuple[str, ...]
    spans: tuple[tuple[int, int], ...]

    @property
    def key(self) -> str:
        return self.repository.casefold()

    @property
    def priority(self) -> str:
        return self.cells[2]

    @property
    def status(self) -> str:
        return self.cells[3]


@dataclass(frozen=True)
class CatalogDocument:
    raw: bytes
    lines: tuple[str, ...]
    rows: tuple[CatalogRow, ...]
    table_start: int
    table_end: int
    newline: str

    @classmethod
    def parse(cls, data: bytes) -> CatalogDocument:
        try:
            lines = tuple(data.decode("utf-8").splitlines(keepends=True))
        except UnicodeError as exc:
            raise CatalogError("catalog_encoding_invalid", "清单必须是 UTF-8；未转换或覆盖原文件。") from exc
        starts = [i for i, line in enumerate(lines) if line.strip() == "## 收藏列表"]
        ends = [i for i, line in enumerate(lines) if line.strip() == "## 状态说明"]
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            raise CatalogError("catalog_format_invalid", "需要唯一且顺序正确的「## 收藏列表」和「## 状态说明」。")
        active = [i for i in range(starts[0] + 1, ends[0]) if lines[i].strip()]
        if len(active) < 2 or active != list(range(active[0], active[-1] + 1)):
            raise CatalogError("catalog_format_invalid", "主表必须连续，不能夹入第二张表、说明文字或空行。")
        header, _ = table_cells(lines[active[0]], active[0] + 1)
        separator, _ = table_cells(lines[active[1]], active[1] + 1)
        if header != HEADER or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
            raise CatalogError("catalog_format_invalid", "主表标题或分隔行与五列契约不符；请人工核对。", line=active[0] + 1)
        rows: list[CatalogRow] = []
        seen: set[str] = set()
        for index in active[2:]:
            cells, spans = table_cells(lines[index], index + 1)
            urls = re.findall(r"https?://[^\s)\]>]+", cells[0], re.IGNORECASE)
            if len(urls) != 1:
                raise CatalogError("catalog_identity_invalid", "仓库列须包含唯一 GitHub 仓库链接。", line=index + 1)
            resolved = normalize_repository(urls[0])
            key = resolved.full_name.casefold()
            labels = [s for s in re.findall(r"`([^`]+)`", cells[0]) if _ID.fullmatch(s)]
            if any(normalize_repository(label).full_name.casefold() != key for label in labels):
                raise CatalogError("catalog_identity_conflict", "仓库链接与 owner/repo 标签不一致。", line=index + 1)
            if key in seen:
                raise CatalogError("catalog_duplicate_repository", f"主表有重复仓库：{resolved.full_name}", line=index + 1)
            if any(not c for c in cells):
                raise CatalogError("catalog_format_invalid", "主表不得有空列；没有笔记时使用「—」。", line=index + 1)
            seen.add(key)
            rows.append(CatalogRow(resolved.full_name, index, cells, spans))
        newline = "\r\n" if lines[active[0]].endswith("\r\n") else "\n"
        return cls(data, lines, tuple(rows), active[0], active[-1] + 1, newline)

    @property
    def outside_table(self) -> tuple[bytes, bytes]:
        return ("".join(self.lines[:self.table_start]).encode("utf-8"),
                "".join(self.lines[self.table_end:]).encode("utf-8"))

    def updated(self, changes: dict[str, dict[int, str]] | None = None,
                additions: Sequence[Sequence[str]] = ()) -> bytes:
        changes = changes or {}
        lines = list(self.lines)
        unknown = set(changes) - {row.key for row in self.rows}
        if unknown:
            raise CatalogError("catalog_unknown_row", "不允许修改未识别的行。")
        for row in self.rows:
            line = lines[row.line_index]
            for column, value in sorted(changes.get(row.key, {}).items(), reverse=True):
                if column not in {3, 4} or "\n" in value or "\r" in value:
                    raise CatalogError("catalog_change_invalid", "同步只允许更新状态和正式笔记两列。")
                a, b = row.spans[column]
                original = line[a:b]
                left = original[:len(original) - len(original.lstrip())]
                right = original[len(original.rstrip()):]
                line = line[:a] + left + value + right + line[b:]
            lines[row.line_index] = line
        if additions:
            new_lines = ["| " + " | ".join(cells) + " |" + self.newline for cells in additions]
            lines[self.table_end:self.table_end] = new_lines
        data = "".join(lines).encode("utf-8")
        result = CatalogDocument.parse(data)
        if result.outside_table != self.outside_table:
            raise CatalogError("catalog_preservation_failed", "主表以外内容发生变化，拒绝发布。")
        return data


def checked_path(settings: Settings, name: str) -> Path:
    if settings.notes_is_fallback or not settings.notes_root.is_dir():
        raise CatalogError("catalog_storage_unconfirmed", "先确认现有 notes_root；不会自动配置或迁移。")
    root = settings.notes_root.resolve()
    path = root / name
    if path.is_symlink() or path.resolve().parent != root or (path.exists() and not path.is_file()):
        raise CatalogError("catalog_path_invalid", "索引目标必须是 notes_root 内的普通文件。")
    return path


def read_document(settings: Settings, *, allow_missing: bool = False) -> tuple[CatalogDocument, str | None]:
    path = checked_path(settings, CATALOG_NAME)
    if not path.exists():
        if allow_missing:
            return CatalogDocument.parse(DEFAULT_CATALOG), None
        raise CatalogError("catalog_missing", "尚无收藏清单；显式收藏仓库后才创建，不影响正式研究。")
    data = path.read_bytes()
    return CatalogDocument.parse(data), sha256(data)


def require_expected(actual: str | None, expected: str | None) -> None:
    if expected is not None and actual != (None if expected == "absent" else expected):
        raise CatalogError("catalog_target_changed", "文件与已审阅的 SHA 不同；请重新读取并合并，不覆盖。")


@contextmanager
def catalog_lock(settings: Settings, *, timeout: float = 5.0) -> Iterator[None]:
    root = checked_path(settings, CATALOG_NAME).parent
    state = root / ".github-catalog"
    if state.is_symlink() or state.resolve().parent != root:
        raise CatalogError("catalog_lock_path_invalid", "索引锁目录不得指向其它位置。")
    try:
        with repository_lock(state, "index/catalog", timeout=timeout):
            yield
    except PublishSafetyError as exc:
        raise CatalogError("catalog_busy" if exc.code == "repo_busy" else exc.code, str(exc)) from exc


def commit_bytes(path: Path, data: bytes, expected: str | None) -> bool:
    actual = sha256(path.read_bytes()) if path.exists() else None
    require_expected(actual, expected if expected is not None else "absent")
    if actual == sha256(data):
        return False
    try:
        publish_bytes(path, data, expected_old_sha=expected)
    except PublishSafetyError as exc:
        raise CatalogError(exc.code.replace("note_", "catalog_"), str(exc)) from exc
    return True


def unified_diff(before: bytes, after: bytes, name: str) -> str:
    return "".join(difflib.unified_diff(before.decode("utf-8").splitlines(keepends=True),
                                       after.decode("utf-8").splitlines(keepends=True),
                                       fromfile=name, tofile=name))


def _candidates(inputs: Sequence[str | dict[str, Any]], description: str, priority: str,
                source: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in inputs:
        options = {"description": description, "priority": priority, "source": source}
        if isinstance(item, dict):
            if set(item) - {"repository", "description", "priority", "source"}:
                result.append({"error": "candidate_unverified", "message": "批量对象含未知字段。"})
                continue
            options.update({k: v for k, v in item.items() if k != "repository"})
            value = item.get("repository", "")
        else:
            value = item
        if not isinstance(value, str) or not all(isinstance(v, str) for v in options.values()):
            result.append({"error": "candidate_unverified", "message": "输入和说明必须是文本。"})
            continue
        urls = _URL.findall(value)
        values = [u.rstrip("。，；;，!！?？)]}）】") for u in urls] if urls else [value.strip()]
        for candidate in values:
            try:
                repo = normalize_repository(candidate)
                if options["priority"] not in PRIORITIES:
                    raise CatalogError("candidate_priority_invalid", "优先级只能是高、中、低。")
                result.append({"repository": repo.full_name, "url": repo.canonical_url, **options})
            except (CatalogError, ValueError) as exc:
                result.append({"input": candidate, "error": getattr(exc, "code", "candidate_unverified"),
                               "message": str(exc)})
    return result


def add_catalog(settings: Settings, inputs: Sequence[str | dict[str, Any]], *,
                description: str = "待研究：仅记录链接，尚未核验仓库内容。", priority: str = "中",
                source: str = "", dry_run: bool = False, expected_sha: str | None = None) -> dict[str, Any]:
    if not inputs:
        raise CatalogError("catalog_input_required", "请提供仓库地址或 UTF-8 JSON 批量文件。")
    candidates = _candidates(inputs, description, priority, source)

    def plan() -> tuple[dict[str, Any], bytes, str | None]:
        doc, old_sha = read_document(settings, allow_missing=True)
        require_expected(old_sha, expected_sha)
        seen = {row.key for row in doc.rows}
        additions = []
        results = []
        for item in candidates:
            if "error" in item:
                results.append({**item, "status": "needs_verification"})
                continue
            identity = item["repository"]
            if identity.casefold() in seen:
                results.append({"repository": identity, "status": "already_saved", "existing_values_preserved": True})
                continue
            reason = item["description"].strip() or "待研究：仅记录链接，尚未核验仓库内容。"
            if item["source"].strip():
                reason += "；发现来源：" + item["source"].strip()
            additions.append([f"[{identity}]({item['url']}) · `{identity}`", text_cell(reason),
                              item["priority"], "待归档", "—"])
            seen.add(identity.casefold())
            results.append({"repository": identity, "status": "would_add" if dry_run else "added",
                            "identity_check": "syntax_only", "public_status": "not_checked"})
        output = doc.updated(additions=additions)
        changed = bool(additions)
        errors = any("error" in item for item in results)
        payload = {"status": "catalog_partial" if errors else ("catalog_added" if changed else "no_change"),
                   "dry_run": dry_run, "changed": changed, "written": False, "added": len(additions),
                   "total": len(seen), "results": results, "catalog_sha256": old_sha,
                   "proposed_sha256": sha256(output), "network_used": False}
        if dry_run:
            payload["diff"] = unified_diff(doc.raw if old_sha else b"", output, CATALOG_NAME) if changed else ""
        return payload, output, old_sha

    if dry_run:
        return plan()[0]
    with catalog_lock(settings):
        payload, output, old_sha = plan()
        if payload["changed"]:
            payload["written"] = commit_bytes(checked_path(settings, CATALOG_NAME), output, old_sha)
            payload["catalog_sha256"] = sha256(output)
        return payload
