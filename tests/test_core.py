import json
from pathlib import Path

import pytest

from github_learning.auth import resolve_github_auth
from github_learning.config import ConfigurationError, Settings, configure_notes, load_settings
from github_learning.github_client import SourceBundle
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import finalize_job, preflight_publish, prepare_job
from github_learning.note_template import render_note, repository_identity_from_text, unique_note_path


def test_resolve_repository_url_and_slug():
    a = resolve_repository("https://github.com/ZiYao00/github-learning-automation")
    b = resolve_repository("ZiYao00/github-learning-automation")
    assert a.full_name == b.full_name == "ZiYao00/github-learning-automation"
    assert a.canonical_url == "https://github.com/ZiYao00/github-learning-automation"


def test_reject_non_github():
    with pytest.raises(ValueError):
        resolve_repository("https://example.com/a/b")


def test_unique_note_path_does_not_overwrite(tmp_path: Path):
    first = tmp_path / "demo.md"
    first.write_text("x", encoding="utf-8")
    assert unique_note_path(tmp_path, "demo").name == "demo（2）.md"


def test_render_note_hides_empty_sections():
    job = {
        "collected_at": "2026-08-22T00:00:00+00:00",
        "repository": {
            "name": "demo",
            "full_name": "owner/demo",
            "html_url": "https://github.com/owner/demo",
            "homepage": "",
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        },
        "latest_release": {},
    }
    analysis = {
        "summary": "一句话。",
        "what_it_is": "一个示例项目。",
        "capabilities": ["能力 A"],
        "use_cases": [],
        "install": "pip install demo",
        "usage": "demo --help",
        "configuration": "",
        "caveats": [],
        "tags": ["开发工具", "Python"],
    }
    text = render_note(job, analysis)
    assert "## 适合什么场景" not in text
    assert "### 关键配置" not in text
    assert "## 如何使用" in text
    assert "github-note" in text


def test_finalize_publishes_note_and_retains_runtime(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    job_dir = runtime_root / "owner__demo__1234"
    job_dir.mkdir(parents=True)
    job = {
        "collected_at": "2026-08-22T00:00:00+00:00",
        "repository": {
            "name": "demo",
            "full_name": "owner/demo",
            "html_url": "https://github.com/owner/demo",
            "homepage": "",
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        },
        "latest_release": {},
    }
    analysis = {
        "source_status": "sufficient",
        "source_notes": "README 足够。",
        "summary": "用于演示。",
        "what_it_is": "一个示例仓库。",
        "capabilities": ["能力 A"],
        "use_cases": ["测试"],
        "install": "",
        "usage": "",
        "configuration": "",
        "caveats": [],
        "tags": ["开发工具", "Python"],
        "coverage_review": {"status": "passed", "notes": "已复核"},
    }
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    (job_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    result = finalize_job(settings, job_dir)

    assert result["status"] == "note_ready"
    assert result["runtime_status"] == "retained_for_audit"
    assert job_dir.is_dir()
    assert (notes_root / "demo.md").is_file()


def test_source_insufficient_is_normal_status(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    job_dir = runtime_root / "owner__demo__1234"
    job_dir.mkdir(parents=True)
    job = {
        "collected_at": "2026-08-22T00:00:00+00:00",
        "repository": {"name": "demo", "full_name": "owner/demo", "html_url": "https://github.com/owner/demo"},
        "latest_release": {},
    }
    analysis = {
        "source_status": "insufficient",
        "source_notes": "README 只有项目名，没有用途或使用方式。",
        "coverage_review": {"status": "pending", "notes": ""},
    }
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    (job_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    result = finalize_job(settings, job_dir)

    assert result["status"] == "source_insufficient"
    assert "README" in result["reason"]
    assert not notes_root.exists()


def test_prepare_refuses_fallback_without_creating_runtime(tmp_path: Path):
    project = tmp_path / "project"
    settings = Settings(
        project,
        project / "notes" / "github" / "00-Inbox",
        project / ".runtime" / "github-learning",
        project / "config/local.json",
        True,
    )
    resolved = resolve_repository("owner/demo")
    bundle = SourceBundle(
        repository={"name": "demo", "full_name": "owner/demo", "html_url": "https://github.com/owner/demo"},
        readme="# Demo",
        root_entries=[],
        manifests={},
        latest_release=None,
    )

    result = prepare_job(settings, resolved, bundle)

    assert result["status"] == "configuration_required"
    assert not settings.runtime_root.exists()


def test_configure_notes_writes_explicit_vault_config(tmp_path: Path):
    project = tmp_path / "project"
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)

    path = configure_notes(project, vault_root=vault, notes_subdir="GitHub-Note")
    settings = load_settings(project)

    assert path == project / "config/local.json"
    assert settings.notes_is_fallback is False
    assert settings.notes_root == vault / "GitHub-Note"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["notes_subdir"] == "GitHub-Note"


def test_load_settings_without_config_uses_fallback_but_marks_it(tmp_path: Path):
    settings = load_settings(tmp_path)
    assert settings.notes_is_fallback is True
    assert settings.notes_source == "fallback"
    assert settings.notes_root == tmp_path / "notes" / "github" / "00-Inbox"


def test_auth_prefers_environment_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "example-token")
    auth = resolve_github_auth()
    assert auth.authenticated is True
    assert auth.source == "environment"
    assert auth.token == "example-token"


def test_frontmatter_quotes_special_tag_values():
    job = {
        "collected_at": "2026-08-22T00:00:00+00:00",
        "repository": {
            "name": "demo",
            "full_name": "owner/demo",
            "html_url": "https://github.com/owner/demo",
            "homepage": "",
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        },
        "latest_release": {},
    }
    analysis = {
        "summary": "一句话。",
        "what_it_is": "一个示例项目。",
        "capabilities": ["能力 A"],
        "tags": ["AI:Agent", "#工具"],
    }
    text = render_note(job, analysis)
    assert 'repo: "owner/demo"' in text
    assert '  - "AI:Agent"' in text
    assert '  - "工具"' in text


def test_auth_reuses_logged_in_gh_cli(monkeypatch):
    from types import SimpleNamespace
    import github_learning.auth as auth_module

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(auth_module.shutil, "which", lambda name: "C:/Program Files/GitHub CLI/gh.exe" if name == "gh" else None)
    monkeypatch.setattr(
        auth_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="gh-secret-token\n", stderr=""),
    )

    auth = resolve_github_auth()
    assert auth.authenticated is True
    assert auth.source == "gh_cli"
    assert auth.token == "gh-secret-token"


def _write_job(job_dir: Path, job: dict, analysis: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    (job_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")


def _valid_job(full_name: str = "owner/demo", *, publish_mode: str = "upsert") -> dict:
    owner, name = full_name.split("/", 1)
    return {
        "version": 2,
        "publish_mode": publish_mode,
        "collected_at": "2026-08-22T16:30:00+00:00",
        "collected_local_date": "2026-08-23",
        "repository": {
            "name": name,
            "full_name": full_name,
            "html_url": f"https://github.com/{owner}/{name}",
            "homepage": "",
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        },
        "latest_release": {},
        "collection_warnings": [],
    }


def _valid_analysis(summary: str = "用于演示。") -> dict:
    return {
        "source_status": "sufficient",
        "source_notes": "README 足够。",
        "summary": summary,
        "what_it_is": "一个示例仓库。",
        "capabilities": ["能力 A"],
        "use_cases": ["测试"],
        "install": "",
        "usage": "",
        "configuration": "",
        "source_conflicts": [],
        "caveats": [],
        "tags": ["开发工具", "Python"],
        "coverage_review": {"status": "passed", "notes": "已复核"},
    }


def test_render_note_uses_local_collection_date_and_conflict_callout():
    job = _valid_job()
    analysis = _valid_analysis()
    analysis["source_conflicts"] = ["README 开头和结尾的许可证说明不一致。"]
    text = render_note(job, analysis)
    assert 'updated: "2026-08-23"' in text
    assert "> [!risk] 官方资料存在冲突" in text
    assert "许可证说明不一致" in text


def test_upsert_refreshes_same_repo_and_preserves_personal_tail(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    existing_job = _valid_job()
    existing_analysis = _valid_analysis("旧摘要")
    existing_text = render_note(existing_job, existing_analysis).replace(
        "<!-- 此处及其后的个人内容会在 refresh 时保留。 -->",
        "我的人工实测：保留这一行。",
    )
    existing_path = notes_root / "demo.md"
    existing_path.write_text(existing_text, encoding="utf-8")

    job_dir = runtime_root / "owner__demo__new"
    job = _valid_job()
    analysis = _valid_analysis("新摘要")
    _write_job(job_dir, job, analysis)
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    result = finalize_job(settings, job_dir)

    assert result["status"] == "note_ready"
    assert result["publish_action"] == "refreshed"
    assert result["note_path"] == str(existing_path)
    text = existing_path.read_text(encoding="utf-8")
    assert "新摘要" in text
    assert "旧摘要" not in text
    assert "我的人工实测：保留这一行。" in text
    assert not (notes_root / "demo（2）.md").exists()


def test_same_repo_name_from_different_owner_gets_owner_suffix(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    (notes_root / "demo.md").write_text(render_note(_valid_job("ownerA/demo"), _valid_analysis()), encoding="utf-8")

    job_dir = runtime_root / "ownerB__demo__new"
    _write_job(job_dir, _valid_job("ownerB/demo"), _valid_analysis())
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    result = finalize_job(settings, job_dir)

    assert result["status"] == "note_ready"
    assert result["publish_action"] == "created"
    assert Path(result["note_path"]).name == "demo · ownerB.md"


def test_legacy_refresh_is_blocked_without_explicit_replace(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    legacy_path = notes_root / "demo.md"
    legacy_text = '---\nrepo: "owner/demo"\n---\n\n# demo\n\n人工补充内容\n'
    legacy_path.write_text(legacy_text, encoding="utf-8")

    job_dir = runtime_root / "owner__demo__new"
    _write_job(job_dir, _valid_job(), _valid_analysis("新摘要"))
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    blocked = finalize_job(settings, job_dir)
    assert blocked["status"] == "legacy_note_refresh_blocked"
    assert legacy_path.read_text(encoding="utf-8") == legacy_text

    replaced = finalize_job(settings, job_dir, replace_legacy=True)
    assert replaced["status"] == "note_ready"
    assert replaced["publish_action"] == "refreshed"
    backup = Path(replaced["legacy_backup_path"])
    assert backup.read_text(encoding="utf-8") == legacy_text
    assert "新摘要" in legacy_path.read_text(encoding="utf-8")


def test_explicit_new_note_keeps_multiple_versions_for_same_repo(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    (notes_root / "demo.md").write_text(render_note(_valid_job(), _valid_analysis()), encoding="utf-8")

    job_dir = runtime_root / "owner__demo__new"
    _write_job(job_dir, _valid_job(publish_mode="new"), _valid_analysis("第二版"))
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    result = finalize_job(settings, job_dir)
    assert result["status"] == "note_ready"
    assert Path(result["note_path"]).name == "demo（2）.md"


def test_collection_warnings_render_as_coverage_meta():
    job = _valid_job()
    job["collection_warnings"] = ["Latest Release 读取失败，已按可选来源跳过。"]
    text = render_note(job, _valid_analysis())
    assert "> [!meta] 采集覆盖提醒" in text
    assert "Latest Release" in text


def test_manifest_prefers_raw_download_and_optional_release_failure_is_warning(monkeypatch):
    import github_learning.github_client as client
    from github_learning.auth import GitHubAuth

    calls: list[str] = []

    def fake_json(url, auth=None):
        calls.append(url)
        if url.endswith("/repos/owner/demo"):
            return {"name": "demo", "full_name": "owner/demo", "html_url": "https://github.com/owner/demo"}
        if url.endswith("/repos/owner/demo/readme"):
            return {"encoding": "base64", "content": "IyBEZW1v"}
        if url.endswith("/repos/owner/demo/contents"):
            return [
                {
                    "name": "pyproject.toml",
                    "type": "file",
                    "download_url": "https://raw.githubusercontent.com/owner/demo/main/pyproject.toml",
                }
            ]
        if url.endswith("/repos/owner/demo/releases/latest"):
            raise client.GitHubFetchError("rate_limited_or_forbidden", "release limited", 403)
        raise AssertionError(url)

    monkeypatch.setattr(client, "_request_json", fake_json)
    monkeypatch.setattr(client, "_request_text", lambda url, auth: "[project]\nname='demo'\n")
    bundle = client.fetch_repository_sources("owner/demo", GitHubAuth("token", "environment", True))

    assert bundle.manifests["pyproject.toml"].startswith("[project]")
    assert any("Latest Release" in warning for warning in bundle.warnings)
    assert not any(url.endswith("/contents/pyproject.toml") for url in calls)


def test_configure_notes_root_requires_existing_directory(tmp_path: Path):
    project = tmp_path / "project"
    missing = tmp_path / "missing-notes"

    with pytest.raises(ConfigurationError) as exc_info:
        configure_notes(project, notes_root=missing)

    assert exc_info.value.code == "notes_root_missing"
    assert not (project / "config/local.json").exists()


def test_load_settings_rejects_stale_notes_root(tmp_path: Path):
    config = tmp_path / "config/local.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"notes_root": str(tmp_path / "missing-notes")}), encoding="utf-8")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(tmp_path)

    assert exc_info.value.code == "notes_root_missing"


def test_repository_identity_only_reads_frontmatter():
    body_only = "# Demo\n\n```yaml\nrepo: owner/demo\n```\n"
    frontmatter = '---\nrepo: "owner/demo"\n---\n\n# Demo\n'

    assert repository_identity_from_text(body_only) is None
    assert repository_identity_from_text(frontmatter) == "owner/demo"


def test_preflight_detects_managed_refresh_before_collection(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    existing = notes_root / "demo.md"
    existing.write_text(render_note(_valid_job(), _valid_analysis()), encoding="utf-8")
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    result = preflight_publish(settings, "owner/demo")

    assert result["status"] == "ready"
    assert result["operation"] == "refresh"
    assert result["note_path"] == str(existing)
    assert not runtime_root.exists()


def test_preflight_blocks_legacy_before_collection_and_allows_explicit_migration(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    legacy = notes_root / "demo.md"
    legacy.write_text('---\nrepo: "owner/demo"\n---\n\n# demo\n', encoding="utf-8")
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)

    blocked = preflight_publish(settings, "owner/demo")
    allowed = preflight_publish(settings, "owner/demo", replace_legacy=True)

    assert blocked["status"] == "legacy_note_refresh_blocked"
    assert allowed["status"] == "ready"
    assert allowed["operation"] == "replace_legacy"
    assert not runtime_root.exists()


def test_prepare_records_legacy_authorization_in_job(tmp_path: Path):
    project = tmp_path / "project"
    runtime_root = project / ".runtime" / "github-learning"
    notes_root = project / "notes"
    notes_root.mkdir(parents=True)
    (notes_root / "demo.md").write_text('---\nrepo: "owner/demo"\n---\n\n# demo\n', encoding="utf-8")
    settings = Settings(project, notes_root, runtime_root, project / "config/local.json", False)
    resolved = resolve_repository("owner/demo")
    bundle = SourceBundle(
        repository={"name": "demo", "full_name": "owner/demo", "html_url": "https://github.com/owner/demo"},
        readme="# Demo",
        root_entries=[],
        manifests={},
        latest_release=None,
    )

    result = prepare_job(settings, resolved, bundle, replace_legacy=True)
    job = json.loads((Path(result["job_dir"]) / "job.json").read_text(encoding="utf-8"))

    assert result["status"] == "analysis_required"
    assert job["publish_operation"] == "replace_legacy"
    assert job["replace_legacy_authorized"] is True


def test_render_note_declares_learning_lab_and_github_extension_classes():
    text = render_note(_valid_job(), _valid_analysis())

    assert "  - learning-page" in text
    assert "  - github-note" in text


def test_obsidian_extension_requires_core_without_video_dependency():
    project_root = Path(__file__).resolve().parents[1]
    core = (project_root / "obsidian/snippets/learning-lab.css").read_text(encoding="utf-8")
    extension = (project_root / "obsidian/snippets/github-note.css").read_text(encoding="utf-8")

    assert ".learning-page" in core
    assert ".learning-page.github-note" in extension
    assert "Requires: learning-lab.css" in extension
    assert "video-note" not in extension


def test_public_sources_do_not_embed_personal_vault_path():
    project_root = Path(__file__).resolve().parents[1]
    forbidden = "M:" + "\\ZiYao" + "\\Note"
    excluded_parts = {".git", ".runtime", "__pycache__", "dist", "notes"}
    excluded_names = {"local.json"}

    for path in project_root.rglob("*"):
        if not path.is_file() or path.name in excluded_names or any(part in excluded_parts for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".md", ".toml", ".json", ".yaml", ".yml", ".css", ".txt"}:
            continue
        assert forbidden not in path.read_text(encoding="utf-8", errors="ignore"), str(path)
