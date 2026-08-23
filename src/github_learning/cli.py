from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .auth import probe_rate_limit, resolve_github_auth
from .config import ConfigurationError, configure_notes, load_settings
from .github_client import GitHubFetchError, fetch_repository_sources
from .input_resolver import resolve_repository
from .lifecycle import finalize_job, preflight_publish, prepare_job


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (OSError, ValueError):
                pass


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _doctor_payload(settings, *, check_api: bool = False) -> dict[str, Any]:
    auth = resolve_github_auth()
    issues: list[dict[str, str]] = []

    if settings.notes_is_fallback:
        issues.append(
            {
                "code": "configuration_required",
                "message": "尚未显式配置笔记保存位置；prepare 不会静默写入项目 fallback。",
            }
        )
    if not auth.authenticated:
        issues.append(
            {
                "code": "auth_recommended",
                "message": "未检测到 GitHub 登录。匿名 API 额度有限；首次使用应先登录，或显式选择匿名模式。",
            }
        )

    if settings.notes_is_fallback:
        status = "configuration_required"
    elif not auth.authenticated:
        status = "auth_recommended"
    else:
        status = "ready"

    payload: dict[str, Any] = {
        "status": status,
        "ready": status == "ready",
        "project_root": str(settings.project_root),
        "notes_root": str(settings.notes_root),
        "notes_source": settings.notes_source,
        "notes_is_fallback": settings.notes_is_fallback,
        "local_config": str(settings.local_config_path),
        "local_config_exists": settings.local_config_path.is_file(),
        "github_auth": {
            "authenticated": auth.authenticated,
            "source": auth.source,
        },
        "issues": issues,
    }
    if check_api:
        payload["github_api"] = probe_rate_limit(auth)
    return payload


def _configuration_required(settings) -> dict[str, Any]:
    return {
        "status": "configuration_required",
        "message": "请先配置笔记保存位置，再执行 prepare。",
        "notes_is_fallback": True,
        "fallback_path": str(settings.notes_root),
        "local_config": str(settings.local_config_path),
        "example": 'python scripts/github_learning.py configure --vault-root "D:\\Notes\\MyVault" --notes-subdir "GitHub-Note"',
    }


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(prog="github-learning", description="GitHub 仓库转学习笔记")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="采集 GitHub 官方资料并创建 Agent 分析任务")
    p_prepare.add_argument("repository")
    p_prepare.add_argument(
        "--allow-anonymous",
        action="store_true",
        help="显式允许匿名 GitHub API；额度较低，不建议作为默认模式。",
    )
    p_prepare.add_argument(
        "--new-note",
        action="store_true",
        help="为同一仓库显式创建另一篇笔记；默认按 repo identity 创建或刷新现有笔记。",
    )
    p_prepare.add_argument(
        "--replace-legacy",
        action="store_true",
        help="显式允许迁移缺少 managed marker 的旧版笔记；finalize 前会先备份旧文件。",
    )

    p_finalize = sub.add_parser("finalize", help="验证 Agent 分析并发布 Markdown")
    p_finalize.add_argument("job_dir")
    p_finalize.add_argument(
        "--replace-legacy",
        action="store_true",
        help="显式允许刷新缺少 managed marker 的旧版笔记；原文会先备份到 runtime job。",
    )

    p_doctor = sub.add_parser("doctor", help="检查首次运行配置、GitHub 认证与输出目录")
    p_doctor.add_argument("--check-api", action="store_true", help="额外探测 GitHub API rate limit。")

    p_configure = sub.add_parser("configure", help="创建或更新 config/local.json")
    target = p_configure.add_mutually_exclusive_group(required=True)
    target.add_argument("--vault-root", type=Path, help="Obsidian Vault 根目录。")
    target.add_argument("--notes-root", type=Path, help="直接指定笔记输出目录。")
    p_configure.add_argument("--notes-subdir", default="GitHub-Note", help="Vault 内相对子目录，默认 GitHub-Note。")

    args = parser.parse_args()
    root = _project_root()

    try:
        if args.command == "configure":
            path = configure_notes(
                root,
                vault_root=args.vault_root,
                notes_subdir=args.notes_subdir,
                notes_root=args.notes_root,
            )
            settings = load_settings(root)
            _print(
                {
                    "status": "configured",
                    "local_config": str(path),
                    "notes_root": str(settings.notes_root),
                    "notes_source": settings.notes_source,
                }
            )
            return 0

        settings = load_settings(root)

        if args.command == "doctor":
            _print(_doctor_payload(settings, check_api=args.check_api))
            return 0

        if args.command == "prepare":
            if settings.notes_is_fallback:
                _print(_configuration_required(settings))
                return 0

            auth = resolve_github_auth()
            if not auth.authenticated and not args.allow_anonymous:
                _print(
                    {
                        "status": "auth_recommended",
                        "message": "未检测到 GitHub 登录；为避免匿名 60 次/小时额度导致中途失败，本次未开始采集。",
                        "github_auth": {"authenticated": False, "source": auth.source},
                        "next_actions": [
                            "运行 gh auth login 后重试（推荐）",
                            "或显式追加 --allow-anonymous 继续匿名模式",
                        ],
                    }
                )
                return 0

            resolved = resolve_repository(args.repository)
            publish_mode = "new" if args.new_note else "upsert"
            preflight = preflight_publish(
                settings,
                resolved.full_name,
                publish_mode=publish_mode,
                replace_legacy=args.replace_legacy,
            )
            if preflight["status"] != "ready":
                _print(preflight)
                return 0
            bundle = fetch_repository_sources(resolved.full_name, auth)
            _print(
                prepare_job(
                    settings,
                    resolved,
                    bundle,
                    publish_mode=publish_mode,
                    replace_legacy=args.replace_legacy,
                )
            )
            return 0

        if args.command == "finalize":
            if settings.notes_is_fallback:
                _print(_configuration_required(settings))
                return 0
            _print(finalize_job(settings, Path(args.job_dir), replace_legacy=args.replace_legacy))
            return 0

    except GitHubFetchError as exc:
        _print({"status": exc.code, "error": str(exc), "http_status": exc.status})
        return 0 if exc.code in {"auth_required", "auth_invalid", "rate_limited_or_forbidden"} else 2
    except ConfigurationError as exc:
        _print({"status": exc.code, "error": str(exc)})
        return 0
    except Exception as exc:
        _print({"status": "error", "error": str(exc)})
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
