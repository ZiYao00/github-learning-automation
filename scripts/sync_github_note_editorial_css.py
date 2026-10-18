"""Safely sync only github-note.css v0.4 to the configured Obsidian Vault.

The verified installed github-note.css v0.3 hash is pinned as the upgrade base.
Other snippets, note files, and the Research Packet are read-only.
Usage:
  py -3.12 scripts/sync_github_note_editorial_css.py --check
  py -3.12 scripts/sync_github_note_editorial_css.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from github_learning.config import load_settings
from github_learning.style_sources import resolve_css_source

BASELINE_V03_HASH = "159bd26087a731b1a69eaf057fe19ead5b675d8280f3011d959d517f282dd433"


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def hash_file(path: Path) -> str | None:
    return sha(path.read_bytes()) if path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--styles-root", type=Path, help="Shared CSS source checkout; otherwise OBSIDIAN_STYLES_ROOT")
    args = parser.parse_args()

    settings = load_settings(ROOT)
    vault = settings.vault_root
    if not vault or str(settings.notes_subdir).replace("\\", "/") != "GitHub-Note":
        raise RuntimeError("This controlled update requires the confirmed GitHub-Note Vault mapping")
    installed_dir = vault / ".obsidian" / "snippets"
    source_file = resolve_css_source(ROOT, "github-note.css", styles_root=args.styles_root)
    installed_file = installed_dir / "github-note.css"
    appearance_file = vault / ".obsidian" / "appearance.json"
    if not source_file.is_file() or not installed_file.is_file() or not appearance_file.is_file():
        raise RuntimeError("Canonical CSS, installed CSS, or appearance.json is missing")
    if installed_dir.is_symlink() or installed_file.is_symlink() or (hasattr(installed_dir, "is_junction") and installed_dir.is_junction()):
        raise RuntimeError("Refusing to write through a snippet symlink/Junction")
    appearance = json.loads(appearance_file.read_text(encoding="utf-8-sig"))
    if "github-note" not in appearance.get("enabledCssSnippets", []):
        raise RuntimeError("The GitHub Note snippet is disabled in Obsidian")
    original_bytes = installed_file.read_bytes()
    source_bytes = source_file.read_bytes()
    existing_hash, source_hash = sha(original_bytes), sha(source_bytes)
    if b"Learning Lab Extension v0.4" not in source_bytes or b"GitHub-Note/_repo-data" not in source_bytes:
        raise RuntimeError("Canonical CSS is not the expected scoped v0.4 extension")
    if existing_hash not in {BASELINE_V03_HASH, source_hash}:
        raise RuntimeError(f"Installed CSS has unknown modifications (SHA256={existing_hash}); no update")
    other_before = {path.name: hash_file(path) for path in installed_dir.glob("*.css") if path.name != "github-note.css"}
    if any(value is None for value in other_before.values()):
        raise RuntimeError("Expected shared CSS snippets are missing; no update")

    backup = ROOT / ".runtime" / "github-note-css-backups" / f"github-note-{existing_hash[:16]}.css"
    update_needed = existing_hash != source_hash
    if args.check:
        print(json.dumps({
            "status": "ready" if update_needed else "already_synced",
            "installed_css": str(installed_file),
            "existing_hash": existing_hash,
            "source_hash": source_hash,
            "backup_when_applied": str(backup) if update_needed else None,
            "other_snippets": other_before,
        }, ensure_ascii=False, indent=2))
        return 0

    if update_needed:
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            if backup.read_bytes() != original_bytes:
                raise RuntimeError("Backup filename collision; no update")
        else:
            with backup.open("xb") as handle:
                handle.write(original_bytes)
        if backup.read_bytes() != original_bytes:
            raise RuntimeError("Original CSS backup verification failed; no update")
        temp = installed_file.with_name("github-note.css.v04-update.tmp")
        if temp.exists():
            raise RuntimeError("A CSS update temp file already exists; manual inspection needed")
        try:
            with temp.open("xb") as handle:
                handle.write(source_bytes)
            if temp.read_bytes() != source_bytes:
                raise RuntimeError("Staged CSS integrity failure")
            os.replace(temp, installed_file)
        finally:
            if temp.exists():
                temp.unlink()

    if hash_file(installed_file) != source_hash:
        raise RuntimeError("Installed CSS mismatch after sync; backup available for recovery")
    other_after = {path.name: hash_file(path) for path in installed_dir.glob("*.css") if path.name != "github-note.css"}
    if other_before != other_after:
        raise RuntimeError("Unrelated snippet changed during sync")
    print(json.dumps({
        "status": "synced" if update_needed else "already_synced",
        "css_sha256": source_hash,
        "installed_css": str(installed_file),
        "previous_css_backup": str(backup) if update_needed else None,
        "other_snippets_unchanged": True,
        "user_notes_untouched": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"GH_NOTE_CSS_SYNC_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
