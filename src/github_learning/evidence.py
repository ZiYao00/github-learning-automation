from __future__ import annotations

from typing import Any


class EvidenceValidationError(ValueError):
    pass


_ALLOWED_EVIDENCE_STATUS = {"represented", "omitted_with_reason"}


def _source_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = manifest.get("sources") or []
    return [item for item in sources if isinstance(item, dict)]


def required_source_ids(manifest: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id") or "")
        for item in _source_entries(manifest)
        if bool(item.get("coverage_required")) and str(item.get("id") or "")
    }


def validate_evidence_map(manifest: dict[str, Any], analysis: dict[str, Any]) -> None:
    required = required_source_ids(manifest)
    raw_entries = analysis.get("evidence_map") or []
    if not isinstance(raw_entries, list):
        raise EvidenceValidationError("analysis.evidence_map 必须是数组。")

    seen: set[str] = set()
    for entry in raw_entries:
        if not isinstance(entry, dict):
            raise EvidenceValidationError("evidence_map 每个条目必须是对象。")
        source_id = str(entry.get("source_id") or "").strip()
        if not source_id:
            raise EvidenceValidationError("evidence_map 条目缺少 source_id。")
        if source_id in seen:
            raise EvidenceValidationError(f"evidence_map 重复 source_id：{source_id}")
        seen.add(source_id)

        status = str(entry.get("status") or "").strip()
        if status not in _ALLOWED_EVIDENCE_STATUS:
            raise EvidenceValidationError(
                f"evidence_map {source_id} 的 status 必须是 represented 或 omitted_with_reason。"
            )
        if status == "represented":
            targets = entry.get("targets") or []
            if not isinstance(targets, list) or not any(str(item).strip() for item in targets):
                raise EvidenceValidationError(f"evidence_map {source_id} represented 时必须提供 targets。")
        else:
            reason = str(entry.get("reason") or "").strip()
            if not reason:
                raise EvidenceValidationError(
                    f"evidence_map {source_id} omitted_with_reason 时必须说明 reason。"
                )

    missing = sorted(required - seen)
    if missing:
        raise EvidenceValidationError(
            "以下 coverage_required 来源没有 Evidence Map 归宿：" + ", ".join(missing)
        )


def evidence_targets(analysis: dict[str, Any], source_id: str) -> list[str]:
    for entry in analysis.get("evidence_map") or []:
        if isinstance(entry, dict) and str(entry.get("source_id") or "") == source_id:
            return [str(item).strip() for item in entry.get("targets") or [] if str(item).strip()]
    return []
