"""Build host-neutral GitHub Note Skills and a self-contained ZIP.

Only skill/github-note/SKILL.md is hand-edited; the two supporting references
are copied from docs/NOTE-SPEC.md and the approved ODS Golden Sample.
Generated copies under skill/, github-note/, agent-skills/ and release/ are
derived data. --check validates content and the actual ZIP payload.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from github_learning.lifecycle import EDITORIAL_CONTRACT_VERSION, CURRENT_JOB_VERSION

SOURCE = PROJECT_ROOT / "skill" / "github-note"
OUTPUTS = [
    PROJECT_ROOT / "github-note",
    PROJECT_ROOT / "agent-skills" / "chatgpt" / "github-note",
    PROJECT_ROOT / "agent-skills" / "codex" / "github-note",
    PROJECT_ROOT / "agent-skills" / "claude" / "github-note",
    PROJECT_ROOT / "agent-skills" / "workbuddy" / "github-note",
]
REFERENCE_INPUTS = {
    "NOTE-SPEC.md": PROJECT_ROOT / "docs" / "NOTE-SPEC.md",
    "ODS-V2.2-GOLDEN.md": PROJECT_ROOT / "docs" / "ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md",
}
ZIP_PATH = PROJECT_ROOT / "release" / "skill.zip"
SKILL_VERSION = "2.2.0"
CSS_VERSION = "0.4"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package_files() -> dict[str, bytes]:
    contents: dict[str, bytes] = {
        "SKILL.md": (SOURCE / "SKILL.md").read_bytes(),
        "agents/openai.yaml": (SOURCE / "agents" / "openai.yaml").read_bytes(),
    }
    for name, path in REFERENCE_INPUTS.items():
        contents["references/" + name] = path.read_bytes()
    policy = {
        "skill_version": SKILL_VERSION,
        "editorial_contract_version": EDITORIAL_CONTRACT_VERSION,
        "new_job_version": CURRENT_JOB_VERSION,
        "css_extension_version": CSS_VERSION,
        "references": {
            name: sha((REFERENCE_INPUTS[name]).read_bytes()) for name in sorted(REFERENCE_INPUTS)
        },
    }
    contents["references/contract.json"] = (
        json.dumps(policy, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return contents


def expected_files() -> dict[Path, bytes]:
    pkg = package_files()
    expected: dict[Path, bytes] = {}
    for name, content in pkg.items():
        # One canonical SKILL text and supporting copies generated for every host.
        expected[SOURCE / name] = content
        for root in OUTPUTS:
            if name == "agents/openai.yaml" and root not in (OUTPUTS[0], OUTPUTS[1]):
                continue
            expected[root / name] = content
    return expected


def expected_zip_bytes() -> bytes:
    files = package_files()
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            member = zipfile.ZipInfo("github-note/" + name, (2026, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o644 << 16
            member.flag_bits |= 0x800
            archive.writestr(member, data)
    return target.getvalue()


def check() -> int:
    drift = []
    for path, content in expected_files().items():
        if not path.is_file() or path.read_bytes() != content:
            drift.append(str(path.relative_to(PROJECT_ROOT)))
    packaged = expected_zip_bytes()
    if not ZIP_PATH.is_file() or ZIP_PATH.read_bytes() != packaged:
        drift.append(str(ZIP_PATH.relative_to(PROJECT_ROOT)))
    else:
        with zipfile.ZipFile(ZIP_PATH) as archive:
            if archive.testzip() is not None:
                drift.append("ZIP CRC mismatch")
            actual = set(archive.namelist())
            required = {"github-note/" + name for name in package_files()}
            if actual != required:
                drift.append("ZIP entries differ from required Skill resources")
    if drift:
        print("Skill resources or the distributable ZIP are out of date:")
        for item in drift:
            print("- " + item)
        return 1
    print(f"GitHub Note Skill v{SKILL_VERSION} validated: {len(OUTPUTS)} hosts, "
          f"{len(package_files())} resources, ZIP sha256={sha(packaged)}")
    return 0


def build() -> int:
    for path, content in expected_files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = expected_zip_bytes()
    ZIP_PATH.write_bytes(payload)
    print(f"Generated Skill v{SKILL_VERSION}, editorial V{EDITORIAL_CONTRACT_VERSION}:")
    for output in OUTPUTS:
        print("- " + str(output.relative_to(PROJECT_ROOT)))
    print("- " + str(ZIP_PATH.relative_to(PROJECT_ROOT)))
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize and validate portable GitHub Note Skill distributions.")
    parser.add_argument("--check", action="store_true", help="Read-only comparison, including actual ZIP bytes and entries.")
    args = parser.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
