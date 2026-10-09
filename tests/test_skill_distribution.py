"""Portable stdlib Skill policy/ZIP distribution contract tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.lifecycle import EDITORIAL_CONTRACT_VERSION, CURRENT_JOB_VERSION

SPEC = importlib.util.spec_from_file_location("build_skill",ROOT/"scripts"/"build_agent_skill_packages.py")
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class SkillDistributionTests(unittest.TestCase):
    def test_reference_resources_and_contract(self):
        package=build.package_files()
        self.assertEqual(len(package),5)
        policy=json.loads(package["references/contract.json"].decode("utf-8"))
        self.assertEqual(policy["editorial_contract_version"],EDITORIAL_CONTRACT_VERSION)
        self.assertEqual(CURRENT_JOB_VERSION,8)
        self.assertEqual(policy["new_job_version"],CURRENT_JOB_VERSION)
        self.assertEqual(policy["css_extension_version"],"0.4")
        for name,source in build.REFERENCE_INPUTS.items():
            actual=source.read_bytes()
            self.assertEqual(package["references/"+name],actual)
            self.assertEqual(policy["references"][name],hashlib.sha256(actual).hexdigest())
        self.assertIn(b"gh-source",package["references/ODS-V2.2-GOLDEN.md"])
        self.assertIn("Mandatory contract",package["SKILL.md"].decode("utf-8"))

    def test_generated_host_copies_match_canonical(self):
        self.assertEqual(build.check(),0)
        for path,content in build.expected_files().items():
            self.assertTrue(path.is_file(),str(path))
            self.assertEqual(path.read_bytes(),content)

    def test_self_contained_zip_has_all_and_only_required_files(self):
        with zipfile.ZipFile(build.ZIP_PATH) as archive:
            self.assertIsNone(archive.testzip())
            expected={"github-note/"+name for name in build.package_files()}
            self.assertEqual(set(archive.namelist()),expected)
            for name,contents in build.package_files().items():
                self.assertEqual(archive.read("github-note/"+name),contents)
        self.assertEqual(build.ZIP_PATH.read_bytes(),build.expected_zip_bytes())


if __name__=="__main__":
    unittest.main()
