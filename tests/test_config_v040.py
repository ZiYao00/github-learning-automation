import json
from pathlib import Path

from github_learning.config import configure_notes, load_settings


def test_research_root_merge_preserves_note_configuration(tmp_path: Path):
    project = tmp_path / "project"
    vault = tmp_path / "vault"
    research = tmp_path / "research"
    (vault / ".obsidian").mkdir(parents=True)
    research.mkdir()

    configure_notes(project, vault_root=vault, notes_subdir="GitHub-Note")
    configure_notes(project, research_root=research)

    settings = load_settings(project)
    payload = json.loads((project / "config/local.json").read_text(encoding="utf-8"))

    assert settings.notes_root == vault / "GitHub-Note"
    assert settings.research_root == research
    assert payload["vault_root"] == str(vault.resolve())
    assert payload["research_root"] == str(research.resolve())


def test_note_reconfigure_preserves_research_root(tmp_path: Path):
    project = tmp_path / "project"
    vault = tmp_path / "vault"
    research = tmp_path / "research"
    (vault / ".obsidian").mkdir(parents=True)
    research.mkdir()

    configure_notes(project, vault_root=vault, notes_subdir="GitHub-Note", research_root=research)
    configure_notes(project, vault_root=vault, notes_subdir="GitHub-Note-V2")

    payload = json.loads((project / "config/local.json").read_text(encoding="utf-8"))
    settings = load_settings(project)

    assert payload["research_root"] == str(research.resolve())
    assert settings.notes_root == vault / "GitHub-Note-V2"
    assert settings.research_root == research
