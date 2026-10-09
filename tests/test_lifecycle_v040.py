import json
from pathlib import Path

from github_learning.config import Settings
from github_learning.github_client import SourceBundle, SourceDocument
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import finalize_job, prepare_job, preflight_publish


def _settings(tmp_path: Path) -> Settings:
    project = tmp_path / "project"
    notes = project / "notes"
    research = project / "research"
    notes.mkdir(parents=True)
    research.mkdir(parents=True)
    return Settings(
        project,
        notes,
        project / ".runtime" / "github-learning",
        project / "config/local.json",
        False,
        notes_source="test",
        research_root=research,
        research_source="test",
    )


def _bundle() -> SourceBundle:
    return SourceBundle(
        repository={
            "name": "demo",
            "full_name": "owner/demo",
            "html_url": "https://github.com/owner/demo",
            "default_branch": "main",
        },
        readme="# Demo",
        root_entries=[],
        manifests={},
        latest_release=None,
        revision="abc123",
        default_branch="main",
        source_profile="python-project",
        sources=(SourceDocument("README.md", "readme", "# Demo", coverage_required=True, archive_content="# Demo"),),
        tree_entries=({"path": "README.md", "type": "blob", "sha": "readme-sha", "size": 6},),
    )


def _complete_analysis(job_dir: Path) -> None:
    path = job_dir / "analysis.json"
    analysis = json.loads(path.read_text(encoding="utf-8"))
    analysis.update(
        {
            "source_status": "sufficient",
            "why_save": "一个用于验证 v0.4 生命周期的仓库。",
            "editorial_contract_version": "2.2",
            "editorial_headline": "合成生命周期：数据与可读笔记",
            "editorial_body": "本测试依据合成 README 检查版本化笔记发布。" * 18,
            "editorial_review": {
                "status": "passed",
                "repository_type_rationale": "合成测试的类型仅用于校验工作流，新版资料不会外推。",
                "official_highlights": "资料只有演示内容，不声明真实的官方亮点清单。",
                "claims_and_limits": "这是合成证据，不等于实际安装或模型测试。",
                "source_traceability": "所有表述均限于测试数据中的 README 说明。",
                "readability": "单篇文章优先保留自然阅读和清晰内容边界。",
            },
            "summary": "演示仓库。",
            "what_it_is": "用于测试 Capture Note。",
            "capabilities": ["能力 A"],
            "use_cases": ["测试"],
            "tags": ["开发工具", "Python"],
            "coverage_review": {"status": "passed", "notes": "已复核"},
        }
    )
    for entry in analysis["evidence_map"]:
        entry["status"] = "represented"
        entry["targets"] = ["summary"]
        entry["reason"] = ""
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_prepare_archives_packet_before_analysis(tmp_path: Path):
    settings = _settings(tmp_path)
    result = prepare_job(settings, resolve_repository("owner/demo"), _bundle())
    job = json.loads((Path(result["job_dir"]) / "job.json").read_text(encoding="utf-8"))

    assert result["status"] == "analysis_required"
    assert result["packet_status"] == "packet_archived"
    assert result["packet_id"] == "owner/demo@abc123"
    assert Path(result["packet_path"]).is_dir()
    assert job["version"] == 7
    assert job["editorial_contract_version"] == "2.2"
    assert job["state"] == "analysis_required"


def test_second_prepare_same_packet_and_observation_returns_no_change(tmp_path: Path):
    settings = _settings(tmp_path)
    first = prepare_job(settings, resolve_repository("owner/demo"), _bundle())
    first_job = Path(first["job_dir"])
    _complete_analysis(first_job)
    published = finalize_job(settings, first_job)

    second = prepare_job(settings, resolve_repository("owner/demo"), _bundle())

    assert published["status"] == "note_ready"
    assert second["status"] == "no_change"
    assert second["packet_id"] == first["packet_id"]


def test_legacy_active_job_requires_explicit_restart(tmp_path: Path):
    settings = _settings(tmp_path)
    job_dir = settings.runtime_root / "owner__demo__legacy"
    job_dir.mkdir(parents=True)
    (job_dir / "job.json").write_text(
        json.dumps(
            {
                "version": 5,
                "job_id": job_dir.name,
                "state": "analysis_required",
                "collected_at": "2026-10-01T00:00:00+00:00",
                "repository": {"full_name": "owner/demo"},
            }
        ),
        encoding="utf-8",
    )

    result = preflight_publish(settings, "owner/demo")

    assert result["status"] == "legacy_job_restart_required"
