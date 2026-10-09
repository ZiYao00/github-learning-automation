"""Regression for ordinary repositories with author-maintained reusable Prompts.

A pinned README may link only FAQ/Security while package.json ships separate
CHATGPT_PROMPT.md/CODEX_PROMPT.md and a translated README. This source planner
must not silently miss such substantial documentation.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from github_learning.source_planner import plan_additional_sources, source_selection_warnings


class PromptDocumentSelection(unittest.TestCase):
    def test_generic_original_prompt_and_localized_readme(self):
        paths = [
            "README.md", "README_ZH.md", "package.json",
            "CHATGPT_PROMPT.md", "CODEX_PROMPT.md", "FAQ.md", "SECURITY.md",
            "CHANGELOG.md", "DOMAIN_SETUP.md", "docs/site-guide.md",
        ]
        tree = [
            {"path": name, "type": "blob", "size": 500 if "PROMPT" in name else 900,
             "sha": "a" * 40}
            for name in paths
        ]
        planned = plan_additional_sources(
            tree, readme_path="README.md", readme_content="# Test\n"
            "[FAQ](FAQ.md) [Security](SECURITY.md)",
            manifest_paths={"package.json"}
        )
        selected = {item.path: item for item in planned}
        for name in ("README_ZH.md", "CHATGPT_PROMPT.md", "CODEX_PROMPT.md"):
            self.assertIn(name, selected)
        self.assertNotIn("README.md", selected)
        self.assertNotIn("package.json", selected)
        self.assertEqual(selected["CHATGPT_PROMPT.md"].kind, "prompt_document")
        self.assertEqual(selected["CODEX_PROMPT.md"].kind, "prompt_document")
        self.assertLess(
            selected["CHATGPT_PROMPT.md"].priority,
            selected["CHANGELOG.md"].priority
        )

    def test_bounded_planner_reports_skipped_candidate_paths(self):
        paths = [f"docs/install-guide-{index:02d}.md" for index in range(35)]
        tree = [{"path": p, "type": "blob", "size": 1000,
                 "sha": "d" * 40} for p in paths]
        selected = plan_additional_sources(tree, readme_path="README.md",
                                           readme_content="")
        warnings = source_selection_warnings(
            tree, selected, readme_path="README.md", readme_content=""
        )
        self.assertTrue(warnings)
        self.assertIn("未选路径", warnings[0])
        self.assertIn("Source Planner", warnings[0])

    def test_prompt_name_works_for_other_repositories(self):
        paths = ["docs/creative-prompt.md", "PROMPTS.md", "docs/manual.md"]
        tree = [
            {"path": name, "type": "blob", "size": 300, "sha": "b" * 40}
            for name in paths
        ]
        selected = {x.path for x in plan_additional_sources(
            tree, readme_path="README.md", readme_content=""
        )}
        self.assertIn("docs/creative-prompt.md", selected)
        self.assertIn("PROMPTS.md", selected)

if __name__ == "__main__":
    unittest.main()
