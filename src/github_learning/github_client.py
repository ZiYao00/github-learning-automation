from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .auth import API_ROOT, USER_AGENT, GitHubAuth, resolve_github_auth
from .source_planner import (
    MAX_FILE_BYTES,
    MAX_TOTAL_SOURCE_BYTES,
    ROOT_MANIFESTS,
    classify_repository,
    plan_additional_sources,
)


class GitHubFetchError(RuntimeError):
    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class SourceDocument:
    path: str
    kind: str
    content: str
    sha: str = ""
    size: int = 0
    truncated: bool = False


@dataclass(frozen=True)
class SourceBundle:
    repository: dict[str, Any]
    readme: str
    root_entries: list[dict[str, Any]]
    manifests: dict[str, str]
    latest_release: dict[str, Any] | None
    warnings: tuple[str, ...] = ()
    revision: str = ""
    default_branch: str = ""
    readme_path: str = ""
    source_profile: str = "generic"
    sources: tuple[SourceDocument, ...] = ()


def _headers(auth: GitHubAuth) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if auth.token:
        headers["Authorization"] = f"Bearer {auth.token}"
    return headers


def _request_json(url: str, auth: GitHubAuth | None = None) -> Any:
    auth = auth or resolve_github_auth()
    req = urllib.request.Request(url, headers=_headers(auth))
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GitHubFetchError("not_found", f"GitHub 资源不存在或不可访问：{url}", status=404) from exc
        if exc.code == 401:
            raise GitHubFetchError("auth_invalid", "GitHub 认证无效，请重新登录 GitHub CLI 或更新 Token。", status=401) from exc
        if exc.code == 403:
            if auth.authenticated:
                message = "GitHub API 拒绝请求；可能达到认证额度或当前凭据无权访问该资源。"
                code = "rate_limited_or_forbidden"
            else:
                message = "GitHub 匿名 API 拒绝请求；请登录 GitHub CLI，或显式提供 GITHUB_TOKEN 后重试。"
                code = "auth_required"
            raise GitHubFetchError(code, message, status=403) from exc
        raise GitHubFetchError("api_error", f"GitHub API 请求失败：HTTP {exc.code}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise GitHubFetchError("network_error", f"无法连接 GitHub API：{exc.reason}") from exc


def _request_text(url: str, auth: GitHubAuth) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com":
        raise GitHubFetchError("unsafe_raw_url", f"拒绝读取非 GitHub Raw 地址：{url}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, **({"Authorization": f"Bearer {auth.token}"} if auth.token else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise GitHubFetchError("optional_source_unavailable", f"GitHub Raw 文件读取失败：HTTP {exc.code}", exc.code) from exc
    except urllib.error.URLError as exc:
        raise GitHubFetchError("optional_source_unavailable", f"GitHub Raw 文件读取失败：{exc.reason}") from exc


def _decode_content(payload: dict[str, Any]) -> str:
    content = payload.get("content") or ""
    if payload.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return str(content)


def _with_ref(url: str, revision: str) -> str:
    return f"{url}?{urllib.parse.urlencode({'ref': revision})}"


def _raw_url(full_name: str, revision: str, path: str) -> str:
    owner, repo = full_name.split("/", 1)
    encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    return (
        "https://raw.githubusercontent.com/"
        f"{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(repo, safe='')}/"
        f"{urllib.parse.quote(revision, safe='')}/{encoded_path}"
    )


def _truncate(content: str, limit: int = MAX_FILE_BYTES) -> tuple[str, bool]:
    encoded = content.encode("utf-8")
    if len(encoded) <= limit:
        return content, False
    clipped = encoded[:limit].decode("utf-8", errors="ignore")
    return clipped, True


def _fetch_planned_text(
    full_name: str,
    revision: str,
    path: str,
    auth: GitHubAuth,
    *,
    kind: str,
    sha: str = "",
    size: int = 0,
) -> tuple[SourceDocument | None, str | None]:
    try:
        content = _request_text(_raw_url(full_name, revision, path), auth)
    except GitHubFetchError as exc:
        return None, f"可选来源 `{path}` 读取失败，已跳过：{exc}"
    clipped, truncated = _truncate(content)
    return SourceDocument(path, kind, clipped, sha, size or len(content.encode("utf-8")), truncated), None


def _fit_document_budget(document: SourceDocument, remaining: int) -> SourceDocument | None:
    if remaining <= 0:
        return None
    encoded = document.content.encode("utf-8")
    if len(encoded) <= remaining:
        return document
    clipped = encoded[:remaining].decode("utf-8", errors="ignore")
    if not clipped:
        return None
    return SourceDocument(
        document.path,
        document.kind,
        clipped,
        document.sha,
        document.size,
        True,
    )


def _root_entries_from_tree(tree_entries: list[dict[str, Any]], full_name: str, revision: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in tree_entries:
        path = str(item.get("path") or "")
        if not path or "/" in path:
            continue
        item_type = str(item.get("type") or "")
        result.append(
            {
                "name": path,
                "path": path,
                "type": "file" if item_type == "blob" else "dir" if item_type == "tree" else item_type,
                "sha": item.get("sha") or "",
                "size": item.get("size") or 0,
                "download_url": _raw_url(full_name, revision, path) if item_type == "blob" else None,
            }
        )
    return sorted(result, key=lambda item: str(item.get("name") or "").casefold())


def fetch_repository_sources(full_name: str, auth: GitHubAuth | None = None) -> SourceBundle:
    auth = auth or resolve_github_auth()
    warnings: list[str] = []

    repo = _request_json(f"{API_ROOT}/repos/{full_name}", auth)
    if bool(repo.get("private")):
        raise GitHubFetchError(
            "private_repository_blocked",
            "当前工作流默认拒绝采集私有仓库，避免把私有资料意外写入 Obsidian 或 runtime。",
        )

    default_branch = str(repo.get("default_branch") or "main")
    encoded_branch = urllib.parse.quote(default_branch, safe="")
    commit = _request_json(f"{API_ROOT}/repos/{full_name}/commits/{encoded_branch}", auth)
    revision = str(commit.get("sha") or "")
    tree_sha = str(((commit.get("commit") or {}).get("tree") or {}).get("sha") or "")
    if not revision or not tree_sha:
        raise GitHubFetchError("snapshot_unavailable", "无法确定仓库 HEAD commit/tree，拒绝生成混合版本来源包。")

    try:
        readme_payload = _request_json(_with_ref(f"{API_ROOT}/repos/{full_name}/readme", revision), auth)
        readme_full = _decode_content(readme_payload)
        readme = readme_full[:120_000]
        readme_path = str(readme_payload.get("path") or "README.md")
        readme_sha = str(readme_payload.get("sha") or "")
    except GitHubFetchError as exc:
        if exc.status != 404:
            raise
        readme = ""
        readme_full = ""
        readme_path = ""
        readme_sha = ""

    root_payload = _request_json(_with_ref(f"{API_ROOT}/repos/{full_name}/contents", revision), auth)
    pinned_root_entries = root_payload if isinstance(root_payload, list) else []

    try:
        tree_payload = _request_json(f"{API_ROOT}/repos/{full_name}/git/trees/{tree_sha}?recursive=1", auth)
        tree_entries = tree_payload.get("tree") if isinstance(tree_payload, dict) else []
        tree_entries = tree_entries if isinstance(tree_entries, list) else []
        if isinstance(tree_payload, dict) and tree_payload.get("truncated"):
            warnings.append("Git tree 返回 truncated=true；Source Planner 只基于本次可见路径选择补充来源。")
    except GitHubFetchError as exc:
        tree_entries = []
        warnings.append(f"递归 Git tree 读取失败，Source Planner 降级为根目录资料：{exc}")

    if tree_entries:
        root_entries = _root_entries_from_tree(tree_entries, full_name, revision)
    else:
        root_entries = pinned_root_entries
        tree_entries = [
            {
                "path": str(item.get("path") or item.get("name") or ""),
                "type": "blob" if item.get("type") == "file" else "tree",
                "sha": item.get("sha") or "",
                "size": item.get("size") or 0,
            }
            for item in pinned_root_entries
            if isinstance(item, dict)
        ]

    root_tree = {
        str(item.get("path") or ""): item
        for item in tree_entries
        if isinstance(item, dict) and "/" not in str(item.get("path") or "")
    }
    manifests: dict[str, str] = {}
    sources: list[SourceDocument] = []
    remaining_budget = MAX_TOTAL_SOURCE_BYTES

    if readme:
        readme_clipped, readme_truncated = _truncate(
            readme_full or readme,
            min(120_000, remaining_budget),
        )
        readme_document = SourceDocument(
            readme_path or "README.md",
            "readme",
            readme_clipped,
            readme_sha,
            len((readme_full or readme).encode("utf-8")),
            readme_truncated,
        )
        sources.append(readme_document)
        remaining_budget -= len(readme_document.content.encode("utf-8"))

    manifest_paths: set[str] = set()
    for name in sorted(ROOT_MANIFESTS, key=str.casefold):
        entry = root_tree.get(name)
        if not entry:
            continue
        document, warning = _fetch_planned_text(
            full_name,
            revision,
            name,
            auth,
            kind="manifest",
            sha=str(entry.get("sha") or ""),
            size=int(entry.get("size") or 0),
        )
        if document is not None:
            fitted = _fit_document_budget(document, remaining_budget)
            if fitted is not None:
                manifests[name] = fitted.content
                sources.append(fitted)
                manifest_paths.add(name)
                remaining_budget -= len(fitted.content.encode("utf-8"))
            else:
                warnings.append(f"来源总预算已用尽，跳过 manifest：{name}")
        if warning:
            warnings.append(warning)

    source_profile = classify_repository(tree_entries)
    for planned in plan_additional_sources(
        tree_entries,
        readme_path=readme_path,
        readme_content=readme_full or readme,
        manifest_paths=manifest_paths,
    ):
        document, warning = _fetch_planned_text(
            full_name,
            revision,
            planned.path,
            auth,
            kind=planned.kind,
            sha=planned.sha,
            size=planned.size,
        )
        if document is not None:
            fitted = _fit_document_budget(document, remaining_budget)
            if fitted is not None:
                sources.append(fitted)
                remaining_budget -= len(fitted.content.encode("utf-8"))
            else:
                warnings.append(f"来源总预算已用尽，跳过补充来源：{planned.path}")
        if warning:
            warnings.append(warning)

    try:
        release = _request_json(f"{API_ROOT}/repos/{full_name}/releases/latest", auth)
        latest_release = release if isinstance(release, dict) else None
        if latest_release:
            body = str(latest_release.get("body") or "")
            body_clipped, body_truncated = _truncate(body, min(50_000, max(remaining_budget, 0)))
            if body_clipped:
                release_document = SourceDocument(
                    "@latest_release",
                    "release",
                    body_clipped,
                    "",
                    len(body.encode("utf-8")),
                    body_truncated,
                )
                sources.append(release_document)
                remaining_budget -= len(release_document.content.encode("utf-8"))
            elif body and remaining_budget <= 0:
                warnings.append("来源总预算已用尽，Latest Release 仅保留 metadata，正文未进入来源包。")
    except GitHubFetchError as exc:
        if exc.status == 404:
            latest_release = None
        else:
            latest_release = None
            warnings.append(f"Latest Release 读取失败，已按可选来源跳过：{exc}")

    return SourceBundle(
        repository=repo,
        readme=readme,
        root_entries=root_entries,
        manifests=manifests,
        latest_release=latest_release,
        warnings=tuple(warnings),
        revision=revision,
        default_branch=default_branch,
        readme_path=readme_path,
        source_profile=source_profile,
        sources=tuple(sources),
    )
