import pytest

from github_learning.evidence import EvidenceValidationError, validate_evidence_map


def _manifest():
    return {
        "sources": [
            {"id": "src-001", "coverage_required": True},
            {"id": "src-002", "coverage_required": True},
            {"id": "src-003", "coverage_required": False},
        ]
    }


def test_evidence_map_requires_every_required_source():
    analysis = {
        "evidence_map": [
            {"source_id": "src-001", "status": "represented", "targets": ["summary"], "reason": ""}
        ]
    }

    with pytest.raises(EvidenceValidationError):
        validate_evidence_map(_manifest(), analysis)


def test_evidence_map_allows_explicit_omission_reason():
    analysis = {
        "evidence_map": [
            {"source_id": "src-001", "status": "represented", "targets": ["knowledge_map:01"], "reason": ""},
            {
                "source_id": "src-002",
                "status": "omitted_with_reason",
                "targets": [],
                "reason": "与 src-001 完全重复。",
            },
        ]
    }

    validate_evidence_map(_manifest(), analysis)
