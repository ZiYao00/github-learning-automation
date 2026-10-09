"""Promote the user-approved ODS V2.2 visually enhanced note to the ONE Git Golden Sample.
Check before apply. Existing reference is SHA-backed up under ignored .runtime.
Never mutate any Vault note, Research Packet, formal Capture Note, or CSS.
"""
from __future__ import annotations
import argparse, hashlib, os, sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.config import load_settings
from publish_ods_v22_styled_preview import make_styled, ORIGINAL, STYLED, REVISION

def digest(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def replace_once(text:str,old:str,new:str)->str:
    if text.count(old)!=1: raise ValueError("Unexpected golden reference structure: "+old[:60])
    return text.replace(old,new,1)
def main():
    parser=argparse.ArgumentParser()
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--check",action="store_true");g.add_argument("--apply",action="store_true")
    mode=parser.parse_args()
    cfg=load_settings(ROOT)
    if cfg.notes_subdir != Path("GitHub-Note") or not cfg.vault_root:
        raise RuntimeError("Missing configured direct Obsidian Vault")
    note_dir=cfg.notes_root/"00-待整理"
    original=note_dir/ORIGINAL
    accepted=note_dir/STYLED
    archived=ROOT/"research/github/Osmantic/ODS/snapshots"/REVISION/"sources/001.md"
    golden=ROOT/"docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md"
    for p in (original,accepted,archived,golden):
        if not p.is_file() or p.is_symlink(): raise RuntimeError("Required file missing or unsafe: "+str(p))
    orig_data=original.read_bytes();accepted_data=accepted.read_bytes()
    expected=make_styled(orig_data.decode("utf-8"),archived.read_text(encoding="utf-8")).encode("utf-8")
    if accepted_data!=expected: raise RuntimeError("Approved Vault visual-enhanced note has changed; stop")
    text=accepted_data.decode("utf-8")
    text=replace_once(text,'note_type: "editorial_v2_2_visual_preview"','note_type: "editorial_v2_2_reference"')
    text=replace_once(text,'title: "ODS：把本地 AI 工具管起来，而不只是跑一个模型（视觉增强版）"',
                      'title: "ODS：把本地 AI 工具管起来，而不只是跑一个模型"')
    text=replace_once(text,"本页是 V2.2 独立视觉增强版，原版与 Golden Sample 保留不变；",
                      "本页是已批准的 V2.2 视觉增强黄金样板；")
    result=text.encode("utf-8")
    before=golden.read_bytes()
    if 'note_type: "editorial_v2_2_reference"' not in before.decode("utf-8"): 
        raise RuntimeError("Current canonical file is not a known reference")
    if text.count("> [!gh-source]")!=1 or "## 仓库自己强调的七项能力" not in text: raise RuntimeError("Missing approved editorial components")
    if "\nrepo:" in text or "~~~prompt" in text: raise RuntimeError("Golden sample is unexpectedly managed or invents a Prompt")
    backup=ROOT/".runtime/golden-sample-backups"/("ODS-V2.2-"+digest(before)[:16]+".md")
    status="unchanged" if before==result else "ready"
    if mode.apply and before!=result:
        backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():
            if backup.read_bytes()!=before: raise RuntimeError("Backup collision")
        else:
            with backup.open("xb") as fh:fh.write(before)
        if backup.read_bytes()!=before:raise RuntimeError("Backup verification failed")
        tmp=golden.with_suffix(golden.suffix+".golden.tmp")
        if tmp.exists():raise RuntimeError("Existing temporary update")
        try:
            with tmp.open("xb") as fh:fh.write(result)
            if tmp.read_bytes()!=result: raise RuntimeError("Temporary golden mismatch")
            os.replace(tmp,golden)
        finally:
            if tmp.exists(): tmp.unlink()
        status="promoted"
    if mode.apply and golden.read_bytes()!=result:raise RuntimeError("Post-promotion golden mismatch")
    if accepted.read_bytes()!=accepted_data or original.read_bytes()!=orig_data:raise RuntimeError("Vault note changed unexpectedly")
    print(json.dumps({"status":status,"golden":str(golden),"sha256":digest(result),"original_vault_preserved":True,"accepted_vault_preserved":True,"backup":str(backup) if before!=result else None},ensure_ascii=False,indent=2))
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,RuntimeError) as e:
        print("PROMOTION_BLOCKED: "+str(e),file=sys.stderr);raise SystemExit(2)
