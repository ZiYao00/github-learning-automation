"""Source authenticity: verify Git blob bytes before decoding or truncation."""
from __future__ import annotations
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from github_learning.github_client import _fetch_planned_text,_git_blob_sha,GitHubFetchError


class GitBlobVerificationTests(unittest.TestCase):
    def test_valid_utf8_source_and_sha(self):
        data="# sample\n视频提示词中文".encode("utf-8")
        with patch("github_learning.github_client._request_raw_bytes",return_value=data):
            obj, warning=_fetch_planned_text("x/y","f"*40,"PROMPT.md",None,
                             kind="prompt_document",sha=_git_blob_sha(data),size=len(data))
        self.assertIsNone(warning)
        self.assertEqual(obj.content,data.decode("utf-8"))
        self.assertEqual(obj.sha,_git_blob_sha(data))

    def test_declared_sha_mismatch_is_fatal(self):
        data=b"tampered"
        with patch("github_learning.github_client._request_raw_bytes",return_value=data):
            with self.assertRaises(GitHubFetchError) as error:
                _fetch_planned_text("x/y","f"*40,"PROMPT.md",None,
                                    kind="prompt_document",sha="a"*40,size=len(data))
        self.assertEqual(error.exception.code,"source_blob_mismatch")

    def test_declared_size_mismatch_is_fatal(self):
        data=b"hello"
        with patch("github_learning.github_client._request_raw_bytes",return_value=data):
            with self.assertRaisesRegex(GitHubFetchError,"不匹配"):
                _fetch_planned_text("x/y","f"*40,"PROMPT.md",None,
                                    kind="prompt_document",sha=_git_blob_sha(data),size=99)

    def test_non_utf8_source_fails_closed(self):
        data=b"hi\xff"
        with patch("github_learning.github_client._request_raw_bytes",return_value=data):
            with self.assertRaises(GitHubFetchError) as error:
                _fetch_planned_text("x/y","f"*40,"PROMPT.md",None,
                                    kind="prompt_document",sha=_git_blob_sha(data),size=len(data))
        self.assertEqual(error.exception.code,"source_encoding_invalid")

if __name__=="__main__":
    unittest.main()
