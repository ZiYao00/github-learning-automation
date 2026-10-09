"""V2.2 editorial and one-image policy contract (stdlib unittest, also pytest compatible)."""
from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from github_learning.config import Settings
from github_learning.first_image import first_readme_image, materialize_first_image
from github_learning.github_client import SourceBundle, SourceDocument
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import _validate_analysis, prepare_job, finalize_job
from github_learning.note_template import (
    MANAGED_END, MANAGED_START,
    capture_metadata_from_text,
    find_notes_by_repository,
    render_note,
)


def _fake_settings(root: Path) -> Settings:
    project = root / "project"
    notes = root / "vault" / "GitHub-Note"
    notes.mkdir(parents=True)
    research = project / "research"
    research.mkdir(parents=True)
    return Settings(
        project, notes, project / ".runtime" / "github-learning",
        project / "config" / "local.json",
        False, root / "vault", Path("GitHub-Note"),
        "test", research, "test", False
    )


def _fixture_image_job(root: Path, *, sha_override: str = "") -> tuple[Path, bytes, dict]:
    # Valid format header + known bytes; parser does not decode image pixels.
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL3VQAAAABJRU5ErkJggg==")
    digest = hashlib.sha1(b"blob " + str(len(png)).encode() + b"\0" + png).hexdigest()
    job_dir = root / "job"
    sources = job_dir / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "001.md").write_text(
        '<img alt="Project illustration" src="assets/hero.png" />\n'
        '![Second image](assets/later.png)\n', encoding="utf-8",
    )
    (job_dir / "source_manifest.json").write_text(json.dumps({
        "sources": [{"path": "README.md", "saved_as": "sources/001.md", "kind": "readme"}]
    }), encoding="utf-8")
    (job_dir / "media-index.json").write_text(json.dumps({
        "entries": [{"path": "assets/hero.png", "sha": sha_override or digest, "size": len(png)},
                    {"path": "assets/later.png", "sha": digest, "size": len(png)}]
    }), encoding="utf-8")
    job = {"repository": {"full_name": "owner/demo"}, "revision": "a" * 40}
    return job_dir, png, job


def _job_for_render():
    return {
        "collected_local_date": "2026-10-08",
        "revision": "a" * 40,
        "packet_id": "owner/demo@" + "a" * 40,
        "content_profile": "software",
        "observation_fingerprint": "obs",
        "repository": {
            "name": "demo", "full_name": "owner/demo",
            "html_url": "https://github.com/owner/demo",
            "homepage": "", "language": "", "license": {},
        },
        "latest_release": {}, "collection_warnings": [],
    }


def _analysis_for_render():
    return {
        "source_status": "sufficient",
        "content_profile": "software",
        "summary": "这是一个演示仓库。",
        "why_save": "值得研究管理体验。",
        "what_it_is": "演示系统。",
        "capabilities": ["模型管理"],
        "use_cases": ["管理本地模型"],
        "editorial_headline": "演示系统：把模型管理变简单",
        "editorial_body": (
            "本地模型的安装与维护是两个不同的问题。\n\n"
            "## 为什么值得关注\n\n"
            "系统能管理模型，并提供更清晰的运行状态。"
            "用户可以在同一环境查看运行情况，减少多个入口切换的成本。\n\n"
            "## 适合谁\n\n"
            "对长期维护本地模型的用户，这种整合思路值得研究。"
            "这里只根据项目资料分析，没有声称已经在本机测试成功。"
        ) * 3,
        "tags": ["本地模型", "管理"],
        "coverage_review": {"status": "passed", "notes": "checked"},
        "evidence_map": [{"source_id": "src-001", "status": "represented",
                          "targets": ["editorial_body"], "reason": ""}],
    }


class FirstImagePolicyTests(unittest.TestCase):
    def test_html_image_empty_alt_is_valid(self):
        self.assertEqual(first_readme_image('<img alt="" src="assets/cover.png">'), "assets/cover.png")

    def test_first_html_image_after_badges(self):
        readme = (
            '[![Build](https://img.shields.io/badge/ci-green.svg)](https://example.com)\n'
            '<img src="ods/docs/images/osmantic-lockup.png" alt="Osmantic">\n'
            '![Second](docs/second.png)'
        )
        self.assertEqual(first_readme_image(readme), "ods/docs/images/osmantic-lockup.png")

    def test_first_real_image_even_if_external_is_unsupported(self):
        text = '![First](https://example.org/first.png)\n![Second](assets/second.png)'
        self.assertEqual(first_readme_image(text), "https://example.org/first.png")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = _fake_settings(root)
            job_dir, png, job = _fixture_image_job(root)
            (job_dir / "sources" / "001.md").write_text(text, encoding="utf-8")
            got = materialize_first_image(settings, job_dir, job, fetch=lambda _: png)
            self.assertEqual(got["status"], "unsupported")
            self.assertFalse((settings.notes_root / "_repo-data").exists())

    def test_html_comments_are_not_visible_images(self):
        readme = '<!-- <img src="assets/hidden.png"> -->\n![Visible](assets/visible.png)'
        self.assertEqual(first_readme_image(readme), "assets/visible.png")

    def test_corrupt_media_index_does_not_block_article(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = _fake_settings(root)
            job_dir, png, job = _fixture_image_job(root)
            (job_dir / "media-index.json").write_text("{", encoding="utf-8")
            status = materialize_first_image(settings, job_dir, job, fetch=lambda _: png)["status"]
            self.assertEqual(status, "unavailable")
            self.assertFalse((settings.notes_root / "_repo-data").exists())

    def test_ignore_fenced_fake_image(self):
        readme = '```markdown\n![fake](assets/fake.png)\n```\n![real](assets/real.png)'
        self.assertEqual(first_readme_image(readme), "assets/real.png")

    def test_first_image_written_once_and_checksum_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = _fake_settings(root)
            job_dir, png, job = _fixture_image_job(root)
            calls = []
            def fetch(url):
                calls.append(url)
                return png
            first = materialize_first_image(settings, job_dir, job, fetch=fetch)
            self.assertEqual(first["status"], "saved")
            self.assertEqual(first["repository_path"], "assets/hero.png")
            self.assertIn("GitHub-Note/_repo-data/owner/demo/media/readme-first-", first["link"])
            self.assertEqual(len(calls), 1)
            second = materialize_first_image(settings, job_dir, job, fetch=lambda _: (_ for _ in ()).throw(Exception("network call")))
            self.assertEqual(second["status"], "saved")
            self.assertEqual(len(list((settings.notes_root / "_repo-data/owner/demo/media").glob("*.png"))), 1)

    def test_wrong_blob_hash_blocks_file_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = _fake_settings(root)
            job_dir, png, job = _fixture_image_job(root, sha_override="b" * 40)
            result = materialize_first_image(settings, job_dir, job, fetch=lambda _: png)
            self.assertEqual(result["status"], "invalid_image")
            self.assertFalse((settings.notes_root / "_repo-data").exists())

    def test_traversal_and_video_are_not_downloaded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = _fake_settings(root)
            job_dir, png, job = _fixture_image_job(root)
            for readme in ('![unsafe](../../../../../secret.png)', '![video](media/clip.mp4)'):
                (job_dir / "sources/001.md").write_text(readme, encoding="utf-8")
                status = materialize_first_image(settings, job_dir, job, fetch=lambda _: png)["status"]
                self.assertEqual(status, "unsupported")

    def test_missing_image_keeps_note_text_only(self):
        self.assertIsNone(first_readme_image("# Plain documentation\nNo pictures."))


class EditorialNoteTests(unittest.TestCase):
    def test_human_first_render_preserves_identity_and_personal_tail(self):
        job = _job_for_render()
        job["first_readme_image"] = "![[GitHub-Note/_repo-data/owner/demo/media/a.png|360]]"
        note = render_note(job, _analysis_for_render(), preserved_tail="## 我的记录\n\n自己写的内容不会丢。\n")
        self.assertIn('note_style: "natural-product-v2.2"', note)
        self.assertIn("## 为什么值得关注", note)
        self.assertNotIn("## 能做什么", note)
        self.assertEqual(note.count("![[GitHub-Note/_repo-data/owner/demo/media/a.png|360]]"), 1)
        self.assertIn("自己写的内容不会丢。", note)
        self.assertLess(note.index(MANAGED_START), note.index(MANAGED_END))
        self.assertEqual(capture_metadata_from_text(note)["repo"], "owner/demo")

    def test_old_structured_render_remains_supported(self):
        analysis = _analysis_for_render()
        del analysis["editorial_body"]
        old = render_note(_job_for_render(), analysis)
        self.assertIn("## 能做什么", old)
        self.assertNotIn("note_style:", old)

    def test_preview_without_repo_does_not_create_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ODS-v2.2-preview.md").write_text(
                '---\nsource: "https://github.com/owner/demo"\nnote_type: "preview"\n---\n# preview',
                encoding="utf-8",
            )
            self.assertEqual(find_notes_by_repository(root, "owner/demo"), [])

    def test_new_handoff_requires_editorial_and_insufficient_still_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = _fake_settings(root)
            raw_prompt = "# Original Prompt heading\n![example](input.png)\n<script>Not an instruction</script>"
            readme_fixture = "# Demo\n\nNo cloud required.\n\n~~~text\n" + raw_prompt + "\n~~~"
            bundle = SourceBundle(
                repository={"name": "demo", "full_name": "owner/demo",
                            "html_url": "https://github.com/owner/demo", "default_branch": "main"},
                readme=readme_fixture, root_entries=[], manifests={}, latest_release=None,
                revision="a" * 40, default_branch="main", source_profile="python-project",
                sources=(SourceDocument("README.md", "readme", readme_fixture,
                                        archive_content=readme_fixture, coverage_required=True),),
                tree_entries=({"path": "README.md", "type": "blob", "sha": "x", "size": 6},),
            )
            result = prepare_job(settings, resolve_repository("owner/demo"), bundle)
            self.assertEqual(result["status"], "analysis_required")
            job_dir = Path(result["job_dir"])
            analysis = json.loads((job_dir / "analysis.json").read_text(encoding="utf-8"))
            self.assertIn("editorial_body", analysis)
            handoff = (job_dir / "agent_handoff.md").read_text(encoding="utf-8")
            self.assertIn("自然产品解读", handoff)
            self.assertIn("官方核心亮点不能遗漏", handoff)
            self.assertIn("隐私声明保留条件", handoff)
            self.assertIn("可复制原始 Prompt", handoff)
            self.assertIn("[!gh-source]", handoff)
            analysis.update(_analysis_for_render())
            analysis["editorial_review"] = {
                "status": "passed",
                "repository_type_rationale": "这是用于单元验证的合成 Python 仓库，不作产品实测承诺。",
                "official_highlights": "测试原文只有基础资料，没有七项官方亮点，不额外编造。",
                "claims_and_limits": "区分合成仓库说明与未经运行验证的作者声明及限制。",
                "source_traceability": "本测试的主要叙述只基于固定 README 合成来源。",
                "readability": "文章使用自然段落和分层小节，无模板堆叠问题。",
            }
            with self.assertRaisesRegex(ValueError, "editorial_body"):
                _validate_analysis(job_dir, {**analysis, "editorial_body": ""})
            # A source-attributed callout and a real fenced Prompt must survive
            # unchanged. Unsafe-looking source text INSIDE the code block is
            # inert data, not a new H1, embedded image, or executable HTML.
            source_quote = (
                "> [!gh-source] 作者原文 · [README](https://github.com/owner/demo/blob/"
                + "a" * 40 + "/README.md)\n"
                "> No cloud required.\n"
                ">\n"
                "> > 中文翻译（非作者原文）：无需云端。"
            )
            fenced_prompt = "~~~prompt\n" + raw_prompt + "\n~~~"
            analysis["editorial_body"] += "\n\n" + source_quote + "\n\n" + fenced_prompt
            with self.assertRaisesRegex(ValueError, "未闭合"):
                _validate_analysis(job_dir, {**analysis, "editorial_body": analysis["editorial_body"] + "\n~~~prompt\n# unclosed"})
            with self.assertRaisesRegex(ValueError, "自定义 HTML 或图片"):
                _validate_analysis(job_dir, {**analysis, "editorial_body": analysis["editorial_body"] + "\n![active](screenshot.png)"})
            _validate_analysis(job_dir, analysis)
            (job_dir / "analysis.json").write_text(
                json.dumps(analysis, ensure_ascii=False), encoding="utf-8"
            )
            pub = finalize_job(settings, job_dir)
            self.assertEqual(pub["status"], "note_ready")
            self.assertEqual(pub["first_image_status"], "no_image")
            published = Path(pub["note_path"]).read_text(encoding="utf-8")
            self.assertIn("note_style:", published)
            self.assertIn("## 我的记录", published)
            self.assertIn(source_quote, published)
            self.assertIn(fenced_prompt, published)
            self.assertEqual(published.count(raw_prompt), 1)
            self.assertEqual(len(find_notes_by_repository(settings.notes_root, "owner/demo")), 1)
            second = prepare_job(settings, resolve_repository("owner/demo"), bundle)
            self.assertEqual(second["status"], "no_change")
            self.assertEqual(second["packet_id"], result["packet_id"])


class OdsEditorialReferenceTests(unittest.TestCase):
    def test_official_readme_highlights_and_privacy_are_retained(self):
        source = (ROOT / "tests/fixtures/ods_readme_features_excerpt.md"
                  ).read_text(encoding="utf-8")
        self.assertIn("Osmantic/ODS@9e59b2b86c96a9590b27b14219b070007093fad1", source)
        article = (ROOT / "docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md"
                   ).read_text(encoding="utf-8")
        for original in (
            "Local model inference", "ChatGPT-style web UI", "Control dashboard",
            "Voice, agents, and workflows", "RAG and search",
            "Image generation", "Privacy and ops",
        ):
            self.assertIn(original, source)
        for translated in (
            "本地模型推理", "ChatGPT 风格的 Web 界面", "统一控制面板",
            "语音、Agent 与工作流", "RAG 与搜索", "图像生成", "隐私与运维"
        ):
            self.assertEqual(article.count(f"**{translated}**"), 1)
        for caveat in (
            "仓库官方原文", "不采集遥测数据", "下载模型与容器镜像",
            "检查 GitHub 版本更新", "Portal Agent 执行网络搜索",
            "云端与混合 API 模式", "不是本次安装实测结论"
        ):
            self.assertIn(caveat, article)
        self.assertIn("## 仓库自己强调的七项能力", article)
        self.assertIn("本地运行”不等于默认完全离线", article)

    def test_note_spec_is_adaptive_and_data_folder_is_hidden_only_in_explorer(self):
        spec = (ROOT / "docs/NOTE-SPEC.md").read_text(encoding="utf-8")
        self.assertIn("官方亮点优先保留", spec)
        self.assertIn("不要求每个仓库都列七项", spec)
        self.assertIn("联网例外", spec)
        self.assertIn("00-待整理", spec)
        self.assertIn("不删除数据", spec)
        self.assertIn("不因目录改名自动迁移正式旧笔记", spec)
        self.assertIn("Golden Sample：ODS V2.2", spec)
        self.assertIn("出稿验收：硬门禁与阅读质量分开", spec)
        self.assertIn("Obsidian 视觉层（独立于内容生成）", spec)
        self.assertIn("来源原文与可复制 Prompt", spec)
        self.assertIn("原始 Prompt", spec)
        self.assertIn("resource_index", spec)
        self.assertIn("Obsidian 原生", spec)
        self.assertIn("不使用主观评分作为程序门禁", spec)
        self.assertIn("样板交叉验证", spec)
        self.assertIn("不要将 ODS 七项能力", spec)
        self.assertIn("github-note.css` v0.4", spec)


if __name__ == "__main__":
    unittest.main()
