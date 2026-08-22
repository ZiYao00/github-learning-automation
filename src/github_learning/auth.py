from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

API_ROOT = "https://api.github.com"
USER_AGENT = "github-learning-automation/0.2.0"


@dataclass(frozen=True)
class GitHubAuth:
    token: str | None
    source: str
    authenticated: bool


def resolve_github_auth() -> GitHubAuth:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and token.strip():
        return GitHubAuth(token.strip(), "environment", True)

    gh = shutil.which("gh")
    if gh:
        try:
            result = subprocess.run(
                [gh, "auth", "token"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            result = None
        if result and result.returncode == 0 and result.stdout.strip():
            return GitHubAuth(result.stdout.strip(), "gh_cli", True)
        return GitHubAuth(None, "gh_cli_not_authenticated", False)

    return GitHubAuth(None, "anonymous", False)


def probe_rate_limit(auth: GitHubAuth, timeout: int = 10) -> dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if auth.token:
        headers["Authorization"] = f"Bearer {auth.token}"
    request = urllib.request.Request(f"{API_ROOT}/rate_limit", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        return {"status": "unavailable", "http_status": exc.code}
    except (OSError, urllib.error.URLError, ValueError):
        return {"status": "unavailable"}

    core = ((payload or {}).get("resources") or {}).get("core") or {}
    return {
        "status": "ok",
        "limit": core.get("limit"),
        "remaining": core.get("remaining"),
        "reset": core.get("reset"),
    }
