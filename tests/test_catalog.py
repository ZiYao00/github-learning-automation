"""Offline catalog regression. All writes stay in TemporaryDirectory."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

# Keep stdlib unittest discovery runnable without installing the project.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from github_learning.catalog import (  # noqa: E402
    CATALOG_NAME,
    DEFAULT_CATALOG,
    NAV_NAME,
    CatalogDocument,
    CatalogError,
    add_catalog,
    normalize_repository,
    read_document,
    sha256,
    table_cells,
)
from github_learning.catalog_nav import inspect_catalog, navigation, note_link, scan_notes  # noqa: E402
from github_learning.config import Settings  # noqa: E402
from github_learning.note_template import MANAGED_END, MANAGED_START  # noqa: E402


def sample_catalog(count: int = 34, *, crlf: bool = False, bom: bool = False) -> bytes:
    featured = "# 收藏\n\n## 重点推荐\n\n### 六个优先\n\n| 顺序 | 项目 | 原因 |\n| --- | --- | --- |\n"
    featured += "".join(f"| {i} | [项目](https://github.com/example/r{i}) | 人工推荐 |\n" for i in range(6))
    featured += "\n### 四个备选\n\n| 项目 | 说明 |\n| --- | --- |\n"
    featured += "".join(f"| [项目](https://github.com/example/r{i}) | 保留 |\n" for i in range(6, 10))
    featured += "\n"
    body = DEFAULT_CATALOG.decode("utf-8").split("## 收藏列表", 1)[1]
    text = featured + "## 收藏列表" + body
    doc = CatalogDocument.parse(text.encode("utf-8"))
    additions = [[f"[r{i}](https://github.com/example/r{i}) · `example/r{i}`", f"人工原因 {i}",
                  "高" if i % 2 else "中", "待归档", "—"] for i in range(count)]
    data = doc.updated(additions=additions)
    if crlf:
        data = data.replace(b"\n", b"\r\n")
    return (b"\xef\xbb\xbf" if bom else b"") + data


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="github-catalog-test-")
        self.base = Path(self.tmp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.vault = self.base / "vault"
        (self.vault / ".obsidian").mkdir(parents=True)
        self.notes = self.vault / "GitHub-Note"
        self.notes.mkdir()
        self.settings = Settings(self.project, self.notes, self.project / ".runtime", self.project / "local.json",
                                 False, self.vault, Path("GitHub-Note"), research_root=self.project / "research")
        self.catalog = self.notes / CATALOG_NAME
        self.catalog.write_bytes(sample_catalog())
        self.addCleanup(self.tmp.cleanup)

    def note(self, repo: str, *, state: str = "sufficient", name: str | None = None,
             legacy: bool = False, preview: bool = False, packet: str | None = None) -> Path:
        revision = "a" * 40
        meta = {"repo": repo, "source": f"https://github.com/{repo}", "revision": revision,
                "packet_id": packet or f"{repo}@{revision}", "capture_status": "saved", "analysis_status": state}
        if legacy:
            meta.pop("analysis_status")
        if preview:
            meta.pop("repo")
        text = "---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in meta.items()) + "\n---\n\n"
        text += MANAGED_START + "\n# 已保存笔记\n\n来源充分的正文。\n" + MANAGED_END + "\n\n## 我的记录\n\n人工内容。\n"
        path = self.notes / (name or f"00-待整理/{repo.split('/')[-1]}.md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def set_state(self, repo: str, state: str) -> None:
        doc, _ = read_document(self.settings)
        self.catalog.write_bytes(doc.updated({repo.casefold(): {3: state}}))

    def test_34_rows_do_not_include_ten_recommendations(self) -> None:
        raw = self.catalog.read_bytes()
        doc = CatalogDocument.parse(raw)
        self.assertEqual(len(doc.rows), 34)
        self.assertEqual(len({r.key for r in doc.rows}), 34)
        self.assertEqual(doc.updated(), raw)
        self.assertEqual(doc.outside_table[0].count(b"https://github.com"), 10)

    def test_bom_crlf_and_outside_bytes_are_preserved(self) -> None:
        raw = sample_catalog(crlf=True, bom=True)
        doc = CatalogDocument.parse(raw)
        updated = doc.updated({"example/r0": {3: "已归档", 4: r"[[GitHub-Note/中文\|查看笔记]]"}})
        after = CatalogDocument.parse(updated)
        self.assertEqual(doc.outside_table, after.outside_table)
        self.assertEqual(doc.rows[0].cells[:3], after.rows[0].cells[:3])
        self.assertTrue(updated.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))

    def test_headers_unknown_lines_and_broken_columns_fail_closed(self) -> None:
        raw = self.catalog.read_bytes()
        for bad in [raw.replace("优先级 | 状态".encode(), "状态 | 优先级".encode()),
                    raw.replace("人工原因 0".encode(), b"bad | column"),
                    raw.replace("## 状态说明".encode(), "额外主表说明\n## 状态说明".encode())]:
            with self.subTest(bad=bad[:20]), self.assertRaises(CatalogError):
                CatalogDocument.parse(bad)

    def test_escaped_pipe_is_one_cell_but_even_backslash_is_not(self) -> None:
        cells, _ = table_cells(r"| a | A\|B | 高 | 待归档 | [[路径\|名称]] |", 1)
        self.assertEqual(len(cells), 5)
        with self.assertRaises(CatalogError):
            table_cells(r"| a | A\\|B | 高 | 待归档 | — |", 1)

    def test_duplicate_and_conflicting_repo_labels_are_rejected(self) -> None:
        raw = self.catalog.read_bytes()
        for bad in [raw.replace(b"example/r1", b"example/r0"),
                    raw.replace(b"`example/r0`", b"`other/repo`")]:
            with self.assertRaises(CatalogError):
                CatalogDocument.parse(bad)

    def test_only_status_and_link_are_programmatically_mutable(self) -> None:
        doc = CatalogDocument.parse(self.catalog.read_bytes())
        for changes in [{"example/r0": {1: "rewrite"}}, {"none/repo": {3: "已归档"}}]:
            with self.assertRaises(CatalogError):
                doc.updated(changes)

    def test_url_and_bare_identity_variants(self) -> None:
        for value in ["example/repo.git", "https://github.com/example/repo.git", "https://github.com/example/repo/tree/main",
                      "http://github.com/example/repo?tab=readme-ov-file"]:
            self.assertEqual(normalize_repository(value).full_name, "example/repo")

    def test_invalid_or_ambiguous_identity_is_not_invented(self) -> None:
        for value in ["JustProject", "https://github.com.evil.test/a/b", "https://user@github.com/a/b",
                      "https://github.com:443/a/b", "https://github.com/a", "https://github.com/a/../b",
                      "https://github.com/a/%2e%2e/b", "https://github.com/settings/profile", "../repo"]:
            with self.subTest(value=value), self.assertRaises(CatalogError):
                normalize_repository(value)

    def test_bulk_deduplicates_without_collector_or_metadata_overwrite(self) -> None:
        before = CatalogDocument.parse(self.catalog.read_bytes())
        with patch("github_learning.github_client.fetch_repository_sources", side_effect=AssertionError("network forbidden")):
            result = add_catalog(self.settings, ["example/r0", "EXAMPLE/R0.git",
                                                "看看 https://github.com/new/one 和 https://github.com/new/two/tree/main"])
        after = CatalogDocument.parse(self.catalog.read_bytes())
        self.assertEqual(result["added"], 2)
        self.assertEqual(len(after.rows), 36)
        self.assertEqual(before.rows, after.rows[:34])
        self.assertEqual(before.outside_table, after.outside_table)
        raw = self.catalog.read_bytes()
        self.assertEqual(add_catalog(self.settings, ["new/one", "NEW/two"])["status"], "no_change")
        self.assertEqual(raw, self.catalog.read_bytes())

    def test_partial_input_reports_each_result(self) -> None:
        result = add_catalog(self.settings, ["only-a-name", "valid/repo"])
        self.assertEqual(result["status"], "catalog_partial")
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["results"][0]["status"], "needs_verification")
        self.assertEqual(result["results"][1]["public_status"], "not_checked")

    def test_description_escapes_markdown_html_and_newline(self) -> None:
        add_catalog(self.settings, [{"repository": "new/repo", "description": "A|B\n[[注入]] <script>x</script> <% script %> ![图片](bad)",
                                     "priority": "高", "source": "来自帖子"}])
        doc = CatalogDocument.parse(self.catalog.read_bytes())
        self.assertEqual(len(doc.rows), 35)
        cell = doc.rows[-1].cells[1]
        self.assertIn(r"A\|B", cell)
        self.assertNotIn("<script>", cell)
        self.assertNotIn("[[注入]]", cell)
        self.assertIn("来自帖子", cell)

    def test_add_dry_run_has_no_writes_or_locks(self) -> None:
        before = {p.relative_to(self.notes): p.read_bytes() for p in self.notes.rglob('*') if p.is_file()}
        result = add_catalog(self.settings, ["new/repo"], dry_run=True)
        self.assertIn("+|", result["diff"])
        after = {p.relative_to(self.notes): p.read_bytes() for p in self.notes.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse((self.notes / ".github-catalog").exists())

    def test_sha_conflict_does_not_overwrite(self) -> None:
        digest = sha256(self.catalog.read_bytes())
        self.catalog.write_bytes(self.catalog.read_bytes() + b"\nmanual tail\n")
        current = self.catalog.read_bytes()
        with self.assertRaises(CatalogError):
            add_catalog(self.settings, ["new/repo"], expected_sha=digest)
        self.assertEqual(self.catalog.read_bytes(), current)

    def test_new_catalog_requires_explicit_add_and_no_vault_or_auth(self) -> None:
        root = self.base / "standalone"
        root.mkdir()
        settings = replace(self.settings, notes_root=root, vault_root=None, notes_subdir=None)
        result = add_catalog(settings, ["new/repo"])
        self.assertEqual(result["added"], 1)
        self.assertEqual(len(CatalogDocument.parse((root / CATALOG_NAME).read_bytes()).rows), 1)
        with self.assertRaises(CatalogError):
            navigation(settings)

    def test_navigation_distinguishes_full_minimal_legacy_preview(self) -> None:
        self.note("example/r0")
        self.note("example/r1", state="insufficient")
        self.note("example/r2", legacy=True)
        self.note("example/r3", preview=True)
        raw = self.catalog.read_bytes()
        result = navigation(self.settings, dry_run=True)
        self.assertEqual(result["counts"]["catalog_sufficient"], 1)
        self.assertEqual(result["counts"]["catalog_minimal"], 1)
        self.assertEqual(result["counts"]["ignored_nonformal"], 1)
        self.assertEqual(result["preview"].count("- [x]"), 1)
        self.assertIn("历史笔记（待核验）", result["preview"])
        self.assertFalse((self.notes / NAV_NAME).exists())
        self.assertEqual(raw, self.catalog.read_bytes())

    def test_category_navigation_groups_skills_and_keeps_new_repos_visible(self) -> None:
        config = self.project / "config"
        config.mkdir()
        (config / "catalog-taxonomy.json").write_text(json.dumps({
            "schema_version": 1,
            "categories": ["Agent", "Video"],
            "repositories": {
                "example/r0": {"category": "Agent", "kind": "Skill"},
                "example/r1": {"category": "Video", "kind": "Skill+工具"},
            },
        }), encoding="utf-8")
        result = navigation(self.settings, dry_run=True)
        rendered = result["preview"]
        self.assertIn("**Skill（1）**", rendered)
        self.assertIn("**Skill + 工具（1）**", rendered)
        self.assertIn("### Agent（1）", rendered)
        self.assertIn("### Video（1）", rendered)
        self.assertIn("### 其他 / 待分类（32）", rendered)
        self.assertFalse((self.notes / NAV_NAME).exists())

    def test_invalid_category_mapping_fails_before_navigation_write(self) -> None:
        config = self.project / "config"
        config.mkdir()
        (config / "catalog-taxonomy.json").write_text(json.dumps({
            "schema_version": 1,
            "categories": ["Agent"],
            "repositories": {"example/r0": {"category": "Agent", "kind": "unknown"}},
        }), encoding="utf-8")
        with self.assertRaises(CatalogError) as ctx:
            navigation(self.settings)
        self.assertEqual(ctx.exception.code, "catalog_taxonomy_invalid")
        self.assertFalse((self.notes / NAV_NAME).exists())

    def test_duplicate_notes_block_completion_and_links(self) -> None:
        self.note("example/r0")
        self.note("example/r0", name="另一个名字.md", legacy=True)
        entry = inspect_catalog(self.settings)["entries"][0]
        self.assertFalse(entry["complete"])
        self.assertIsNone(entry["note_link"])
        self.assertEqual(entry["archive_state"], "conflict")

    def test_mismatched_packet_is_never_complete(self) -> None:
        self.note("example/r0", packet="wrong/repo@" + "a" * 40)
        entry = inspect_catalog(self.settings)["entries"][0]
        self.assertEqual(entry["archive_state"], "legacy")
        self.assertFalse(entry["complete"])

    def test_duplicate_frontmatter_is_never_complete(self) -> None:
        path = self.note("example/r0")
        text = path.read_text(encoding="utf-8").replace('analysis_status: "sufficient"', 'analysis_status: "sufficient"\nanalysis_status: "insufficient"')
        path.write_text(text, encoding="utf-8")
        self.assertFalse(inspect_catalog(self.settings)["entries"][0]["complete"])

    def test_human_defer_and_tested_statuses_are_not_downgraded(self) -> None:
        self.set_state("example/r0", "暂缓")
        self.set_state("example/r1", "已实测")
        self.note("example/r0")
        self.note("example/r1")
        result = inspect_catalog(self.settings)
        self.assertEqual(result["entries"][0]["proposed_status"], "暂缓")
        self.assertEqual(result["entries"][1]["proposed_status"], "已实测")
        self.assertNotIn(3, result["changes"].get("example/r0", {}))
        self.assertNotIn(3, result["changes"].get("example/r1", {}))

    def test_claimed_archive_without_note_is_an_anomaly_not_a_success(self) -> None:
        self.set_state("example/r0", "已归档")
        result = inspect_catalog(self.settings)
        self.assertFalse(result["entries"][0]["complete"])
        self.assertEqual(result["entries"][0]["proposed_status"], "已归档")
        self.assertEqual(result["entries"][0]["diagnostics"][0]["code"], "catalog_status_conflict")
        self.assertNotIn("example/r0", result["changes"])

    def test_table_links_are_vault_relative_and_escaped(self) -> None:
        path = self.note("example/r0", name="00-待整理/中文文件.md")
        self.assertEqual(note_link(self.settings, path, table=True), r"[[GitHub-Note/00-待整理/中文文件\|查看笔记]]")
        self.assertEqual(note_link(self.settings, path), "[[GitHub-Note/00-待整理/中文文件|查看笔记]]")

    def test_reserved_filename_uses_exact_encoded_native_link(self) -> None:
        path = self.note("example/r0", name="00-待整理/[中文]#标题.md")
        link = note_link(self.settings, path, table=True)
        self.assertIn("%5B", link)
        self.assertIn("%23", link)
        relative = unquote(link.split("<./", 1)[1].split(">", 1)[0])
        self.assertEqual((self.notes / relative).resolve(), path.resolve())

    def test_mapping_mismatch_never_publishes_fake_links(self) -> None:
        other = self.vault / "wrong"
        other.mkdir()
        settings = replace(self.settings, notes_subdir=Path("wrong"))
        self.note("example/r0")
        preview = navigation(settings, dry_run=True)
        self.assertFalse(preview["can_write"])
        self.assertIsNone(preview["entries"][0]["note_link"])
        with self.assertRaises(CatalogError):
            navigation(settings)
        self.assertFalse((self.notes / NAV_NAME).exists())

    def test_hybrid_junction_uses_display_prefix(self) -> None:
        display = self.vault / "Display"
        if os.name == "nt":
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(display), str(self.notes)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            display.symlink_to(self.notes, target_is_directory=True)
        settings = replace(self.settings, notes_subdir=Path("Display"))
        path = self.note("example/r0")
        self.assertEqual(note_link(settings, path), "[[Display/00-待整理/r0|查看笔记]]")

    def test_moved_note_is_located_by_identity_not_old_title(self) -> None:
        path = self.note("example/r0")
        destination = self.notes / "改名.md"
        path.rename(destination)
        entry = inspect_catalog(self.settings)["entries"][0]
        self.assertTrue(entry["complete"])
        self.assertIn("改名", entry["note_link"])

    def test_unlisted_notes_are_navigation_only(self) -> None:
        self.note("other/repo")
        raw = self.catalog.read_bytes()
        result = navigation(self.settings)
        self.assertEqual(result["counts"]["unlisted_formal"], 1)
        self.assertEqual(raw, self.catalog.read_bytes())
        self.assertEqual(navigation(self.settings)["status"], "no_change")

    def test_existing_unowned_navigation_is_protected(self) -> None:
        target = self.notes / NAV_NAME
        target.write_text("人工写的导航", encoding="utf-8")
        with self.assertRaises(CatalogError):
            navigation(self.settings)
        self.assertEqual(target.read_text(encoding="utf-8"), "人工写的导航")

    def test_changed_note_snapshot_is_detected(self) -> None:
        path = self.note("example/r0")
        index = scan_notes(self.settings)
        path.write_text(path.read_text(encoding="utf-8") + "人工更新", encoding="utf-8")
        with self.assertRaises(CatalogError):
            index.assert_unchanged()

    def test_new_duplicate_after_scan_is_detected(self) -> None:
        self.note("example/r0")
        index = scan_notes(self.settings)
        self.note("example/r0", name="duplicate.md")
        with self.assertRaises(CatalogError):
            index.assert_unchanged()

    def test_media_and_hidden_reference_markdown_are_excluded(self) -> None:
        self.note("example/r0", name="_repo-data/example/raw.md")
        self.note("example/r0", name=".private/raw.md")
        self.assertFalse(inspect_catalog(self.settings)["entries"][0]["complete"])


if __name__ == "__main__":
    unittest.main()
