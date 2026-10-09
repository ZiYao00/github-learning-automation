"""Negative editorial source-fidelity and media-markup checks."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from github_learning.editorial_integrity import validate_media_markup
from github_learning.lifecycle import prepare_job,_validate_analysis
from github_learning.input_resolver import resolve_repository
from test_editorial_contract_v7 import settings,bundle,finish_analysis


class EditorialFidelityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg=settings(Path(self.tmp.name))
        self.prompt="Create an uninterrupted 30-second sequence with consistent lighting."
        self.quote="The archive is local and searchable."
        self.readme="# Demo\n\n"+self.quote+"\n\n"+self.prompt+"\n"
        b=bundle()
        src=replace(b.sources[0],content=self.readme,archive_content=self.readme)
        b=replace(b,readme=self.readme,sources=(src,))
        prepared=prepare_job(self.cfg,resolve_repository("editorial/demo"),b)
        self.jobdir=Path(prepared["job_dir"])
        self.data=finish_analysis(self.jobdir)
        revision=b.revision
        pinned=f"https://github.com/editorial/demo/blob/{revision}/README.md"
        self.body=(
            "本文用于演示通用原文核查，而不是实际部署任何项目。"*12
            +"\n\n"
            +f"> [!gh-source] 固定 README · [Source]({pinned})\n"
            +f"> {self.quote}\n\n"
            +f"这个示例来自 [固定版本 README]({pinned})：\n\n"
            +"~~~prompt\n"+self.prompt+"\n~~~\n\n"
            +"最后应当解释来源、能力和没有经过实际验证的部分。"*8
        )
        self.data["editorial_body"]=self.body

    def test_verified_literal_source_and_copy_prompt_pass(self):
        _validate_analysis(self.jobdir,self.data)

    def test_prompt_single_character_change_rejected(self):
        self.data["editorial_body"]=self.body.replace("consistent lighting","different lighting")
        with self.assertRaisesRegex(ValueError,"Prompt 内容"):
            _validate_analysis(self.jobdir,self.data)

    def test_fake_original_quote_rejected(self):
        self.data["editorial_body"]=self.body.replace(self.quote,"The model is unlimited.")
        with self.assertRaisesRegex(ValueError,"官方引用"):
            _validate_analysis(self.jobdir,self.data)

    def test_missing_pinned_source_link_rejected(self):
        self.data["editorial_body"]=self.body.replace("blob/","tree/")
        with self.assertRaises(ValueError):
            _validate_analysis(self.jobdir,self.data)

    def test_unauthorized_media_forms_rejected(self):
        for markup in ('<img src="https://example.com/pixel.png">',
                       '<video src="https://example.com/a.mp4"></video>',
                       '![Picture][imgref]',
                       '<div onclick="alert(1)">danger</div>'):
            with self.subTest(markup=markup):
                with self.assertRaisesRegex(ValueError,"不允许"):
                    validate_media_markup("Some prose "+markup)

    def test_inert_code_samples_not_banned(self):
        validate_media_markup("Use `<img src=x>` as a literal.\n\n"
                              "~~~prompt\n![reference][img]\n<img src=x>\n~~~\n")


if __name__=="__main__":
    unittest.main()
