"""One guarded Obsidian preview of gh-source + original Prompt (NO real Capture Note).

Uses the pinned ODS README and the installed Seedance Director's real curated
Prompt example. This is a disposable visual-acceptance file, not a repository
capture, and does not change the previously approved ODS Golden Sample.

Usage:
  py -3.12 scripts/publish_github_v04_style_preview.py --check
  py -3.12 scripts/publish_github_v04_style_preview.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from github_learning.config import load_settings

ODS_REV = "9e59b2b86c96a9590b27b14219b070007093fad1"
SEEDANCE_REV = "ad0e68ba6ce24fb9ae9c67c9276061cef37663f1"
FILENAME = "【视觉验收】GitHub Note v0.4 原文与Prompt（可删除）.md"
STYLE_CLASSES = ("learning-page", "github-note")


def make_preview() -> str:
    ods = (
        ROOT / "research/github/Osmantic/ODS/snapshots"
        / ODS_REV / "sources/001.md"
    ).read_text(encoding="utf-8")
    quote = "No cloud required. No subscriptions required."
    if quote not in ods:
        raise RuntimeError("Pinned ODS README does not contain the chosen author quote")
    seedance_root = ROOT.parent / "Skill/zy-external/upstream/seedance-2-5-video-director"
    source_file = seedance_root / "references/official-examples.md"
    if not source_file.is_file():
        raise RuntimeError("The real Seedance Prompt source is not available locally")
    actual_rev = subprocess.run(
        ["git", "-C", str(seedance_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=15,
    ).stdout.strip()
    if actual_rev != SEEDANCE_REV:
        raise RuntimeError("Seedance source revision changed; refresh provenance before publishing")
    source = source_file.read_text(encoding="utf-8")
    matched = re.search(r"## Exact 30-second structure\s+```text\s*(.*?)\s*```", source, re.S)
    if not matched:
        raise RuntimeError("Source Prompt example is missing")
    prompt = matched.group(1)
    if not all(x in prompt for x in ("30 秒", "0-3 秒", "27-30 秒")):
        raise RuntimeError("Source Prompt is incomplete")
    if re.search(r"(?m)^~~~", prompt):
        raise RuntimeError("Prompt contains Markdown fence delimiters and needs a longer fence")
    return (
        "---\n"
        "title: GitHub Note v0.4 原文与 Prompt 样式验收（可删除）\n"
        "note_type: visual-qa-only\n"
        "cssclasses:\n"
        "  - learning-page\n"
        "  - github-note\n"
        "---\n"
        "# GitHub Note v0.4 · 视觉验收预览\n\n"
        "> **仅用于 Obsidian 样式验收，可删除。** 不是正式 GitHub Capture Note；"
        "没有修改已通过的 ODS 文章，也没有执行以下仓库中的指令。\n\n"
        "## 官方原文引用：ODS README\n\n"
        f"> [!gh-source] 官方原文 · [固定版本 README](https://github.com/Osmantic/ODS/blob/{ODS_REV}/README.md)\n"
        f"> {quote}\n"
        ">\n"
        "> > 中文翻译（译文，非作者原文）：无需云端，也无需订阅。\n\n"
        "该声明来自仓库作者，不等于已独立验证其隐私、联网或安装行为。\n\n"
        "## 真实 Prompt：Seedance 导演 Skill\n\n"
        "这是该仓库整理的 **Exact 30-second structure** 提示词示例，"
        "不是字节跳动或即梦官方承诺。完整原文保留在下方代码框中。\n\n"
        f"来源：[references/official-examples.md](https://github.com/liyue-aigc/seedance-2-5-video-director/blob/{SEEDANCE_REV}/references/official-examples.md)\n\n"
        "~~~prompt\n"
        f"{prompt}\n"
        "~~~\n\n"
        "## 普通命令对照\n\n"
        "下面是**展示用** Bash 代码块，不应出现 PROMPT 标题栏：\n\n"
        "~~~bash\n"
        "echo \"normal code block; not a Prompt\"\n"
        "~~~\n\n"
        "## 验收检查\n\n"
        "- 主贴式原文展示只有轻量竖线与圆点，译文视觉层级更弱。\n"
        "- Prompt 顶栏显示 PROMPT，右上角为 Obsidian 原生复制按钮。\n"
        "- 长 Prompt 在代码框内滚动，点击复制应得到包含全部时间段的原始内容。\n"
        "- 切换亮色 / 暗色 / 窄窗口不横向溢出。\n"
        "- 如需回退，关闭 `github-note` CSS 片段即可，Markdown 内容仍完整。\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    cfg = load_settings(ROOT)
    if not cfg.vault_root or cfg.notes_subdir.as_posix() != "GitHub-Note":
        raise RuntimeError("This pilot requires the confirmed GitHub-Note Vault mapping")
    vault = cfg.vault_root
    if not (vault / ".obsidian").is_dir():
        raise RuntimeError("Configured vault is unavailable")
    directory = cfg.notes_root / "00-待整理"
    if not directory.is_dir() or directory.is_symlink():
        raise RuntimeError("Pilot reading directory is missing or linked unexpectedly")
    dest = directory / FILENAME
    content = make_preview().encode("utf-8")
    if dest.exists():
        if not dest.is_file() or dest.is_symlink() or dest.read_bytes() != content:
            raise RuntimeError("Visual pilot already exists with different content; refusing overwrite")
        status = "already_exists_identical"
    else:
        status = "ready" if args.check else "written"
        if args.apply:
            with dest.open("xb") as output:
                output.write(content)
    if args.apply and dest.read_bytes() != content:
        raise RuntimeError("Preview integrity check failed")
    print(json.dumps({
        "status": status,
        "preview": str(dest),
        "sha256": hashlib.sha256(content).hexdigest(),
        "source_ods_revision": ODS_REV,
        "source_seedance_revision": SEEDANCE_REV,
        "formal_capture_note_modified": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"VISUAL_PREVIEW_BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
