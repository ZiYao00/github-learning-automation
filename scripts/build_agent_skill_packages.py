from __future__ import annotations

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "skill" / "github-note"
OUTPUTS = [
    PROJECT_ROOT / "github-note",
    PROJECT_ROOT / "agent-skills" / "chatgpt" / "github-note",
    PROJECT_ROOT / "agent-skills" / "codex" / "github-note",
    PROJECT_ROOT / "agent-skills" / "claude" / "github-note",
    PROJECT_ROOT / "agent-skills" / "workbuddy" / "github-note",
]


def expected_files() -> dict[Path, bytes]:
    skill = (SOURCE / "SKILL.md").read_bytes()
    openai = (SOURCE / "agents" / "openai.yaml").read_bytes()
    expected: dict[Path, bytes] = {}
    for root in OUTPUTS:
        expected[root / "SKILL.md"] = skill
    expected[OUTPUTS[0] / "agents" / "openai.yaml"] = openai
    expected[OUTPUTS[1] / "agents" / "openai.yaml"] = openai
    return expected


def check() -> int:
    drift = []
    for path, content in expected_files().items():
        if not path.is_file() or path.read_bytes() != content:
            drift.append(path.relative_to(PROJECT_ROOT))
    if drift:
        print("Agent Skill packages are out of date:")
        for path in drift:
            print(f"- {path}")
        return 1
    print("Agent Skill packages are synchronized.")
    return 0


def build() -> int:
    for path, content in expected_files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print("Generated Agent Skill packages:")
    for root in OUTPUTS:
        print(f"- {root.relative_to(PROJECT_ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build generated github-note Agent Skill packages.")
    parser.add_argument("--check", action="store_true", help="Check generated packages without writing.")
    args = parser.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
