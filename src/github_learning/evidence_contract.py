"""Stable evidence-set fingerprint used independently from immutable Packet identity.

A collection changes when a verified supplement is added, without changing
owner/repo@revision. The fingerprint never includes machine-specific paths.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable


def evidence_set_id(packet_fingerprint: str, supplements: Iterable[tuple[str, str]] = ()) -> str:
    if not isinstance(packet_fingerprint, str) or len(packet_fingerprint) != 64:
        raise ValueError("Invalid Packet fingerprint")
    records = sorted((str(sid), str(sha)) for sid, sha in supplements)
    if len({sid for sid, _ in records}) != len(records):
        raise ValueError("Duplicate evidence supplement identity")
    data = json.dumps({
        "schema_version": 1,
        "packet_content_fingerprint": packet_fingerprint,
        "supplements": [{"supplement_id": sid, "manifest_sha256": sha} for sid, sha in records],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
