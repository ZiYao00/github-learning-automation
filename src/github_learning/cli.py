from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .auth import probe_rate_limit, resolve_github_auth
from .config import ConfigurationError, configure_defaults, configure_notes, load_settings
from .github_client import GitHubFetchError, fetch_repository_sources
from .input_resolver import resolve_repository
from .lifecycle import (
    EDITORIAL_CONTRACT_VERSION, CURRENT_JOB_VERSION,
    finalize_job, preflight_publish, prepare_job, resume_prepare,
)
from .research_packet import ResearchPacketError


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


def _obsidian_mapping(settings) -> dict[str, Any]:
    if settings.vault_root is None or settings.notes_subdir is None:
        return {"status": "not_configured"}

    display_path = settings.vault_root / settings.notes_subdir
    if settings.notes_root == display_path:
        return {
            "status": "direct_vault",
            "display_path": str(display_path),
            "notes_root": str(settings.notes_root),
        }
    if not display_path.exists():
        return {
            "status": "mapping_missing",
            "display_path": str(display_path),
            "notes_root": str(settings.notes_root),
            "message": "建议把 Vault 子目录建立为指向 notes_root 的 Junction；缺少映射不阻塞项目内存储。",
        }
    try:
        mapping_ok = display_path.resolve() == settings.notes_root.resolve()
    except OSError:
        mapping_ok = False
    return {
        "status": "ok" if mapping_ok else "mapping_mismatch",
        "display_path": str(display_path),
        "notes_root": str(settings.notes_root),
    }


def _needs_onboarding(settings) -> bool:
    return settings.notes_is_fallback or settings.research_is_fallback


def _onboarding_payload(settings) -> dict[str, Any]:
    auth = resolve_github_auth()
    actions: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []

    if settings.notes_is_fallback and settings.research_is_fallback:
        actions.append(
            {
                "code": "storage_choice_required",
                "message": "首次使用请确认存储位置。若不指定自定义路径，可接受项目内默认目录。",
                "defaults": {
                    "notes_root": str(settings.notes_root),
                    "research_root": str(settings.research_root),
                },
                "accept_defaults": "python scripts/github_learning.py configure --use-defaults",
            }
        )
    else:
        if settings.notes_is_fallback:
            actions.append(
                {
                    "code": "notes_root_required",
                    "message": "尚未确认笔记物理目录；可指定 notes_root，或显式接受项目默认目录。",
                    "default": str(settings.notes_root),
                }
            )
        if settings.research_is_fallback:
            actions.append(
                {
                    "code": "research_root_required",
                    "message": "尚未确认长期 Research 目录；可指定自定义目录，或使用项目内 research/github。",
                    "default": str(settings.research_root),
                }
            )

    if not auth.authenticated:
        actions.append(
            {
                "code": "github_auth_recommended",
                "message": "未检测到 GitHub 登录；推荐先运行 gh auth login。匿名模式需要显式允许。",
            }
        )

    mapping = _obsidian_mapping(settings)
    if mapping["status"] in {"mapping_missing", "mapping_mismatch"}:
        warnings.append(
            {
                "code": f"obsidian_notes_{mapping['status']}",
                "message": "Obsidian 映射未就绪；真实文件仍以 notes_root 为准，不影响 Research Packet。",
            }
        )

    if _needs_onboarding(settings):
        status = "action_required"
    elif not auth.authenticated:
        status = "auth_recommended"
    else:
        status = "ready"

    return {
        "status": status,
        "ready": status == "ready",
        "project_root": str(settings.project_root),
        "local_config": str(settings.local_config_path),
        "local_config_exists": settings.local_config_path.is_file(),
        "notes_root": str(settings.notes_root),
        "notes_source": settings.notes_source,
        "research_root": str(settings.research_root) if settings.research_root else "",
        "research_source": settings.research_source,
        "vault_root": str(settings.vault_root) if settings.vault_root else "",
        "notes_subdir": str(settings.notes_subdir) if settings.notes_subdir else "",
        "obsidian_mapping": mapping,
        "github_auth": {"authenticated": auth.authenticated, "source": auth.source},
        "actions": actions,
        "warnings": warnings,
    }


def _doctor_payload(settings, *, check_api: bool = False) -> dict[str, Any]:
    payload = _onboarding_payload(settings)
    issues: list[dict[str, str]] = []
    if settings.notes_is_fallback:
        issues.append(
            {
                "code": "notes_configuration_required",
                "message": "笔记目录尚未由用户确认；当前只显示项目内建议默认值。",
            }
        )
    if settings.research_is_fallback:
        issues.append(
            {
                "code": "research_configuration_required",
                "message": "Research 目录尚未由用户确认；当前只显示项目内建议默认值。",
            }
        )
    payload["issues"] = issues
    payload["editorial_contract_version"] = EDITORIAL_CONTRACT_VERSION
    payload["new_job_version"] = CURRENT_JOB_VERSION
    if check_api:
        payload["github_api"] = probe_rate_limit(resolve_github_auth())
    return payload


def _onboarding_required(settings) -> dict[str, Any]:
    payload = _onboarding_payload(settings)
    return {
        "status": "onboarding_required",
        "message": "首次采集前请先确认本机存储路径。可以接受项目默认目录，也可以指定自定义目录。",
        "notes_root": str(settings.notes_root),
        "research_root": str(settings.research_root) if settings.research_root else "",
        "local_config": str(settings.local_config_path),
        "actions": payload["actions"],
        "warnings": payload["warnings"],
    }


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(prog="github-learning", description="GitHub 仓库长期收藏与学习笔记")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="采集 GitHub 仓库资料、归档 Research Packet 并创建 Agent 分析任务")
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
    p_prepare.add_argument(
        "--restart-job",
        action="store_true",
        help="显式放弃同仓库未完成 Job 并重新采集；旧 Job 保留且标记 superseded。",
    )

    p_finalize = sub.add_parser("finalize", help="验证 Agent 分析并发布 Capture Note")
    p_finalize.add_argument("job_dir")
    p_finalize.add_argument(
        "--replace-legacy",
        action="store_true",
        help="显式允许刷新缺少 managed marker 的旧版笔记；原文会先备份到 runtime job。",
    )

    sub.add_parser("onboarding", help="首次使用时确认存储位置、Vault 映射与 GitHub 登录")

    p_doctor = sub.add_parser("doctor", help="检查笔记目录、Research 目录、GitHub 认证与输出环境")
    p_doctor.add_argument("--check-api", action="store_true", help="额外探测 GitHub API rate limit。")

    p_configure = sub.add_parser("configure", help="创建或增量更新 config/local.json")
    p_configure.add_argument(
        "--use-defaults",
        action="store_true",
        help="显式接受项目内默认目录 notes/github + research/github；只补齐缺失项。",
    )
    target = p_configure.add_mutually_exclusive_group(required=False)
    target.add_argument("--vault-root", type=Path, help="Obsidian Vault 根目录。")
    target.add_argument("--notes-root", type=Path, help="直接指定笔记输出目录。")
    p_configure.add_argument("--notes-subdir", default=None, help="Vault 内相对子目录；与 --vault-root 一起使用。")
    p_configure.add_argument("--research-root", type=Path, help="长期 Research Packet 根目录；目录必须已存在。")

    args = parser.parse_args()
    root = _project_root()

    try:
        if args.command == "configure":
            has_custom = any(
                value is not None
                for value in (args.vault_root, args.notes_root, args.research_root, args.notes_subdir)
            )
            if args.use_defaults and has_custom:
                raise ConfigurationError(
                    "configure_conflict",
                    "--use-defaults 不能与自定义路径参数同时使用；先接受默认值，再单独增量配置 Vault 即可。",
                )
            if args.use_defaults:
                path = configure_defaults(root)
            else:
                path = configure_notes(
                    root,
                    vault_root=args.vault_root,
                    notes_subdir=args.notes_subdir,
                    notes_root=args.notes_root,
                    research_root=args.research_root,
                )
            settings = load_settings(root)
            _print(
                {
                    "status": "configured",
                    "local_config": str(path),
                    "notes_root": str(settings.notes_root),
                    "notes_source": settings.notes_source,
                    "research_root": str(settings.research_root) if settings.research_root else "",
                    "research_source": settings.research_source,
                }
            )
            return 0

        settings = load_settings(root)

        if args.command == "onboarding":
            _print(_onboarding_payload(settings))
            return 0

        if args.command == "doctor":
            _print(_doctor_payload(settings, check_api=args.check_api))
            return 0

        if args.command == "prepare":
            if _needs_onboarding(settings):
                _print(_onboarding_required(settings))
                return 0

            auth = resolve_github_auth()
            if not auth.authenticated and not args.allow_anonymous:
                _print(
                    {
                        "status": "auth_recommended",
                        "message": "未检测到 GitHub 登录；为避免匿名额度导致中途失败，本次未开始采集。",
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
                restart_job=args.restart_job,
            )
            if preflight["status"] == "in_progress":
                _print(resume_prepare(settings, Path(str(preflight["job_dir"]))))
                return 0
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
                    restart_job=args.restart_job,
                )
            )
            return 0

        if args.command == "finalize":
            if _needs_onboarding(settings):
                _print(_onboarding_required(settings))
                return 0
            _print(finalize_job(settings, Path(args.job_dir), replace_legacy=args.replace_legacy))
            return 0

    except GitHubFetchError as exc:
        _print({"status": exc.code, "error": str(exc), "http_status": exc.status})
        return 0 if exc.code in {
            "auth_required",
            "auth_invalid",
            "rate_limited_or_forbidden",
            "private_repository_blocked",
        } else 2
    except ResearchPacketError as exc:
        _print({"status": exc.code, "error": str(exc)})
        return 0
    except ConfigurationError as exc:
        _print({"status": exc.code, "error": str(exc)})
        return 0
    except Exception as exc:
        _print({"status": "error", "error": str(exc)})
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
