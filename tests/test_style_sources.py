"""Unit tests for CSS source discovery without sibling repository names."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_learning.style_sources import StyleSourceError, resolve_css_source


class TestStyleSources(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="style-source-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.consumer = self.root / "consumer"
        (self.consumer / "config").mkdir(parents=True)
        (self.consumer / "config" / "obsidian-style.json").write_text(json.dumps({
            "schema_version": 1,
            "repository": "https://github.com/ZiYao00/obsidian-learning-snippets",
            "core": "snippets/learning-lab.css",
            "extensions": ["snippets/github-note.css"],
            "cssclasses": ["learning-page", "github-note"],
        }), encoding="utf-8")
        self.provider = self.root / "renamed-styles" / "nested"
        (self.provider / "snippets").mkdir(parents=True)
        self.write_manifest("snippets/github-note.css")
        self.css = self.provider / "snippets" / "github-note.css"
        self.css.write_text("/* extension */", encoding="utf-8")

    def write_manifest(self, extension):
        (self.provider / "manifest.json").write_text(json.dumps({
            "schema_version": 1,
            "repository": "https://github.com/ZiYao00/new-name",
            "core": {"path": "snippets/learning-lab.css"},
            "extensions": [{"path": extension}],
        }), encoding="utf-8")

    def test_explicit_root_and_environment_work_after_rename(self):
        with patch.dict(os.environ, {"OBSIDIAN_STYLES_ROOT": ""}):
            self.assertEqual(resolve_css_source(self.consumer, "github-note.css", styles_root=self.provider), self.css)
            self.assertIsNone(resolve_css_source(self.consumer, "github-note.css", optional=True))
            with self.assertRaisesRegex(StyleSourceError, "not configured"):
                resolve_css_source(self.consumer, "github-note.css")
        with patch.dict(os.environ, {"OBSIDIAN_STYLES_ROOT": str(self.provider)}):
            self.assertEqual(resolve_css_source(self.consumer, "github-note.css"), self.css)

    def test_not_declared_and_unsafe_sources_blocked(self):
        with self.assertRaisesRegex(StyleSourceError, "not declared"):
            resolve_css_source(self.consumer, "x-case-note.css", styles_root=self.provider)
        with self.assertRaisesRegex(StyleSourceError, "not declared"):
            resolve_css_source(self.consumer, "../github-note.css", styles_root=self.provider)
        self.write_manifest("snippets/../github-note.css")
        with self.assertRaisesRegex(StyleSourceError, "not uniquely declared"):
            resolve_css_source(self.consumer, "github-note.css", styles_root=self.provider)


if __name__ == "__main__":
    unittest.main()
