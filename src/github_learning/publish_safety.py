"""Filesystem-only publication safeguards for local multi-agent note workflows.

Repo-scoped OS locks serialize cooperating writers, not external editors.
Content SHA checks are optimistic concurrency guards. No database required.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class PublishSafetyError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_hash(path: Path) -> str | None:
    return sha256(path.read_bytes()) if path.exists() else None


def json_atomic(path: Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


@contextmanager
def repository_lock(runtime_root: Path, full_name: str, timeout: float = 5.0) -> Iterator[None]:
    """Cross-process lock; never delete lock inode to prevent split-brain locking."""
    if "/" not in full_name:
        raise PublishSafetyError("lock_identity_invalid", "锁缺少仓库身份。")
    key = sha256(full_name.casefold().encode("utf-8"))[:32]
    path = runtime_root / ".locks" / (key + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as file:
        file.seek(0, os.SEEK_END)
        if file.tell() == 0:
            file.write(b"\0")
            file.flush()
        file.seek(0)
        acquired = False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (OSError, BlockingIOError):
                time.sleep(0.05)
        if not acquired:
            raise PublishSafetyError("repo_busy", "另一个 Agent 正在发布相同仓库；未执行写入。")
        try:
            yield
        finally:
            file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def publish_bytes(path: Path, data: bytes, *, expected_old_sha: str | None) -> str:
    """Atomic complete-file publication under a repository lock.

    New files use hardlink publish (atomic no-replace). Refresh uses checked
    os.replace; external noncooperating writers still require cooperative editing
    discipline because POSIX/Windows has no atomic hash-conditional rename.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    actual = _file_hash(path)
    if actual != expected_old_sha:
        raise PublishSafetyError("note_target_changed", "目标笔记自授权后已变更或消失，拒绝覆盖。")
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if expected_old_sha is None:
            try:
                os.link(temp, path)
            except FileExistsError as exc:
                raise PublishSafetyError("note_target_appeared", "另一个操作已创建此文件，拒绝覆盖。") from exc
        else:
            if _file_hash(path) != expected_old_sha:
                raise PublishSafetyError("note_target_changed", "目标笔记在写入前发生变化。")
            os.replace(temp, path)
        if _file_hash(path) != sha256(data):
            raise PublishSafetyError("note_write_unverified", "写入后校验失败，请检查文件。")
        return sha256(data)
    finally:
        if temp.exists():
            temp.unlink()
