"""Resolve optional shared Obsidian CSS sources without sibling-repo assumptions.

Routine note generation uses only the consumer's CSS contract and installed
Vault snippets; a source checkout is needed only for specialist maintenance.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


class StyleSourceError(RuntimeError):
    pass


def resolve_css_source(
    project_root: Path,
    css_name: str,
    *,
    styles_root: str | Path | None = None,
    optional: bool = False,
) -> Path | None:
    """Use an explicit provider checkout or OBSIDIAN_STYLES_ROOT.

    Never search adjacent directories, and never treat installed Vault snippets
    as the authoritative upstream source. The provider manifest is authoritative
    for source files; the consumer contract limits which names can be requested.
    """
    config_file = project_root / "config" / "obsidian-style.json"
    if not config_file.is_file():
        raise StyleSourceError("Missing config/obsidian-style.json")
    contract = json.loads(config_file.read_text(encoding="utf-8"))
    required = [contract.get("core"), *(contract.get("extensions") or [])]
    allowed_names = {Path(path).name for path in required if isinstance(path, str)}
    if not re.fullmatch(r"[a-zA-Z0-9-]+[.]css", css_name) or css_name not in allowed_names:
        raise StyleSourceError(f"CSS is not declared by this consumer: {css_name}")

    selected = str(styles_root).strip() if styles_root is not None else os.getenv("OBSIDIAN_STYLES_ROOT", "").strip()
    if not selected:
        if optional:
            return None
        raise StyleSourceError(
            "Shared styles checkout is not configured. Use --styles-root PATH or "
            "set OBSIDIAN_STYLES_ROOT. Ordinary note generation does not need it."
        )
    provider = Path(selected).expanduser().resolve()
    manifest_path = provider / "manifest.json"
    if not manifest_path.is_file():
        raise StyleSourceError(f"Shared styles manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise StyleSourceError("Unsupported shared styles manifest")
    entries = [manifest.get("core"), *(manifest.get("extensions") or [])]
    matches = [
        e["path"]
        for e in entries
        if isinstance(e, dict)
        and isinstance(e.get("path"), str)
        and e["path"].startswith("snippets/")
        and Path(e["path"]).name == css_name
    ]
    if len(matches) != 1 or not re.fullmatch(r"snippets/[a-zA-Z0-9-]+[.]css", matches[0]):
        raise StyleSourceError(f"CSS is not uniquely declared by provider: {css_name}")
    source = provider / matches[0]
    if not source.is_file():
        raise StyleSourceError(f"Shared stylesheet missing: {source}")
    return source
