from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .auth import API_ROOT, USER_AGENT, GitHubAuth, resolve_github_auth


class GitHubFetchError(RuntimeError):
    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class SourceBundle:
    repository: dict[str, Any]
    readme: str
    root_entries: list[dict[str, Any]]
    manifests: dict[str, str]
    latest_release: dict[str, Any] | None
    warnings: tuple[str, ...] = ()


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
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **({"Authorization": f"Bearer {auth.token}"} if auth.token else {})})
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


def _try_file(full_name: str, path: str, auth: GitHubAuth) -> str | None:
    encoded = urllib.parse.quote(path)
    try:
        payload = _request_json(f"{API_ROOT}/repos/{full_name}/contents/{encoded}", auth)
    except GitHubFetchError as exc:
        if exc.status == 404:
            return None
        raise
    if not isinstance(payload, dict) or payload.get("type") != "file":
        return None
    return _decode_content(payload)


def _optional_manifest(full_name: str, entry: dict[str, Any], auth: GitHubAuth) -> tuple[str | None, str | None]:
    name = str(entry.get("name") or "")
    download_url = str(entry.get("download_url") or "").strip()
    try:
        if download_url:
            return _request_text(download_url, auth), None
        return _try_file(full_name, name, auth), None
    except GitHubFetchError as exc:
        return None, f"可选 manifest `{name}` 读取失败，已跳过：{exc}"


def fetch_repository_sources(full_name: str, auth: GitHubAuth | None = None) -> SourceBundle:
    auth = auth or resolve_github_auth()
    warnings: list[str] = []

    repo = _request_json(f"{API_ROOT}/repos/{full_name}", auth)
    try:
        readme_payload = _request_json(f"{API_ROOT}/repos/{full_name}/readme", auth)
        readme = _decode_content(readme_payload)
    except GitHubFetchError as exc:
        if exc.status != 404:
            raise
        readme = ""

    root_payload = _request_json(f"{API_ROOT}/repos/{full_name}/contents", auth)
    root_entries = root_payload if isinstance(root_payload, list) else []
    root_by_name = {str(item.get("name")): item for item in root_entries if isinstance(item, dict)}

    manifest_names = [
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "environment.yml",
        "setup.py",
        "install.py",
        "Dockerfile",
        "docker-compose.yml",
    ]
    manifests: dict[str, str] = {}
    for name in manifest_names:
        entry = root_by_name.get(name)
        if not entry:
            continue
        content, warning = _optional_manifest(full_name, entry, auth)
        if content is not None:
            manifests[name] = content[:30000]
        if warning:
            warnings.append(warning)

    try:
        release = _request_json(f"{API_ROOT}/repos/{full_name}/releases/latest", auth)
        latest_release = release if isinstance(release, dict) else None
    except GitHubFetchError as exc:
        if exc.status == 404:
            latest_release = None
        else:
            latest_release = None
            warnings.append(f"Latest Release 读取失败，已按可选来源跳过：{exc}")

    return SourceBundle(repo, readme[:120000], root_entries, manifests, latest_release, tuple(warnings))
