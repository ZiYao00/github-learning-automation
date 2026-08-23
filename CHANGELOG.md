# Changelog

## 0.2.1 - 2026-08-23

Stability, portability, and Obsidian integration update.

- Validate direct `--notes-root` targets instead of silently accepting a mistyped path.
- Restrict repository identity detection to YAML frontmatter so body code blocks cannot create false duplicate matches.
- Move duplicate/legacy note preflight ahead of GitHub source collection.
- Add explicit `prepare --replace-legacy`; retain backup-before-replace behavior and compatibility with legacy finalize authorization.
- Add shared `learning-lab.css` Core plus a small `github-note.css` Extension; GitHub notes do not depend on `video-note.css`.
- Document Obsidian snippet installation and the fixed `learning-page` + `github-note` style contract.
- Expand regression coverage for configuration, frontmatter identity, preflight behavior, legacy authorization, and style classes.

## 0.2.0 - 2026-08-22

Long-term note identity and refresh update.

- Treat `owner/repo` as the stable repository identity.
- Default repeated conversions to upsert/refresh instead of generating `（2）` notes.
- Add `--new-note` for explicit parallel note creation.
- Preserve user content after the managed region, with `## 我的记录` as the default personal section.
- Block automatic refresh of legacy notes without markers; add explicit `--replace-legacy` with runtime backup.
- Detect duplicate notes for the same repository and stop rather than guessing which file to overwrite.
- Disambiguate same-name repositories from different owners with `repo · owner.md` only when needed.
- Use local collection date for the note `updated` field while retaining UTC runtime timestamps.
- Add `source_conflicts` and a dedicated risk callout for contradictory official materials.
- Separate collection coverage warnings from repository-source conflicts.
- Treat manifest and Latest Release retrieval as optional; failures become coverage warnings instead of aborting the whole job.
- Prefer root-entry GitHub Raw URLs for manifest content to reduce Contents API calls.

## 0.1.1 - 2026-08-22

First-run reliability update based on the first real repository test.

- Add a mandatory configuration/auth preflight state machine.
- Stop `prepare` and `finalize` from silently using the repository fallback note path.
- Add `configure` to create `config/local.json` without manual copying/editing.
- Change the default Vault subdirectory example to `GitHub-Note`.
- Reuse `GITHUB_TOKEN` / `GH_TOKEN` or an already logged-in GitHub CLI session without persisting tokens.
- Require explicit `--allow-anonymous` when no GitHub authentication is detected.
- Add zero-install `scripts/github_learning.py` launcher so the Skill no longer assumes the console script is installed.
- Reconfigure CLI stdout/stderr to UTF-8 for Windows-friendly Chinese JSON messages.
- Treat `source_insufficient` and `analysis_required` as normal workflow states instead of generic errors.
