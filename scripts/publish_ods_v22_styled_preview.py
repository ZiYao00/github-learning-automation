"""Create an independent ODS V2.2 visual-enhanced Obsidian reading preview.

Based on the already-approved V2.2 preview; retains its seven-capability summary,
examples, caveats, first README image and factual status. Changes presentation by
turning only a source-verifiable author claim into a scoped gh-source Callout.

No new Capture Note identity, no alteration of ODS Golden Sample or old preview.
The output is create-only and idempotent; an existing differing file blocks.

Usage:
    py -3.12 scripts/publish_ods_v22_styled_preview.py --check
    py -3.12 scripts/publish_ods_v22_styled_preview.py --apply
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

REVISION = "9e59b2b86c96a9590b27b14219b070007093fad1"
ORIGINAL = "ODS：把本地 AI 工具管起来（V2.2预览）.md"
STYLED = "ODS：把本地 AI 工具管起来（V2.2视觉增强版）.md"
COVER = "![[GitHub-Note/_repo-data/Osmantic/ODS/media/readme-first-f9c72d216f56.png|360]]"

OLD_OPENING = (
    "**它对隐私的描述也值得单独记住。** 仓库作者表示，ODS 无须依赖云端服务或付费订阅即可运行；"
    "模型推理、聊天记录和个人文件保留在本机，并声称 ODS 不采集遥测数据。"
    "**但“本地运行”不等于默认完全离线**"
)
NEW_OPENING = (
    "**它对隐私的描述也值得单独记住。**\n\n"
    "> [!gh-source] 仓库官方原文 · [固定版本 README](https://github.com/Osmantic/ODS/blob/"
    + REVISION
    + "/README.md)\n"
    "> No cloud required. No subscriptions required.\n"
    ">\n"
    "> > 中文翻译（译文，非作者原文）：无需云端，也无需订阅。\n\n"
    "同一份 README 还表示，模型推理、聊天记录与个人文件保留在本机，并声称 ODS 不采集遥测数据。"
    "**但“本地运行”不等于默认完全离线**"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def one_replace(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise RuntimeError(f"Expected exactly one occurrence in approved source: {before[:48]}")
    return text.replace(before, after, 1)


def make_styled(original: str, archived_readme: str) -> str:
    statement = "No cloud required. No subscriptions required."
    if statement not in archived_readme:
        raise RuntimeError("The pinned source no longer contains this author statement")
    if f'revision: "{REVISION}"' not in original or f'packet_id: "Osmantic/ODS@{REVISION}"' not in original:
        raise RuntimeError("Unexpected version of ODS source note")
    if "  - learning-page\n  - github-note" not in original:
        raise RuntimeError("Original note does not declare the scoped GitHub Note CSS")
    if original.count(COVER) != 1:
        raise RuntimeError("ODS original cover image missing or duplicated")
    if "## 仓库自己强调的七项能力" not in original:
        raise RuntimeError("Approved core-feature section missing")
    if "\nrepo:" in original:
        raise RuntimeError("ODS preview unexpectedly has a managed repository identity")
    text = one_replace(
        original,
        'note_type: "editorial_v2_2_preview"',
        'note_type: "editorial_v2_2_visual_preview"',
    )
    text = one_replace(
        text,
        'title: "ODS：把本地 AI 工具管起来，而不只是跑一个模型"',
        'title: "ODS：把本地 AI 工具管起来，而不只是跑一个模型（视觉增强版）"',
    )
    text = one_replace(text, OLD_OPENING, NEW_OPENING)
    text = one_replace(
        text, "本页为单篇阅读样板；",
        "本页是 V2.2 独立视觉增强版，原版与 Golden Sample 保留不变；",
    )
    if text.count("> [!gh-source]") != 1 or "~~~prompt" in text:
        raise RuntimeError("Incorrect source or Prompt presentation in styled output")
    if text.count(COVER) != 1:
        raise RuntimeError("Styled note must preserve exactly one README first image")
    if text.count("## 仓库自己强调的七项能力") != 1:
        raise RuntimeError("The official capability overview was changed")
    for fact in ("Qwen3.5 2B", "ComfyUI", "GHSA-vqpg-pvjj-4cmq",
                 "Portal Agent 执行网络搜索", "## 原始资料", "## 用久之后"):
        if fact not in text:
            raise RuntimeError(f"Required original note detail is missing: {fact}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    cfg = load_settings(ROOT)
    if not cfg.vault_root or cfg.notes_subdir.as_posix() != "GitHub-Note":
        raise RuntimeError("This preview requires the configured GitHub-Note Obsidian Vault")
    if not (cfg.vault_root / ".obsidian").is_dir():
        raise RuntimeError("The configured Vault is unavailable")
    reading_dir = cfg.notes_root / "00-待整理"
    if not reading_dir.is_dir() or reading_dir.is_symlink():
        raise RuntimeError("Configured pending-note folder is unavailable or unsafe")
    source = reading_dir / ORIGINAL
    target = reading_dir / STYLED
    archived = (ROOT / "research/github/Osmantic/ODS/snapshots"
                / REVISION / "sources/001.md")
    if not source.is_file() or not archived.is_file():
        raise RuntimeError("Original ODS note or pinned Research Packet README is missing")

    source_bytes = source.read_bytes()
    contents = make_styled(
        source_bytes.decode("utf-8"),
        archived.read_text(encoding="utf-8"),
    ).encode("utf-8")
    source_digest, styled_digest = sha(source_bytes), sha(contents)
    if target.exists():
        if not target.is_file() or target.is_symlink() or target.read_bytes() != contents:
            raise RuntimeError("Destination already exists with different content; refusing overwrite")
        status = "already_exists_identical"
    else:
        status = "ready" if args.check else "created"
        if args.apply:
            with target.open("xb") as handle:
                handle.write(contents)
            if target.read_bytes() != contents:
                raise RuntimeError("Created file did not match the expected content")
    if sha(source.read_bytes()) != source_digest:
        raise RuntimeError("Original preview unexpectedly changed")
    print(json.dumps({
        "status": status,
        "original_kept": str(source),
        "styled_note": str(target),
        "original_sha256": source_digest,
        "styled_sha256": styled_digest,
        "gh_source_count": 1,
        "first_readme_image_count": 1,
        "prompt_block_count": 0,
        "golden_reference_unchanged": True,
        "managed_capture_note_untouched": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, UnicodeError) as error:
        print(f"STYLED_V22_BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
