from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

LOCAL_CONFIG = Path("config/local.json")
DEFAULT_NOTES_SUBDIR = Path("GitHub-Note")


class ConfigurationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Settings:
    project_root: Path
    notes_root: Path
    runtime_root: Path
    local_config_path: Path
    notes_is_fallback: bool
    vault_root: Path | None = None
    notes_subdir: Path | None = None
    notes_source: str = "fallback"
    research_root: Path | None = None
    research_source: str = "unconfigured"


def _safe_relative(value: str) -> Path:
    path = Path(value.strip())
    if not value.strip() or path.is_absolute() or path == Path(".") or ".." in path.parts:
        raise ConfigurationError("notes_subdir_invalid", "notes_subdir 必须是 Vault 内的安全相对子目录。")
    return path


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else project_root / path


def _require_directory(path: Path, *, code: str, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ConfigurationError(code, f"{label}不存在：{resolved}")
    if not resolved.is_dir():
        raise ConfigurationError(code, f"{label}不是目录：{resolved}")
    return resolved


def _require_vault(path: Path) -> Path:
    resolved = _require_directory(path, code="vault_root_missing", label="Vault 目录")
    if not (resolved / ".obsidian").is_dir():
        raise ConfigurationError("vault_root_not_obsidian", f"未在该目录发现 .obsidian：{resolved}")
    return resolved


def _load_local(project_root: Path) -> tuple[Path, dict[str, str]]:
    path = project_root / LOCAL_CONFIG
    if not path.exists():
        return path, {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError("local_config_invalid_json", f"config/local.json 不是有效 JSON：{path}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("local_config_invalid_type", "config/local.json 必须是 JSON 对象。")
    allowed = {"notes_root", "vault_root", "notes_subdir", "research_root"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigurationError("local_config_unknown_key", "config/local.json 存在未知字段：" + ", ".join(unknown))
    values: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("local_config_invalid_value", f"config/local.json 的 {key} 必须是非空字符串。")
        values[key] = value.strip()
    if "notes_root" in values and ({"vault_root", "notes_subdir"} & values.keys()):
        raise ConfigurationError("local_config_notes_conflict", "notes_root 不能与 vault_root / notes_subdir 同时使用。")
    if "notes_subdir" in values and "vault_root" not in values:
        raise ConfigurationError("local_config_subdir_without_vault", "配置 notes_subdir 时必须同时配置 vault_root。")
    return path, values


def _resolve_research_root(project_root: Path, local: dict[str, str]) -> tuple[Path | None, str]:
    env_research = os.environ.get("GITHUB_LEARNING_RESEARCH_ROOT")
    if env_research:
        return (
            _require_directory(
                _resolve_path(project_root, env_research),
                code="research_root_missing",
                label="Research 目录",
            ),
            "environment",
        )
    if local.get("research_root"):
        return (
            _require_directory(
                _resolve_path(project_root, local["research_root"]),
                code="research_root_missing",
                label="Research 目录",
            ),
            "local",
        )
    return None, "unconfigured"


def load_settings(project_root: Path) -> Settings:
    project_root = project_root.resolve()
    local_path, local = _load_local(project_root)
    research_root, research_source = _resolve_research_root(project_root, local)
    env_root = os.environ.get("GITHUB_LEARNING_NOTES_ROOT")
    env_vault = os.environ.get("GITHUB_LEARNING_VAULT_ROOT")
    env_subdir = os.environ.get("GITHUB_LEARNING_NOTES_SUBDIR")
    runtime_root = project_root / ".runtime" / "github-learning"

    if env_root and (env_vault or env_subdir):
        raise ConfigurationError(
            "environment_notes_conflict",
            "GITHUB_LEARNING_NOTES_ROOT 不能与 GITHUB_LEARNING_VAULT_ROOT / GITHUB_LEARNING_NOTES_SUBDIR 同时设置。",
        )
    if env_subdir and not env_vault:
        raise ConfigurationError(
            "environment_subdir_without_vault",
            "GITHUB_LEARNING_NOTES_SUBDIR 需要同时设置 GITHUB_LEARNING_VAULT_ROOT。",
        )

    if env_root:
        notes_root = _require_directory(
            _resolve_path(project_root, env_root),
            code="notes_root_missing",
            label="笔记目录",
        )
        return Settings(
            project_root,
            notes_root,
            runtime_root,
            local_path,
            False,
            notes_source="environment_notes_root",
            research_root=research_root,
            research_source=research_source,
        )
    if env_vault:
        vault_root = _require_vault(_resolve_path(project_root, env_vault))
        notes_subdir = _safe_relative(env_subdir or str(DEFAULT_NOTES_SUBDIR))
        return Settings(
            project_root,
            vault_root / notes_subdir,
            runtime_root,
            local_path,
            False,
            vault_root,
            notes_subdir,
            "environment_vault",
            research_root,
            research_source,
        )
    if local.get("notes_root"):
        notes_root = _require_directory(
            _resolve_path(project_root, local["notes_root"]),
            code="notes_root_missing",
            label="笔记目录",
        )
        return Settings(
            project_root,
            notes_root,
            runtime_root,
            local_path,
            False,
            notes_source="local_notes_root",
            research_root=research_root,
            research_source=research_source,
        )
    if local.get("vault_root"):
        vault_root = _require_vault(_resolve_path(project_root, local["vault_root"]))
        notes_subdir = _safe_relative(local.get("notes_subdir", str(DEFAULT_NOTES_SUBDIR)))
        return Settings(
            project_root,
            vault_root / notes_subdir,
            runtime_root,
            local_path,
            False,
            vault_root,
            notes_subdir,
            "local_vault",
            research_root,
            research_source,
        )

    notes_root = project_root / "notes" / "github" / "00-Inbox"
    return Settings(
        project_root,
        notes_root,
        runtime_root,
        local_path,
        True,
        research_root=research_root,
        research_source=research_source,
    )


def _write_local_atomic(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def configure_notes(
    project_root: Path,
    *,
    vault_root: Path | None = None,
    notes_subdir: str | None = None,
    notes_root: Path | None = None,
    research_root: Path | None = None,
) -> Path:
    project_root = project_root.resolve()
    if vault_root is not None and notes_root is not None:
        raise ConfigurationError("configure_conflict", "vault_root 与 notes_root 只能选择一种配置方式。")
    if vault_root is None and notes_root is None and research_root is None:
        raise ConfigurationError("configure_missing_target", "必须提供 vault_root、notes_root 或 research_root。")

    path, current = _load_local(project_root)
    payload = dict(current)

    if vault_root is not None:
        validated_vault = _require_vault(vault_root)
        normalized_subdir = _safe_relative(notes_subdir or str(DEFAULT_NOTES_SUBDIR))
        payload.pop("notes_root", None)
        payload["vault_root"] = str(validated_vault)
        payload["notes_subdir"] = str(normalized_subdir)
    elif notes_root is not None:
        validated_root = _require_directory(notes_root, code="notes_root_missing", label="笔记目录")
        payload.pop("vault_root", None)
        payload.pop("notes_subdir", None)
        payload["notes_root"] = str(validated_root)
    elif notes_subdir is not None:
        raise ConfigurationError("configure_subdir_without_vault", "仅更新 notes_subdir 时必须同时提供 vault_root。")

    if research_root is not None:
        validated_research = _require_directory(
            research_root,
            code="research_root_missing",
            label="Research 目录",
        )
        payload["research_root"] = str(validated_research)

    _write_local_atomic(path, payload)
    return path
