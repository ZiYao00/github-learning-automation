from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class ResolvedRepository:
    owner: str
    repo: str
    full_name: str
    canonical_url: str


def resolve_repository(value: str) -> ResolvedRepository:
    value = value.strip()
    if _REPO_RE.fullmatch(value):
        owner, repo = value.split("/", 1)
        return ResolvedRepository(owner, repo, f"{owner}/{repo}", f"https://github.com/{owner}/{repo}")

    urls = re.findall(r"https?://[^\s<>'\"]+", value)
    if not urls:
        raise ValueError("未识别到 GitHub 仓库地址；请提供 https://github.com/owner/repo 或 owner/repo。")
    parsed = urllib.parse.urlparse(urls[0].rstrip("。)，)]}"))
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() != "github.com":
        raise ValueError("当前只接受 github.com 官方仓库地址。")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("GitHub 地址中缺少 owner/repo。")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not _REPO_RE.fullmatch(f"{owner}/{repo}"):
        raise ValueError("GitHub 仓库名称格式无效。")
    return ResolvedRepository(owner, repo, f"{owner}/{repo}", f"https://github.com/{owner}/{repo}")
