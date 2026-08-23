---
name: github-note
description: Turn a public github.com repository into a concise, source-grounded Markdown learning note that can be safely refreshed over time. Use when the user asks to learn, summarize, understand, document, update, refresh, or save notes for a GitHub repository, especially to answer what the repository does, why it is useful, how to install/use it, important caveats, source conflicts, and a small set of knowledge tags. Use official GitHub repository materials as evidence and do not infer missing commands, versions, paths, or compatibility facts.
---

# GitHub Note

Use the host `github-learning-automation` project. Run commands from its project root. Prefer the zero-install launcher:

```powershell
python scripts\github_learning.py <command>
```

If the `github-learning` console command is already installed, it is equivalent. Do not install the package merely to obtain the CLI unless the user explicitly asks.

## First-run gate

Before the first real `prepare`, run:

```powershell
python scripts\github_learning.py doctor
```

Interpret the machine status before doing anything else:

- `configuration_required`: do not run `prepare`. Tell the user that no explicit note destination is configured and ask where the notes should be stored. Then use `configure`; do not manually edit `config/local.json` unless necessary.
- `auth_recommended`: tell the user that GitHub authentication was not detected and anonymous API quota is limited. Recommend `gh auth login`. Only use `--allow-anonymous` when the user explicitly accepts anonymous mode.
- `ready`: continue without asking setup questions again.

The project automatically reuses `GITHUB_TOKEN` / `GH_TOKEN` or an already logged-in `gh auth token`. Never print, persist, quote, or copy the token into project files, logs, notes, or chat.

Never hardcode or assume a specific Vault path. Ask the user where notes should be stored, then configure it:

```powershell
python scripts\github_learning.py configure --vault-root "D:\Notes\MyVault" --notes-subdir "GitHub-Note"
```

## Workflow

1. Confirm `doctor` permits the run.
2. Run `prepare "<github repository>"`. Default mode is upsert: `owner/repo` is the stable identity, so an existing managed note will be refreshed instead of producing `（2）`. The CLI checks duplicate/legacy note state before fetching GitHub sources.
3. Use `--new-note` only when the user explicitly wants a second independent note for the same repository.
4. Read the returned `agent_handoff.md`, `source_bundle.md`, and `analysis.json`.
5. Fill only `analysis.json`. Base every repository fact on `source_bundle.md`; do not use model memory to fill missing details.
6. Set `source_status` to `insufficient` when the official material cannot support a trustworthy note. This is a successful quality-gate outcome, not an execution error.
7. When sufficient, answer the repository-learning questions concisely: what it is, what it does, useful scenarios, official installation/use path, configuration if important, and caveats.
8. Put explicit contradictions between current official sources into `source_conflicts`. Preserve both sides of the conflict and do not decide which one is correct unless the source itself resolves it.
9. Treat `Collection warnings` only as coverage gaps. Do not infer that a Release, manifest, or feature does not exist merely because an optional fetch failed.
10. Add 2-5 high-value knowledge tags. Do not copy all GitHub Topics mechanically.
11. Re-read the source bundle, perform a coverage check, and set `coverage_review.status` to `passed` only when the note has not omitted important source-supported usage or limitations and has not introduced unsupported facts.
12. Run `finalize "<job_dir>"`.
13. Report completion only for `note_ready`. For `source_insufficient`, explain that no note was published because official material was insufficient.

## Shared Obsidian style contract

Read `config/obsidian-style.json` when style dependencies matter. The canonical CSS source is `https://github.com/ZiYao00/obsidian-learning-snippets`; this host project is only a consumer. Do not recreate, fork, or independently modify the shared Core/Extension CSS inside `github-learning-automation`. Generated notes must keep `learning-page` and `github-note` in Frontmatter.

## Refresh safety

A v0.2+ note has an auto-managed region followed by a user-preserved tail, normally beginning with `## 我的记录`. Refresh may rewrite Frontmatter and the managed region, but must preserve everything after the managed end marker.

If `prepare` returns `legacy_note_refresh_blocked`, do not continue to GitHub collection or analysis. Explain that the existing note lacks refresh markers and may contain manual edits. Only after explicit user authorization may you rerun:

```powershell
python scripts\github_learning.py prepare "<github repository>" --replace-legacy
```

The authorization is stored in the new runtime job and bound to the legacy note path plus its SHA-256 at prepare time. If `finalize` returns `legacy_target_changed`, the target changed after authorization: stop, rerun `prepare --replace-legacy`, and require fresh user authorization. When the target is unchanged, `finalize` must still save the old note to `legacy_note_backup.md` before replacing it. For older jobs created before this preflight behavior, `finalize "<job_dir>" --replace-legacy` remains a compatibility path.

If `prepare` (or compatibility `finalize`) returns `duplicate_repository_notes`, stop and surface the matching note paths. Do not guess which duplicate should be overwritten.

Do not perform source-code review, issue mining, PR analysis, security auditing, or repository modification unless the user separately asks for those tasks.
