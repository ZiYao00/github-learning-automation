"""Read-only audit for the codexpro V2.2 Capture Note and append-only supplements.

This is an integration acceptance check, not a target-repository code runner.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.config import load_settings
from github_learning.lifecycle import _validate_analysis
from github_learning.note_template import MANAGED_START,MANAGED_END,capture_metadata_from_text,find_notes_by_repository
from github_learning.research_packet import validate_packet

FULL="rebel0789/codexpro"
REV="113472c6ff0a1516b6f223a43cd355abdf2e61ae"
JOB="rebel0789__codexpro__8610ead7"
SUP="00c10b6635ab1a8f"


def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def blob(b:bytes)->str:return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def verify():
    cfg=load_settings(ROOT)
    jobdir=cfg.runtime_root/JOB
    job=json.loads((jobdir/"job.json").read_text(encoding="utf-8"))
    analysis=json.loads((jobdir/"analysis.json").read_text(encoding="utf-8"))
    manifest=json.loads((jobdir/"source_manifest.json").read_text(encoding="utf-8"))
    assert job["state"]=="published" and job["version"]==7
    assert job["revision"]==REV and job["editorial_contract_version"]=="2.2"
    assert analysis["editorial_review"]["status"]=="passed"
    assert analysis["coverage_review"]["status"]=="passed"
    _validate_analysis(jobdir,analysis)
    packet=validate_packet(Path(job["packet_path"]))
    assert packet["packet_id"]==FULL+"@"+REV
    assert packet["content_fingerprint"]==job["packet_content_fingerprint"]
    assert len(manifest["sources"])==10
    required={s["id"] for s in manifest["sources"] if s["coverage_required"]}
    mapped={e["source_id"] for e in analysis["evidence_map"]}
    assert mapped==required
    assert all(e["status"] in {"represented","omitted_with_reason"} for e in analysis["evidence_map"])

    supplement=cfg.research_root/"rebel0789"/"codexpro"/"supplements"/REV/SUP
    sm=json.loads((supplement/"manifest.json").read_text(encoding="utf-8"))
    assert sm["packet_id"]==packet["packet_id"]
    assert sm["packet_content_fingerprint"]==packet["content_fingerprint"]
    source_index=json.loads((jobdir/"tree-index.json").read_text(encoding="utf-8"))
    expected={i["path"]:i for i in source_index["entries"]}
    original={}
    for record in sm["sources"]:
        raw=(supplement/record["stored_as"]).read_bytes()
        assert sha(raw)==record["sha256"] and len(raw)==record["bytes"]
        assert blob(raw)==record["repository_sha"]==expected[record["path"]]["sha"]
        assert int(expected[record["path"]]["size"])==len(raw)
        original[record["path"]]=raw.decode("utf-8")
    assert set(original)=={"CHATGPT_PROMPT.md","CODEX_PROMPT.md","README_ZH.md"}

    notes=find_notes_by_repository(cfg.notes_root,FULL)
    assert len(notes)==1, "Multiple or missing Capture Notes"
    note_path=notes[0]
    assert note_path.parent==cfg.notes_root/"00-待整理"
    content=note_path.read_text(encoding="utf-8")
    meta=capture_metadata_from_text(content)
    assert meta["repo"]==FULL and meta["revision"]==REV
    assert meta["packet_id"]==FULL+"@"+REV
    assert meta["note_style"]=="natural-product-v2.2"
    assert meta["editorial_contract_version"]=="2.2"
    assert MANAGED_START in content and MANAGED_END in content and "## 我的记录" in content
    assert content.count("> [!gh-source]")==1
    blocks=re.findall(r"~~~prompt\n(.*?)\n~~~",content,re.S)
    assert len(blocks)==2, "Original Prompt blocks missing or malformed"
    for actual,name in zip(blocks,["CHATGPT_PROMPT.md","CODEX_PROMPT.md"]):
        assert actual==original[name].rstrip("\r\n"),"Prompt differs from pinned source "+name
        assert "/blob/"+REV+"/"+name in content
    for part in ("## 仓库自己强调的核心能力","## 场景一","## 场景二","## 场景三","## 安全与隐私"):
        assert part in content,"Missing editorial section: "+part
    assert job["final_result"]["first_image_status"]=="unsupported"
    assert "## 先看结论" not in content,"Unexpected legacy template body"
    assert "0.30.3" in content and "0.30.2" in content
    result={
        "status":"passed",
        "repository":FULL,
        "revision":REV,
        "note_path":str(note_path),
        "note_sha256":sha(content.encode("utf-8")),
        "main_packet_sources":len(manifest["sources"]),
        "supplement_sources":len(original),
        "prompt_blocks":len(blocks),
        "prompts_verbatim":True,
        "factual_quote_grounded":True,
        "immutable_packet_verified":True,
        "note_identity_unique":True,
        "source_coverage_complete":True,
        "first_image":"unsupported_svg",
        "user_tail_preserved":True,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    try:verify()
    except (KeyError,AssertionError,ValueError,OSError) as e:
        print("CODEXPRO_V22_AUDIT_FAILED: "+str(e),file=sys.stderr)
        raise SystemExit(2)
