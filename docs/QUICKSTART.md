# Quickstart & Regression

## 1. Configure

v0.4 requires both a note destination and a long-term Research Root.

~~~powershell
python scripts\github_learning.py configure --vault-root "D:\Notes\MyVault" --notes-subdir "GitHub-Note"
~~~

~~~powershell
python scripts\github_learning.py configure --research-root "D:\GitHub-Research"
~~~

Research Root must already exist.

configure uses merge updates: changing the note destination later must not erase research_root.

## 2. Doctor

~~~powershell
python scripts\github_learning.py doctor
~~~

Expected ready state requires:

- explicit notes configuration;
- explicit research_root;
- GitHub authentication.

Without authentication, use gh auth login, or explicitly choose --allow-anonymous for a prepare.

## 3. Prepare

~~~powershell
python scripts\github_learning.py prepare "https://github.com/owner/repo"
~~~

Expected first-run result:

~~~text
analysis_required
packet_status = packet_archived | packet_reused
packet_id = owner/repo@revision
~~~

Before Agent analysis, verify:

- runtime job version = 6;
- packet.json exists under research_root;
- repository/tree/media core hashes validate;
- source/resource hashes validate;
- Latest Release lives in repo observations, not inside immutable snapshot;
- failed/partial staging is not silently deleted.

## 4. Agent analysis

Read:

- agent_handoff.md
- source_manifest.json
- manifest sources/
- observation.json
- source_bundle.md
- analysis.json

resources/ is an archive surface. Do not read every resource just because it exists.

For a sufficient analysis:

- fill why_save;
- choose/confirm content_profile;
- build a compact knowledge/project map;
- fill resource_index only with supported purpose claims;
- complete every coverage_required Evidence Map entry;
- set coverage_review.status=passed only after source recheck.

## 5. Finalize

~~~powershell
python scripts\github_learning.py finalize "<job_dir>"
~~~

Sufficient source:

~~~text
note_ready
analysis_status = sufficient
~~~

Insufficient source:

~~~text
note_ready
analysis_status = insufficient
~~~

The second case must create a Minimal Capture Note with a visible “待进一步研究” warning.

## 6. Refresh / no-op

After publishing a v0.4 Capture Note, prepare the exact same revision + observation again.

Expected:

~~~text
no_change
~~~

No Agent analysis and no managed-note rewrite should occur.

When revision changes, a new immutable Packet is created and the same Capture Note is refreshed.

## 7. Resume

Interrupt a v0.4 job after runtime material exists or after Packet archive.

A later prepare for the same repo should resume that job without a second GitHub collection.

An unfinished v0.3/v5 job must return:

~~~text
legacy_job_restart_required
~~~

Use --restart-job only with explicit intent; the old runtime remains and becomes superseded.

## 8. Capture Note checks

Full Capture Note should preserve:

- repo/revision/packet_id;
- content_profile;
- capture_status/analysis_status;
- observation_fingerprint;
- why_save;
- adaptive map;
- resource index when available;
- research entry;
- source boundary;
- 我的记录.

Refresh must preserve all content after the managed end marker.

## 9. Representative real repositories

| Profile | Repository | Main acceptance |
| --- | --- | --- |
| Software / container | Osmantic/ODS | architecture/support/release evidence, no vendor noise |
| Agent / knowledge Skill | chenjin-cmd/wechat-graphic-monetization | SKILL + UNIVERSAL + references, assets as archived resources, 8-stage map |
| Python project | psf/requests | compact software Capture Note, not over-expanded |
| Minimal | octocat/Hello-World | Packet + Minimal Capture Note when analysis is insufficient |

## 10. Packet failure cases

Regression coverage should include:

- staging write failure;
- packet core hash mismatch;
- source/resource hash mismatch;
- same repo@revision same fingerprint → reuse;
- same repo@revision different fingerprint → packet_conflict;
- Packet archived but note publish fails → retry without GitHub recollection;
- research_root moves but logical packet_id in note remains unchanged.

## 11. Security

Confirm repository content cannot:

- execute commands;
- install dependencies;
- alter Collector behavior through repository config;
- disclose tokens;
- trigger file deletion;
- force binary downloads.

Private repositories remain blocked.

## 12. Skill package

Canonical Skill source:

~~~text
skill/github-note/SKILL.md
~~~

After Skill changes:

~~~powershell
py -3.12 scripts\build_agent_skill_packages.py
py -3.12 scripts\build_agent_skill_packages.py --check
~~~

Do not manually edit generated Agent Skill outputs.

## 13. Automatic validation

Minimum available without dev dependencies:

~~~powershell
py -3.12 -m compileall src scripts tests
py -3.12 scripts\build_agent_skill_packages.py --check
~~~

When dev dependencies are already installed:

~~~powershell
py -3.12 -m pytest
py -3.12 -m ruff check .
~~~

Do not install dev dependencies automatically just to satisfy a test run.

## 14. Obsidian style

Capture Note still declares:

~~~yaml
cssclasses:
  - learning-page
  - github-note
~~~

Canonical CSS provider remains:

~~~text
https://github.com/ZiYao00/obsidian-learning-snippets
~~~

Research Packet does not require Obsidian CSS.
