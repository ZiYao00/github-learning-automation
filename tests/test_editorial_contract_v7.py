"""Portable stdlib tests: v7 policy enforcement, legacy v6 compatibility, pending folder."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.config import Settings
from github_learning.github_client import SourceBundle,SourceDocument
from github_learning.input_resolver import resolve_repository
from github_learning.lifecycle import prepare_job,finalize_job,_validate_analysis,_reuse_immutable_source_selection
from github_learning.note_template import find_notes_by_repository, render_note


def settings(root:Path)->Settings:
    project=root/"project";notes=root/"vault"/"GitHub-Note";research=project/"research"
    notes.mkdir(parents=True);research.mkdir(parents=True)
    return Settings(project,notes,project/".runtime"/"github-learning",
       project/"config"/"local.json",False,
       root/"vault",Path("GitHub-Note"),"test",research,"test",False)


def bundle()->SourceBundle:
    return SourceBundle(
      repository={"name":"demo","full_name":"editorial/demo",
                  "html_url":"https://github.com/editorial/demo","default_branch":"main"},
      readme="# Demo\n\nA synthetic repository for test-only validation.",
      root_entries=[],manifests={},latest_release=None,
      revision="abcdabcdabcdabcdabcdabcdabcdabcdabcdabcd",default_branch="main",
      source_profile="python-project",
      sources=(SourceDocument("README.md","readme","# Demo\nA synthetic repository.",
             coverage_required=True,archive_content="# Demo\nA synthetic repository."),),
      tree_entries=({"path":"README.md","type":"blob","sha":"sample","size":36},))


def finish_analysis(job_dir:Path):
    path=job_dir/"analysis.json"
    data=json.loads(path.read_text(encoding="utf-8"))
    data.update({
        "source_status":"sufficient",
        "why_save":"这是一次完整的合成回归测试，不代表真实仓库能力。",
        "summary":"测试版本化 V2.2 编辑流程的示例。",
        "what_it_is":"单元测试使用的虚拟仓库。",
        "capabilities":["审查写作字段","维护笔记身份"],
        "use_cases":["检查文档生成器"],
        "content_profile":"library",
        "editorial_headline":"示例仓库：版本契约测试",
        "editorial_body":(
          "读取一个仓库的 README 只能提供初步理解，编写正式笔记还需要清楚区分原始声明与验证事实。"
          "本页只展示合成测试数据，绝不宣称已经实测运行目标仓库。\n\n"
          "## 它提供的是什么\n\n"
          "项目源文件会被存入固定版本的 Research Packet，接着由 Agent 根据证据撰写独立的文字解读。"
          "写作流程应当保留核心功能概览，也要说明适用范围及没有证据的部分，不能用广告式语言替代核查。\n\n"
          "## 适用场景\n\n"
          "当另一位 Agent 接手同一份资料时，应从其历史包和规范文件恢复工作，而非随意套用旧的章节模板。"
          "如果缺少支持关键结论的来源，就必须标明限制而不是编造功能或假装安装成功。"
        ),
        "tags":["文档工具","知识归档"],
        "coverage_review":{"status":"passed","notes":"已经依据合成来源完成映射检查"},
        "editorial_review":{
            "status":"passed",
            "repository_type_rationale":"README 显示它是用于知识处理的合成仓库，因此作为软件包示例。",
            "official_highlights":"README 没有具体官方功能亮点清单，不额外伪造项目卖点。",
            "claims_and_limits":"本篇明确标注内容为单元测试，没有安装实测及隐私承诺。",
            "source_traceability":"只有 README 合成证据，因此限制在其描述可支持的流程。",
            "readability":"先解释需求和价值，再用两个不同层次的章节进行自然说明。",
        },
    })
    for entry in data["evidence_map"]:
        entry.update({"status":"represented","targets":["editorial_body"],"reason":""})
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return data


class EditorialV7Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings=settings(Path(self.tmp.name))
        result=prepare_job(self.settings,resolve_repository("editorial/demo"),bundle())
        self.assertEqual(result["status"],"analysis_required")
        self.job_dir=Path(result["job_dir"])

    def test_prepare_stamps_contract_and_handoff(self):
        job=json.loads((self.job_dir/"job.json").read_text(encoding="utf-8"))
        analysis=json.loads((self.job_dir/"analysis.json").read_text(encoding="utf-8"))
        handoff=(self.job_dir/"agent_handoff.md").read_text(encoding="utf-8")
        self.assertEqual(job["version"],8)
        self.assertEqual(job["editorial_contract_version"],"2.2")
        self.assertEqual(analysis["editorial_contract_version"],"2.2")
        self.assertEqual(analysis["evidence_set_id"],job["evidence_set_id"])
        self.assertEqual(analysis["editorial_review"]["status"],"pending")
        self.assertIn("旧章节模板",handoff)
        self.assertIn("Job v8",handoff)
        self.assertIn("evidence_set_id",handoff)
        self.assertFalse(find_notes_by_repository(self.settings.notes_root,"editorial/demo"))

    def test_existing_packet_reuses_pinned_original_sources_after_planner_upgrade(self):
        old = bundle()
        newly_selected = SourceDocument(
            "CHATGPT_PROMPT.md", "prompt_document", "Use CodexPro.\n",
            sha="b" * 40, size=len("Use CodexPro.\n"),
        )
        new_bundle = replace(old, sources=old.sources + (newly_selected,))
        reconciled = _reuse_immutable_source_selection(self.settings, new_bundle)
        self.assertEqual([s.path for s in reconciled.sources], [s.path for s in old.sources])
        self.assertEqual(reconciled.revision, old.revision)
        self.assertEqual(reconciled.readme, old.readme)

    def test_old_fields_cannot_bypass_v22(self):
        analysis=finish_analysis(self.job_dir)
        del analysis["editorial_body"]
        with self.assertRaisesRegex(ValueError,"editorial_body"):
            _validate_analysis(self.job_dir,analysis)
        with self.assertRaisesRegex(ValueError,"旧模板"):
            render_note(json.loads((self.job_dir/"job.json").read_text(encoding="utf-8")),analysis)
        self.assertFalse(find_notes_by_repository(self.settings.notes_root,"editorial/demo"))

    def test_contract_mismatch_and_missing_review_are_blocked(self):
        analysis=finish_analysis(self.job_dir)
        analysis["editorial_contract_version"]="2.1"
        with self.assertRaisesRegex(ValueError,"版本"):
            _validate_analysis(self.job_dir,analysis)
        analysis["editorial_contract_version"]="2.2"
        analysis["editorial_review"]["status"]="pending"
        with self.assertRaisesRegex(ValueError,"editorial_review"):
            _validate_analysis(self.job_dir,analysis)
        self.assertFalse(find_notes_by_repository(self.settings.notes_root,"editorial/demo"))

    def test_v7_publish_to_pending_and_no_change(self):
        finish_analysis(self.job_dir)
        published=finalize_job(self.settings,self.job_dir)
        self.assertEqual(published["status"],"note_ready")
        path=Path(published["note_path"])
        self.assertEqual(path.parent,self.settings.notes_root/"00-待整理")
        note=path.read_text(encoding="utf-8")
        self.assertIn('editorial_contract_version: "2.2"',note)
        self.assertIn("evidence_set_id:",note)
        self.assertIn('note_style: "natural-product-v2.2"',note)
        self.assertIn("## 我的记录",note)
        self.assertEqual(len(find_notes_by_repository(self.settings.notes_root,"editorial/demo")),1)
        repeated=prepare_job(self.settings,resolve_repository("editorial/demo"),bundle())
        self.assertEqual(repeated["status"],"no_change")
        self.assertEqual(path.read_text(encoding="utf-8"),note)

    def test_preexisting_v6_missing_editorial_still_renders(self):
        job_file=self.job_dir/"job.json"
        job=json.loads(job_file.read_text(encoding="utf-8"))
        job["version"]=6
        job.pop("editorial_contract_version",None)
        job_file.write_text(json.dumps(job,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        analysis=finish_analysis(self.job_dir)
        analysis.pop("editorial_body",None)
        analysis.pop("editorial_headline",None)
        analysis.pop("editorial_contract_version",None)
        analysis.pop("editorial_review",None)
        (self.job_dir/"analysis.json").write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        published=finalize_job(self.settings,self.job_dir)
        self.assertEqual(published["status"],"note_ready")
        note=Path(published["note_path"]).read_text(encoding="utf-8")
        self.assertIn("## 为什么值得保存",note)
        self.assertNotIn("editorial_contract_version:",note)

    def test_root_filename_collision_uses_owner_suffix_in_pending(self):
        old=self.settings.notes_root/"demo.md"
        old_data='---\nrepo: "somebody-else/demo"\n---\n\n# Old Note\n'
        old.write_text(old_data,encoding="utf-8")
        finish_analysis(self.job_dir)
        result=finalize_job(self.settings,self.job_dir)
        self.assertEqual(result["status"],"note_ready")
        self.assertEqual(Path(result["note_path"]).name,"demo · editorial.md")
        self.assertEqual(old.read_text(encoding="utf-8"),old_data)

    def test_new_note_from_existing_root_gets_versioned_filename(self):
        old=self.settings.notes_root/"demo.md"
        old_data='---\nrepo: "editorial/demo"\n---\n\n# Historical Capture Note\n'
        old.write_text(old_data,encoding="utf-8")
        # --new-note is an explicit second-note request; it must not overwrite
        # even when an unfinished regular Job is still in the runtime.
        prepared=prepare_job(self.settings,resolve_repository("editorial/demo"),
                             bundle(),publish_mode="new")
        self.assertEqual(prepared["status"],"analysis_required")
        fresh=Path(prepared["job_dir"])
        finish_analysis(fresh)
        result=finalize_job(self.settings,fresh)
        self.assertEqual(result["status"],"note_ready")
        self.assertEqual(Path(result["note_path"]).name,"demo（2）.md")
        self.assertEqual(old.read_text(encoding="utf-8"),old_data)

    def test_root_legacy_managed_note_preserves_user_tail(self):
        from github_learning.note_template import MANAGED_START,MANAGED_END
        old=self.settings.notes_root/"demo.md"
        old.write_text(
            '---\nrepo: "editorial/demo"\n---\n'
            + MANAGED_START + "\n\n# Previous text\n\n" + MANAGED_END
            + "\n## 我的记录\n\n我的真实人工笔记必须保留。\n",
            encoding="utf-8",
        )
        finish_analysis(self.job_dir)
        result=finalize_job(self.settings,self.job_dir)
        self.assertEqual(result["status"],"note_target_changed")
        self.assertIn("我的真实人工笔记必须保留。",old.read_text(encoding="utf-8"))
        self.assertFalse((self.settings.notes_root/"00-待整理"/"demo.md").exists())


if __name__=="__main__":
    unittest.main()
