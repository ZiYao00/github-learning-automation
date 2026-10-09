"""Read-only end-to-end verification of the pinned Seedance v2.2 Agent/Skill smoke.
This is an integration check on an actual prepare->analysis->finalize result.
It does not fetch GitHub, run target Skill code, or write any file.
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
from github_learning.note_template import (
    MANAGED_START,MANAGED_END,capture_metadata_from_text,find_notes_by_repository,
)

FULL="liyue-aigc/seedance-2-5-video-director"
REV="ad0e68ba6ce24fb9ae9c67c9276061cef37663f1"
JOB="liyue-aigc__seedance-2-5-video-director__6ccb426c"


def main():
    cfg=load_settings(ROOT)
    jobdir=cfg.runtime_root/JOB
    job=json.loads((jobdir/"job.json").read_text(encoding="utf-8"))
    analysis=json.loads((jobdir/"analysis.json").read_text(encoding="utf-8"))
    manifest=json.loads((jobdir/"source_manifest.json").read_text(encoding="utf-8"))
    assert job["version"]==7 and job["editorial_contract_version"]=="2.2"
    assert job["revision"]==REV and job["state"]=="published"
    assert job["final_result"]["status"]=="note_ready"
    assert analysis["editorial_review"]["status"]=="passed"
    assert len(manifest["sources"])==10
    assert all(s["coverage_required"] for s in manifest["sources"])
    assert len(analysis["evidence_map"])==10
    notes=find_notes_by_repository(cfg.notes_root,FULL)
    assert len(notes)==1, "Multiple/missing notes with stable repo identity"
    path=notes[0]
    assert path.parent == cfg.notes_root/"00-待整理"
    data=path.read_text(encoding="utf-8")
    meta=capture_metadata_from_text(data)
    assert meta["repo"]==FULL and meta["revision"]==REV
    assert meta["editorial_contract_version"]=="2.2"
    assert meta["note_style"]=="natural-product-v2.2"
    assert MANAGED_START in data and MANAGED_END in data
    assert "## 我的记录" in data
    assert data.count("> [!gh-source]")==1 and data.count("~~~prompt")==1
    assert "ODS 的七项能力" not in data
    assert job["final_result"]["first_image_status"]=="no_image"
    source = next(s for s in manifest["sources"] if s["path"]=="references/official-examples.md")
    original=(jobdir/source["saved_as"]).read_text(encoding="utf-8")
    matched=re.search(r"## Exact 30-second structure\s+```text\s*(.*?)\s*```",original,re.S)
    if not matched: raise AssertionError("Actual curated source example is missing")
    source_prompt=matched.group(1)
    rendered=re.search(r"~~~prompt\n(.*?)\n~~~",data,re.S)
    if not rendered: raise AssertionError("Published Prompt code block is missing")
    if source_prompt!=rendered.group(1):
        raise AssertionError("Original Prompt text was altered or truncated")
    assert "27-30 秒" in rendered.group(1)
    original_quote="本仓库不会调用付费生成接口，不会自动消耗积分。"
    readme = next(s for s in manifest["sources"] if s["path"]=="README.md")
    assert original_quote in (jobdir/readme["saved_as"]).read_text(encoding="utf-8")
    assert original_quote in data
    print(json.dumps({
        "status":"passed","repository":FULL,"revision":REV,
        "note_path":str(path),"byte_length":len(data.encode("utf-8")),
        "sha256":hashlib.sha256(data.encode("utf-8")).hexdigest(),
        "contract":"2.2","sources_checked":len(manifest["sources"]),
        "original_prompt_verbatim":True,"source_quote_grounded":True,
        "first_image":"no_image","user_tail_present":True,
        "formal_capture_note_single":True,
    },ensure_ascii=False,indent=2))
if __name__=="__main__":
    try:main()
    except (AssertionError,KeyError,ValueError,OSError) as e:
        print("SMOKE_FAIL: "+str(e),file=sys.stderr);raise SystemExit(2)
