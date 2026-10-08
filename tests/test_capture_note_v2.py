from github_learning.note_template import capture_metadata_from_text, render_minimal_note, render_note


def _job():
    return {
        "collected_at": "2026-10-07T12:00:00+00:00",
        "collected_local_date": "2026-10-07",
        "revision": "abc123",
        "packet_id": "owner/demo@abc123",
        "content_profile": "agent-skill",
        "observation_fingerprint": "obs123",
        "repository": {
            "name": "demo",
            "full_name": "owner/demo",
            "html_url": "https://github.com/owner/demo",
            "homepage": "",
            "language": "",
            "license": {},
        },
        "latest_release": {},
        "collection_warnings": [],
        "source_paths": ["README.md", "SKILL.md"],
        "resource_paths": ["assets/template.md"],
    }


def test_capture_note_v2_renders_map_resources_and_packet_identity():
    analysis = {
        "content_profile": "agent-skill",
        "why_save": "以后值得回来继续研究。",
        "summary": "一个演示 Skill。",
        "what_it_is": "一个知识型 Skill。",
        "capabilities": ["能力 A"],
        "use_cases": ["学习"],
        "knowledge_map": [{"title": "01 工作流", "summary": "任务路由与执行。"}],
        "resource_index": [{"title": "模板", "purpose": "复用输出结构", "path": "assets/template.md"}],
        "install": "",
        "usage": "",
        "configuration": "",
        "source_conflicts": [],
        "caveats": [],
        "tags": ["Skill", "学习"],
    }

    text = render_note(_job(), analysis)
    metadata = capture_metadata_from_text(text)

    assert metadata["packet_id"] == "owner/demo@abc123"
    assert metadata["content_profile"] == "agent-skill"
    assert metadata["analysis_status"] == "sufficient"
    assert "## 为什么值得保存" in text
    assert "## 内容地图" in text
    assert "## 可复用资源" in text
    assert "## 深入研究入口" in text
    assert "## 我的记录" in text


def test_minimal_capture_note_is_still_saved():
    analysis = {
        "source_status": "insufficient",
        "source_notes": "说明不足。",
        "why_save": "先收藏，未来再研究。",
        "tags": [],
    }

    text = render_minimal_note(_job(), analysis)
    metadata = capture_metadata_from_text(text)

    assert metadata["capture_status"] == "saved"
    assert metadata["analysis_status"] == "insufficient"
    assert "待进一步研究" in text
    assert "Research Packet" in text
    assert "## 我的记录" in text
