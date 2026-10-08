"""ODS V2.2 reading-layout one-time migration with strict preflight.

Renames only GitHub-Note/00-Inbox to 00-待整理 and the project preview
directory. Refreshes the owned ODS preview and installs only canonical
github-note.css. Keeps backups in the ignored project .runtime directory.
Does not touch formal Capture Notes, Research Packet or other CSS snippets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from github_learning.config import load_settings

PREVIEW = "ODS：把本地 AI 工具管起来（V2.2预览）.md"
EXPECTED_OLD_PREVIEW = "b909538899aef11f85ceb9da9baf8e4233c1733043fcc53e670c143daed93b3c"
EXPECTED_OLD_CSS = "fdd88b3757725c95b8c0bf1072a2883a4d21f072905d86f25c6e780e35a9239b"
HIDDEN_FOLDER_SELECTOR = '.nav-folder-title[data-path="GitHub-Note/_repo-data"]'


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str | None:
    return hash_bytes(path.read_bytes()) if path.is_file() else None


def fail(message: str) -> None:
    raise RuntimeError(message)


def safe_backup(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            fail(f"Backup conflict; will not overwrite: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
    if path.read_bytes() != payload:
        fail(f"Backup verification failed: {path}")


def safe_replace(path: Path, content: bytes) -> None:
    tmp = path.with_name(path.name + ".ods-v22.tmp")
    if tmp.exists():
        fail(f"Temporary file already exists: {tmp}")
    try:
        with tmp.open("xb") as handle:
            handle.write(content)
        if tmp.read_bytes() != content:
            fail(f"Temporary file verification failed: {tmp}")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    if path.read_bytes() != content:
        fail(f"Replacement verification failed: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    cfg = load_settings(ROOT)
    if not cfg.vault_root or not cfg.notes_subdir:
        fail("Vault configuration is missing")
    vault = cfg.vault_root
    if not (vault / ".obsidian").is_dir():
        fail("Configured Vault does not have .obsidian/")
    notes_root = (vault / cfg.notes_subdir).resolve()
    if cfg.notes_root.resolve() != notes_root:
        fail("This one-time migration requires the current direct_vault configuration")
    if cfg.notes_subdir.as_posix() != "GitHub-Note":
        fail("Unexpected notes_subdir, no changes made")

    project_root = ROOT / "notes" / "github"
    project_old, project_new = project_root / "00-Inbox", project_root / "00-待整理"
    vault_old, vault_new = notes_root / "00-Inbox", notes_root / "00-待整理"
    source_css = ROOT.parent / "obsidian-learning-snippets" / "snippets" / "github-note.css"
    target_css = vault / ".obsidian" / "snippets" / "github-note.css"
    appearances = vault / ".obsidian" / "appearance.json"
    if not source_css.is_file() or not target_css.is_file():
        fail("Canonical or installed github-note.css does not exist")
    if target_css.is_symlink():
        fail("Installed CSS is a symlink; refusing to write into it")
    source_css_content = source_css.read_bytes()
    current_css_content = target_css.read_bytes()
    new_css_hash = hash_bytes(source_css_content)
    old_css_hash = hash_bytes(current_css_content)
    if HIDDEN_FOLDER_SELECTOR.encode() not in source_css_content or b"display: none !important" not in source_css_content:
        fail("Canonical CSS is missing the exact GitHub-Note data-folder hide rule")
    if old_css_hash not in {EXPECTED_OLD_CSS, new_css_hash}:
        fail("Installed CSS contains unknown changes; refusing to overwrite")
    enabled = json.loads(appearances.read_text(encoding="utf-8-sig"))
    if "github-note" not in (enabled.get("enabledCssSnippets") or []):
        fail("github-note CSS snippet is not enabled in Obsidian")
    data_image = notes_root / "_repo-data" / "Osmantic" / "ODS" / "media" / "readme-first-f9c72d216f56.png"
    if not data_image.is_file():
        fail("Existing ODS image is missing; refusing to migrate preview")

    originals_present = project_old.is_dir() and vault_old.is_dir()
    migrated_present = project_new.is_dir() and vault_new.is_dir()
    if originals_present == migrated_present:
        fail("Old and new folder states are inconsistent (or both exist); manual review required")
    if originals_present and (project_new.exists() or vault_new.exists()):
        fail("Destination folder exists; will not merge or overwrite folders")
    if migrated_present and (project_old.exists() or vault_old.exists()):
        fail("Old folder was recreated; will not proceed")

    source_dir = project_old if originals_present else project_new
    vault_dir = vault_old if originals_present else vault_new
    source_preview = source_dir / PREVIEW
    vault_preview = vault_dir / PREVIEW
    if not source_preview.is_file() or not vault_preview.is_file():
        fail("Source or Vault ODS preview missing")
    planned_content = source_preview.read_bytes()
    required = ("## 仓库自己强调的七项能力", "**本地模型推理**",
                "**ChatGPT 风格的 Web 界面**", "**统一控制面板**",
                "**语音、Agent 与工作流**", "**RAG 与搜索**",
                "**图像生成**", "**隐私与运维**",
                "下载模型与容器镜像", "遥测", "官方 FAQ")
    source_str = planned_content.decode("utf-8")
    if any(word not in source_str for word in required):
        fail("ODS preview has not incorporated the pinned README highlights and privacy exceptions")
    existing_preview = vault_preview.read_bytes()
    current_preview_hash = hash_bytes(existing_preview)
    if originals_present:
        if current_preview_hash != EXPECTED_OLD_PREVIEW:
            fail("Vault ODS preview has been manually changed. Do not overwrite it")
    elif existing_preview != planned_content:
        fail("Migrated Vault preview differs from project source; manual inspection needed")

    back = ROOT / ".runtime" / "ods-v22-layout-backup"
    if args.check:
        print(json.dumps({
            "status": "ready" if originals_present else "already_applied",
            "vault": str(vault),
            "project_rename": "00-Inbox -> 00-待整理" if originals_present else "already_renamed",
            "vault_rename": "00-Inbox -> 00-待整理" if originals_present else "already_renamed",
            "preview": PREVIEW,
            "preview_update": originals_present,
            "old_preview_hash": current_preview_hash,
            "css_action": "install_updated_github-note_only" if old_css_hash != new_css_hash else "already_installed",
            "css_enabled": True,
            "data_image_kept": data_image.is_file(),
            "css_original_hash": old_css_hash,
        }, ensure_ascii=False, indent=2))
        return

    # All checks complete before first mutation. Back up old Vault note/CSS.
    if originals_present:
        safe_backup(back / "ODS-V2.2-before-layout.md", existing_preview)
        project_old.rename(project_new)
        vault_old.rename(vault_new)
        safe_replace(vault_new / PREVIEW, planned_content)
    if old_css_hash != new_css_hash:
        safe_backup(back / "github-note-before-hide.css", current_css_content)
        safe_replace(target_css, source_css_content)

    if project_old.exists() or vault_old.exists() or (vault_new / PREVIEW).read_bytes() != (project_new / PREVIEW).read_bytes():
        fail("Post-migration directory or content verification failed")
    if target_css.read_bytes() != source_css_content or not data_image.is_file():
        fail("CSS or original data-image verification failed")

    print(json.dumps({
        "status": "applied",
        "vault_preview": str(vault_new / PREVIEW),
        "project_preview": str(project_new / PREVIEW),
        "css_installed": str(target_css),
        "css_source_hash": new_css_hash,
        "backups": str(back),
        "data_folder_remains_on_disk": True,
        "other_snippets_untouched": True
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"LAYOUT_MIGRATION_BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
