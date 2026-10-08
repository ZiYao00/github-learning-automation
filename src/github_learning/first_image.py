"""One bounded, revision-pinned README image for a human-readable Capture Note.

This is deliberately NOT a general media downloader. The immutable Research Packet
continues to index binary files without archiving them. Only one public, same-repo,
README image may be materialized in the reading layer.
"""
from __future__ import annotations

import hashlib
import html
import json
import posixpath
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

IMAGE_MAX_BYTES = 5 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_HTML_IMAGE = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
_HTML_SRC = re.compile(r"""\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""", re.IGNORECASE)
_MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]\n]*)\]\(\s*(?P<target><[^>]+>|[^)\n]+)\s*\)")
_FENCED_CODE = re.compile(r"(?m)^\s*(?:`{3,}|~{3,})[^\n]*\n.*?^\s*(?:`{3,}|~{3,})\s*$", re.DOTALL)
_BADGE_ALT = re.compile(r"^(?:badge|build|ci|status|tests?|coverage|stars?|license|version|downloads?)\b", re.I)


def first_readme_image(readme: str) -> str | None:
    """Return the FIRST meaningful image in README display order (not Git tree order).

    Shields/badges and fenced code samples are not content images. A first content
    image that cannot be safely materialized is NOT replaced by a later image.
    """
    no_code = _FENCED_CODE.sub(lambda m: "\n" * m.group(0).count("\n"), readme)
    no_code = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), no_code, flags=re.DOTALL)
    candidates: list[tuple[int, str, str]] = []
    for match in _HTML_IMAGE.finditer(no_code):
        src = _HTML_SRC.search(match.group(0))
        if src:
            candidate = next((v for v in src.groups() if v), "")
            alt = re.search(r"""\balt\s*=\s*(?:"([^"]*)"|'([^']*)')""", match.group(0), re.I)
            alt_text = next((value for value in alt.groups() if value is not None), "") if alt else ""
            candidates.append((match.start(), html.unescape(candidate), html.unescape(alt_text)))
    for match in _MARKDOWN_IMAGE.finditer(no_code):
        target = match.group("target").strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        else:
            target = target.split(' "', 1)[0].split(" '", 1)[0].strip()
        candidates.append((match.start(), html.unescape(target), match.group("alt")))
    for _, src, alt in sorted(candidates):
        url = urllib.parse.urlsplit(src)
        hostname = (url.hostname or "").lower()
        if hostname in {"img.shields.io", "shields.io", "github.com"} and "/badge/" in url.path.lower():
            continue
        if hostname in {"img.shields.io", "shields.io"} or _BADGE_ALT.match(alt.strip()):
            continue
        if src:
            return src
    return None


def _repo_relative_path(image: str, full_name: str, readme_path: str) -> str | None:
    parsed = urllib.parse.urlsplit(image)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != "https" or parsed.netloc.lower() != "raw.githubusercontent.com":
            return None
        parts = urllib.parse.unquote(parsed.path).lstrip("/").split("/")
        owner, repo = full_name.split("/", 1)
        if len(parts) < 4 or [p.lower() for p in parts[:2]] != [owner.lower(), repo.lower()]:
            return None
        # The URL's ref may be a branch, but actual bytes will be pinned to
        # the captured commit and verified against that snapshot's media index.
        candidate = "/".join(parts[3:])
    else:
        if image.startswith("//") or parsed.path.startswith("\\") or "\\" in parsed.path:
            return None
        path = urllib.parse.unquote(parsed.path)
        if not path or "\x00" in path:
            return None
        candidate = path.lstrip("/") if path.startswith("/") else posixpath.join(posixpath.dirname(readme_path), path)
    candidate = posixpath.normpath(candidate)
    if candidate in {"", ".", ".."} or candidate.startswith("../") or candidate.startswith("/") or ":" in candidate:
        return None
    if Path(candidate).suffix.lower() not in SUPPORTED_EXTENSIONS:
        return None
    return candidate


def _image_bytes_valid(path: str, data: bytes) -> bool:
    suffix = Path(path).suffix.lower()
    return (
        (suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (suffix in {".jpg", ".jpeg"} and data.startswith(b"\xff\xd8\xff"))
        or (suffix == ".gif" and data[:6] in {b"GIF87a", b"GIF89a"})
        or (suffix == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _readme_from_job(job_dir: Path) -> tuple[str, str]:
    manifest = json.loads((job_dir / "source_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("sources", []):
        if entry.get("kind") != "readme":
            continue
        saved = str(entry.get("saved_as") or "")
        if not saved.startswith("sources/") or ".." in Path(saved).parts:
            return "", ""
        return str(entry.get("path") or "README.md"), (job_dir / saved).read_text(encoding="utf-8")
    return "", ""


def materialize_first_image(
    settings: Any,
    job_dir: Path,
    job: dict[str, Any],
    *,
    fetch: Any = None,
) -> dict[str, str]:
    """Best-effort result: saved/no_image/unsupported/not_in_snapshot/unavailable.

    Never follow arbitrary README-hosted URLs and never replace differing files.
    A failed image must not block publication of the fact-checked note.
    """
    try:
        readme_path, readme = _readme_from_job(job_dir)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        return {"status": "unavailable", "reason": str(exc)[:250]}
    source = first_readme_image(readme) if readme else None
    if not source:
        return {"status": "no_image"}
    repo = str((job.get("repository") or {}).get("full_name") or "")
    revision = str(job.get("revision") or "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not re.fullmatch(r"[a-fA-F0-9]{40}", revision):
        return {"status": "unsupported", "source": source}
    rel = _repo_relative_path(source, repo, readme_path)
    if not rel:
        return {"status": "unsupported", "source": source}
    index_file = job_dir / "media-index.json"
    if not index_file.is_file():
        return {"status": "not_in_snapshot", "source": source}
    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
        entries = [e for e in index.get("entries", []) if e.get("path") == rel]
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        return {"status": "unavailable", "source": source, "reason": str(exc)[:250]}
    if len(entries) != 1:
        return {"status": "not_in_snapshot", "source": source}
    try:
        sha = str(entries[0].get("sha") or "").lower()
        size = int(entries[0].get("size") or 0)
    except (TypeError, ValueError, AttributeError):
        return {"status": "too_large_or_invalid", "source": source}
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not 0 < size <= IMAGE_MAX_BYTES:
        return {"status": "too_large_or_invalid", "source": source}
    owner, name = repo.split("/", 1)
    suffix = Path(rel).suffix.lower()
    filename = f"readme-first-{sha[:12]}{suffix}"
    base = settings.notes_root / "_repo-data" / owner / name
    dest = base / "media" / filename
    try:
        if dest.exists():
            data = dest.read_bytes()
        else:
            path = "/".join(urllib.parse.quote(p, safe="") for p in rel.split("/"))
            url = f"https://raw.githubusercontent.com/{owner}/{name}/{revision}/{path}"
            if fetch is None:
                req = urllib.request.Request(url, headers={"User-Agent": "github-learning-automation/first-image"})
                with urllib.request.urlopen(req, timeout=20) as response:
                    if urllib.parse.urlsplit(response.geturl()).hostname != "raw.githubusercontent.com":
                        return {"status": "unavailable", "source": source}
                    data = response.read(IMAGE_MAX_BYTES + 1)
            else:
                data = fetch(url)
        if len(data) != size or _git_blob_sha(data) != sha or not _image_bytes_valid(rel, data):
            return {"status": "invalid_image", "source": source}
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".tmp")
            if tmp.exists():
                return {"status": "unavailable", "source": source}
            try:
                tmp.write_bytes(data)
                tmp.replace(dest)
            finally:
                if tmp.exists():
                    tmp.unlink()
        subdir = str(settings.notes_subdir or "").replace("\\", "/").strip("/")
        vault_prefix = (subdir + "/") if settings.vault_root and subdir else ""
        rel_link = f"{vault_prefix}_repo-data/{owner}/{name}/media/{filename}"
        manifest = {
            "schema_version": 1,
            "repository": repo,
            "revision": revision,
            "source_readme": readme_path,
            "source_image": source,
            "repository_file": rel,
            "git_blob_sha": sha,
            "asset": f"media/{filename}",
            "policy": "only_first_non_badge_readme_image; no_video_or_gallery",
        }
        manifest_path = base / f"readme-first-{revision[:12]}.json"
        serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        if manifest_path.exists():
            if manifest_path.read_text(encoding="utf-8") != serialized:
                return {"status": "manifest_conflict", "source": source}
        else:
            manifest_path.write_text(serialized, encoding="utf-8")
        return {
            "status": "saved",
            "source": source,
            "link": f"![[{rel_link}|360]]",
            "repository_path": rel,
        }
    except (OSError, ValueError, TimeoutError, urllib.error.URLError) as exc:
        return {"status": "unavailable", "source": source, "reason": str(exc)[:250]}
