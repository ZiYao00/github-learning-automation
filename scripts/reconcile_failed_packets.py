"""Reconcile only provably failed, collected-but-unarchived Packet attempts.

Old failed runs are retained (not deleted), but removed from active-job routing.
No immutable Research Packet or published note is modified.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.config import load_settings
from github_learning.research_packet import packet_path,validate_packet,_content_fingerprint


def candidates(repo:str,apply:bool)->list[dict]:
    cfg=load_settings(ROOT)
    results=[]
    for directory in cfg.runtime_root.glob(repo.replace("/","__")+"__*"):
        job_path=directory/"job.json"
        if not job_path.is_file():continue
        job=json.loads(job_path.read_text(encoding="utf-8"))
        if (job.get("repository") or {}).get("full_name") != repo:continue
        if job.get("state")!="collected" or job.get("packet_id"):continue
        paths=[directory/name for name in ("source_manifest.json","repository.json","tree-index.json","media-index.json")]
        if not all(x.is_file() for x in paths):continue
        snapshot=packet_path(cfg.research_root,repo,job["revision"])
        if not snapshot.is_dir():continue
        archived=validate_packet(snapshot)
        fingerprint=_content_fingerprint(job,json.loads(paths[0].read_text(encoding="utf-8")),
                                          paths[1].read_bytes(),paths[2].read_bytes(),paths[3].read_bytes())
        if fingerprint==archived["content_fingerprint"]:continue
        results.append({"job_id":job["job_id"],"state":"collected",
                        "action":"mark_packet_archive_failed" if apply else "would_mark_packet_archive_failed",
                        "reason":"same repo@revision, differing immutable Packet selection"})
        if apply:
            job["state"]="packet_archive_failed"
            job["packet_error_code"]="packet_conflict"
            job["failure_reason"]="Source planner selection diverged from pinned immutable Packet; original Packet preserved"
            tmp=job_path.with_suffix(".packet-reconcile.tmp")
            if tmp.exists():raise RuntimeError("Reconcile temp file exists")
            tmp.write_text(json.dumps(job,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            os.replace(tmp,job_path)
    return results

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("repo")
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check",action="store_true")
    g.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    print(json.dumps({"repository":args.repo,"actions":candidates(args.repo,args.apply)},
                     ensure_ascii=False,indent=2))
