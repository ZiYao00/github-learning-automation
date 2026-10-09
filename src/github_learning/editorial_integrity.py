"""V2.2 editorial source fidelity and safe Markdown policy.

Runtime snapshots are untrusted text. We only compare quoted text against
verified, revision-pinned evidence; we never execute repository instructions.
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Any

from .research_packet import validate_packet

_OPEN = re.compile(r"^ {0,3}(?P<marker>\`{3,}|~{3,})(?P<info>[^\r\n]*)$")
_SOURCE_LINK = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/blob/[0-9a-f]{40}/[^)\s>]+")
_IMAGE_REFERENCE = re.compile(r"!\s*\[[^\]\r\n]*\]\s*(?:\([^\r\n)]*\)|\[[^\]\r\n]*\])")
_HTML_TAG = re.compile(r"<\s*/?\s*([A-Za-z][A-Za-z0-9-]*)\b([^<>]*)>",re.I)
_SAFE_INLINE_HTML = {"kbd", "sup", "sub", "mark", "em", "strong", "code", "small", "details", "summary"}


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_fenced(markdown: str) -> tuple[str,list[tuple[str,str,int]]]:
    """Remove fenced regions for active-markup checks, preserve source verbatim."""
    body = _normalize(markdown)
    visible: list[str] = []
    blocks: list[tuple[str,str,int]] = []
    lines = body.splitlines()
    active: tuple[str,int,str,int] | None = None
    contents: list[str] = []
    for index,line in enumerate(lines):
        if active is None:
            match = _OPEN.fullmatch(line)
            if match:
                marker = match.group("marker")
                language = match.group("info").strip().split(" ",1)[0].casefold()
                active = (marker[0],len(marker),language,index)
                contents=[]
                visible.append("")
            else:
                visible.append(line)
        else:
            character,minimum,language,start = active
            if re.fullmatch(rf"^ {{0,3}}{re.escape(character)}{{{minimum},}}[ \t]*$",line):
                blocks.append((language,"\n".join(contents),start))
                active=None
            else:
                contents.append(line)
            visible.append("")
    if active is not None:
        raise ValueError("Markdown 代码围栏未闭合。")
    return "\n".join(visible),blocks


def validate_media_markup(markdown: str) -> None:
    outside,_=split_fenced(markdown)
    # Backtick inline code is inert. Preserve literal image/HTML examples.
    outside=re.sub(r"(?<!\`)\`[^\r\n\`]+\`(?!\`)", "", outside)
    if _IMAGE_REFERENCE.search(outside) or "![[" in outside:
        raise ValueError("editorial_body 不允许自定义 HTML 或图片：含 Markdown/Obsidian 嵌入。")
    for match in _HTML_TAG.finditer(outside):
        name=match.group(1).casefold()
        attrs=match.group(2).strip()
        if name not in _SAFE_INLINE_HTML or attrs:
            raise ValueError("editorial_body 不允许额外媒体或不安全 HTML：" + name)


def _source_link_path(url: str,repo: str,revision: str) -> str | None:
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or (parsed.hostname or "").lower()!="github.com":
        return None
    prefix="/"+repo+"/blob/"+revision+"/"
    path=urllib.parse.unquote(parsed.path)
    if not path.casefold().startswith(prefix.casefold()):
        return None
    return path[len(prefix):]


def pinned_texts(job: dict[str,Any],analysis: dict[str,Any]) -> dict[str,str]:
    """Read only validated Packet files and explicitly declared supplements."""
    packet_dir=Path(str(job["packet_path"]))
    packet=validate_packet(packet_dir)
    if (packet.get("packet_id")!=job.get("packet_id")
            or packet.get("content_fingerprint")!=job.get("packet_content_fingerprint")):
        raise ValueError("Packet 身份或指纹与分析任务不匹配。")
    originals: dict[str,str]={}
    for item in (packet.get("sources") or [])+(packet.get("resources") or []):
        originals[str(item["path"])]=_normalize((packet_dir / item["saved_as"]).read_text(encoding="utf-8"))
    supplement=analysis.get("supplemental_evidence")
    if supplement:
        sid=str(supplement["supplement_id"])
        key=sid.rsplit(":",1)[1]
        manifest=packet_dir.parent.parent/"supplements"/str(job["revision"])/key/"manifest.json"
        import json
        data=json.loads(manifest.read_text(encoding="utf-8"))
        for entry in data.get("sources",[]):
            originals[str(entry["path"])]=_normalize((manifest.parent/entry["stored_as"]).read_text(encoding="utf-8"))
    return originals


def validate_source_literals(markdown: str,job: dict[str,Any],analysis: dict[str,Any]) -> None:
    visible,blocks=split_fenced(markdown)
    if not any(language=="prompt" for language,_,_ in blocks) and "[!gh-source]" not in visible:
        return
    originals=pinned_texts(job,analysis)
    full_name=str(job["repository"]["full_name"])
    rev=str(job["revision"])
    lines=_normalize(markdown).splitlines()

    for language,content,start in blocks:
        if language!="prompt":
            continue
        if not content.strip():
            raise ValueError("Prompt 代码框为空。")
        earlier="\n".join(lines[max(0,start-14):start])
        links=_SOURCE_LINK.findall(earlier)
        if not links:
            raise ValueError("原始 Prompt 必须在代码框前引用固定提交的来源文件。")
        src=_source_link_path(links[-1],full_name,rev)
        if src not in originals:
            raise ValueError("Prompt 来源链接不是本次固定版本的已验证文件。")
        if content not in originals[src]:
            raise ValueError("Prompt 内容与所标注的原始仓库来源不一致，不允许改写或拼接。")

    for idx,line in enumerate(visible.splitlines()):
        if not re.match(r"^>\s*\[!gh-source\]",line):
            continue
        links=_SOURCE_LINK.findall(line)
        src=_source_link_path(links[-1],full_name,rev) if links else None
        if src not in originals:
            raise ValueError("官方原文引用必须在标题提供本次已核验的固定来源链接。")
        literals=[]
        for quote_line in visible.splitlines()[idx+1:]:
            if not quote_line.startswith(">"):
                break
            if re.match(r"^>\s*>",quote_line):
                continue  # labeled translation is not author-original text
            stripped=re.sub(r"^>\s?","",quote_line).strip()
            if stripped:
                literals.append(stripped)
        if not literals:
            raise ValueError("官方原文引用不应为空。")
        for literal in literals:
            if literal not in originals[src]:
                raise ValueError("官方引用与对应固定仓库原文不一致。")
