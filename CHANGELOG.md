# Changelog

## Unreleased · Natural Product V2.2 pilot

- Ship an ODS V2.2 editorial preview and the first meaningful image from its pinned README into the configured Obsidian Vault without touching the formal ODS Capture Note.
- Introduce default `editorial_headline` + `editorial_body` for new, sufficient Capture Notes; retain legacy structured rendering and Minimal Note compatibility.
- Materialize at most one same-repository README image per note, pinned and Git-blob-verified, stored separately in the reading media layer. No video downloads or media mirroring.
- Preserve `no_change`, duplicate safety, immutability, user-owned tails, and explicit migration requirements.
- Add stdlib editorial/first-image policy and lifecycle tests.
- Preserve README-authored capability/highlight overviews as concise, attributed content; keep on-device/no-cloud/no-telemetry claims together with the README's online exceptions and optional cloud modes.
- Rename the reading-layer staging folder from `00-Inbox` to `00-待整理`; hide `GitHub-Note/_repo-data` only in Obsidian File Explorer by updating the shared `github-note.css` Extension. Existing assets/links remain intact, with guarded original-file backups in ignored `.runtime`.
- Safely refresh the ODS V2.2 Vault preview and its checked-in reference text without touching the formal ODS Capture Note.


## 0.4.1 - 2026-10-08

First-use configuration and local-storage topology polish.

- Add explicit `onboarding` before first collection so storage choices are surfaced instead of hidden behind fallback paths.
- Add `configure --use-defaults` to explicitly accept project-local `notes/github` and `research/github` and record them in ignored `config/local.json`.
- Allow `notes_root + vault_root + notes_subdir` to coexist; recommend project-local notes as physical truth with a Vault child Junction for Obsidian display.
- Preserve legacy direct-vault configurations and prevent `--use-defaults` from silently moving existing notes.
- Add Obsidian mapping diagnostics: direct_vault, ok, mapping_missing, mapping_mismatch, and not_configured.
- Keep Research Packet storage outside Obsidian by default and add `research/` to gitignore.
- Add `docs/CONFIGURATION.md` as the configuration/topology contract.
- Add `docs/V0.5-BACKLOG.md` to record deferred future capabilities without implementing them.
- Update canonical Skill, Agent handoff docs, quickstart, release checklist, and version metadata to v0.4.1.

## 0.4.0 - 2026-10-08

Durable Knowledge Capture update.

- Add explicit `research_root` configuration and require both Reading Layer and Archive Layer before real collection.
- Add immutable Research Packet V1 with `owner/repo@revision` identity, staging, SHA-256 validation, reuse/conflict protection, repository/tree/media indexes, archived sources/resources, and repo-level observations.
- Separate analysis context from archive storage so truncated Agent inputs no longer truncate the long-term high-value archive copy.
- Treat Latest Release and mutable repository metadata as Observations instead of commit Snapshot content.
- Extend Source Planner with Agent/Skill references plus archived resources under assets/templates/examples/prompts/resources while keeping resources out of the default first-pass analysis context.
- Upgrade runtime lifecycle to Job v6, resume interrupted v0.4 jobs without recollection, and gate v0.3/v5 jobs behind explicit restart.
- Add Capture Note V2 with `why_save`, adaptive content/project maps, reusable resource index, logical `packet_id`, `content_profile`, `capture_status`, `analysis_status`, and `observation_fingerprint`.
- Add machine-verifiable Evidence Map coverage for every `coverage_required=true` source while retaining semantic `coverage_review`.
- Change insufficient-source behavior from “no note” to a clearly labeled Minimal Capture Note so successful capture is never lost.
- Add whole-note `no_change` fast path for unchanged Packet + Observation.
- Define Derived Artifact boundaries for future Deep Note / Compare / Media Brief workflows without implementing a second collector.
- Add v0.4 tests, Research Packet / Derived Artifact specs, multi-Agent contract updates, and refreshed release/maintenance documentation.

## 0.3.0 - 2026-10-06

Source-depth, resumability, and multi-Agent maintenance update.

- Pin repository-file collection to one default-branch HEAD revision and record the revision in runtime data and generated note Frontmatter.
- Add a bounded, README-guided Source Planner for high-value official files such as SKILL.md, Agent metadata, manifests, support/quickstart/install/architecture/validation docs, while filtering vendor/build noise and avoiding raw config/Compose files as generic learning sources.
- Add source_manifest.json plus per-source runtime files; keep source_bundle.md as a convenience view instead of the audit source of truth.
- Treat repository text as untrusted data and explicitly prevent repository prompt instructions from changing Agent behavior or triggering execution.
- Block private repositories by default even when current GitHub credentials can read them.
- Expand analysis with optional requirements, compatibility, deployment, architecture, and project_status fields.
- Add runtime Job state, in_progress reuse for interrupted work, explicit --restart-job supersession without deleting audit data, and idempotent finalize for published jobs.
- Centralize the package/User-Agent version at 0.3.0.
- Establish skill/github-note/SKILL.md as the single manually maintained Skill source and generate compatible ChatGPT, Codex, Claude, WorkBuddy, and legacy install surfaces.
- Add Agent integration, maintenance handoff, release checklist, and v0.3 regression coverage.

## 0.2.2 - 2026-08-23

Shared-style migration and refresh-safety update.

- Move Obsidian styling to the shared `obsidian-learning-snippets` provider and add `config/obsidian-style.json` as the consumer contract.
- Stop treating local `obsidian/snippets/` files as the canonical style source; docs and Skill now point to the shared repository.
- Bind authorized legacy-note migration to the prepare-time target path and SHA-256; return `legacy_target_changed` if the note changes before finalize.
- Align generated Agent handoff guidance with the existing 2-5 tag validation rule.
- Remove the public README dependency on a developer-specific local-project path.
- Replace CSS-file-presence regression coverage with consumer-contract coverage.
- Retire the project-local `obsidian/` directory entirely; shared CSS is declared through `config/obsidian-style.json` and installed from the canonical provider repository at the Vault level.

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
