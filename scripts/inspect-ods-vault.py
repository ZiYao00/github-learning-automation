"""Read-only, narrow preflight for the ODS reading layout migration.
Does not read personal note bodies or modify the Vault.
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
from github_learning.style_sources import resolve_css_source

def digest(p: Path | None) -> str | None:
    if p is None or not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()

def folder(p: Path) -> dict:
    return {
        "exists": p.is_dir(),
        "entries": sorted(x.name for x in p.iterdir()) if p.is_dir() else [],
        "reparse_point": p.is_symlink(),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--styles-root", type=Path, help="Shared CSS source checkout; otherwise OBSIDIAN_STYLES_ROOT")
    args = parser.parse_args()
    cfg = load_settings(ROOT)
    if not cfg.vault_root:
        raise SystemExit("Vault is unconfigured")
    notes_root = cfg.notes_root
    vault = cfg.vault_root
    if not (vault / ".obsidian").is_dir():
        raise SystemExit("Not an Obsidian Vault")
    css_source = resolve_css_source(ROOT, "github-note.css", styles_root=args.styles_root, optional=True)
    css_installed = vault / ".obsidian" / "snippets" / "github-note.css"
    snippets = []
    for p in [vault / ".obsidian" / "appearance.json",vault / ".obsidian" / "app.json"]:
        if p.is_file():
            data=json.loads(p.read_text(encoding="utf-8-sig"))
            if isinstance(data,dict):
                snippets.append({"file":p.name,"enabledCssSnippets":data.get("enabledCssSnippets","unavailable")})
    title="ODS：把本地 AI 工具管起来（V2.2预览）.md"
    print(json.dumps({
      "vault_mapping": "direct" if notes_root.resolve() == (vault / str(cfg.notes_subdir)).resolve() else "other",
      "vault_old": folder(notes_root/"00-Inbox"),
      "vault_new": folder(notes_root/"00-待整理"),
      "project_old": folder(ROOT/"notes/github/00-Inbox"),
      "project_new": folder(ROOT/"notes/github/00-待整理"),
      "preview_hashes":{
        "source_old":digest(ROOT/"notes/github/00-Inbox"/title),
        "vault_old":digest(notes_root/"00-Inbox"/title),
        "vault_new":digest(notes_root/"00-待整理"/title),
      },
      "css_source_hash":digest(css_source),
      "css_source_configured":css_source is not None,
      "css_installed_hash":digest(css_installed),
      "css_enabled": snippets,
    },ensure_ascii=False,indent=2))
if __name__=="__main__":main()
