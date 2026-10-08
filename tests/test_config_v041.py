import json
from pathlib import Path

from github_learning.config import configure_defaults, configure_notes, load_settings


def test_unconfigured_project_exposes_project_defaults_without_writing(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    settings = load_settings(project)

    assert settings.notes_root == project / "notes/github"
    assert settings.research_root == project / "research/github"
    assert settings.notes_is_fallback is True
    assert settings.research_is_fallback is True
    assert not (project / "config/local.json").exists()
    assert not settings.notes_root.exists()
    assert not settings.research_root.exists()


def test_configure_defaults_creates_project_storage_and_local_config(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    configure_defaults(project)
    settings = load_settings(project)
    payload = json.loads((project / "config/local.json").read_text(encoding="utf-8"))

    assert payload["notes_root"] == "notes/github"
    assert payload["research_root"] == "research/github"
    assert settings.notes_root == (project / "notes/github").resolve()
    assert settings.research_root == (project / "research/github").resolve()
    assert settings.notes_is_fallback is False
    assert settings.research_is_fallback is False


def test_existing_direct_vault_keeps_note_storage_when_accepting_defaults(tmp_path: Path):
    project = tmp_path / "project"
    vault = tmp_path / "vault"
    project.mkdir()
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "GitHub-Note").mkdir()

    configure_notes(project, vault_root=vault, notes_subdir="GitHub-Note")
    configure_defaults(project)

    settings = load_settings(project)
    payload = json.loads((project / "config/local.json").read_text(encoding="utf-8"))

    assert "notes_root" not in payload
    assert payload["research_root"] == "research/github"
    assert settings.notes_root == vault / "GitHub-Note"
    assert settings.notes_source == "local_vault"
    assert settings.research_root == (project / "research/github").resolve()


def test_hybrid_notes_root_and_vault_can_coexist(tmp_path: Path):
    project = tmp_path / "project"
    notes = project / "notes/github"
    research = project / "research/github"
    vault = tmp_path / "vault"
    notes.mkdir(parents=True)
    research.mkdir(parents=True)
    (vault / ".obsidian").mkdir(parents=True)

    configure_notes(project, notes_root=notes, research_root=research)
    configure_notes(project, vault_root=vault, notes_subdir="GitHub-Note")

    settings = load_settings(project)
    payload = json.loads((project / "config/local.json").read_text(encoding="utf-8"))

    assert payload["notes_root"] == str(notes.resolve())
    assert payload["vault_root"] == str(vault.resolve())
    assert settings.notes_root == notes.resolve()
    assert settings.vault_root == vault.resolve()
    assert settings.notes_subdir == Path("GitHub-Note")
    assert settings.notes_source == "local_notes_root_with_vault"
