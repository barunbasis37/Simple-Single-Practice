#!/usr/bin/env python3
"""Deterministic, no-LLM checks against a unified diff.

Covers the pattern-matchable subset of docs/pr-bot/01-review-logic.md:
hardcoded secrets and unsafe-permission-style patterns (category 3), missing
tests for non-trivial changed files (category 2), and debug/TODO noise
(category 4). Kept dependency-free (stdlib only) so it runs in CI with no
install step and can be unit tested in isolation from the OpenAI call.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    category: str  # "security" | "test-coverage" | "style"
    severity: str  # "blocking" | "note"
    file: str
    message: str


SECRET_PATTERNS = [
    (
        re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\'][^"\']{8,}["\']'),
        "possible hardcoded credential",
    ),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "possible AWS access key ID"),
    (re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"), "embedded private key"),
]

DEBUG_PATTERNS = [
    re.compile(r"\bconsole\.log\("),
    re.compile(r"\bdebugger;"),
    re.compile(r"^\s*print\("),
]

TODO_PATTERN = re.compile(r"(TODO|FIXME)(?!.*#\d+)", re.IGNORECASE)

TEST_HINT = re.compile(r"(test|spec)", re.IGNORECASE)
TRIVIAL_HINT = re.compile(
    r"(models?/|dto|migrations?/|\.md$|\.json$|\.ya?ml$|\.csproj$|\.gitignore$)",
    re.IGNORECASE,
)

_CATEGORY_ORDER = {"security": 0, "test-coverage": 1, "style": 2}


def parse_diff(diff_text: str) -> dict[str, list[str]]:
    """Map each changed file path to the list of lines it gained (added-only)."""
    files: dict[str, list[str]] = {}
    current_file: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].split("\t")[0].strip()
            if path.startswith("b/"):
                path = path[2:]
            current_file = None if path == "/dev/null" else path
            if current_file is not None:
                files.setdefault(current_file, [])
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file is not None:
                files[current_file].append(line[1:])
    return files


def find_secrets(files: dict[str, list[str]]) -> list[Finding]:
    findings = []
    for path, lines in files.items():
        for line in lines:
            for pattern, desc in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding("security", "blocking", path, f"{desc}: `{line.strip()[:120]}`")
                    )
    return findings


def find_debug_statements(files: dict[str, list[str]]) -> list[Finding]:
    findings = []
    for path, lines in files.items():
        if TEST_HINT.search(path):
            continue
        for line in lines:
            if any(pattern.search(line) for pattern in DEBUG_PATTERNS):
                findings.append(
                    Finding("style", "note", path, f"leftover debug statement: `{line.strip()[:120]}`")
                )
    return findings


def find_todo_without_reference(files: dict[str, list[str]]) -> list[Finding]:
    findings = []
    for path, lines in files.items():
        for line in lines:
            if TODO_PATTERN.search(line):
                findings.append(
                    Finding("style", "note", path, f"TODO/FIXME without an issue reference: `{line.strip()[:120]}`")
                )
    return findings


def find_missing_tests(files: dict[str, list[str]]) -> list[Finding]:
    changed_paths = list(files.keys())
    test_paths = [p for p in changed_paths if TEST_HINT.search(p)]
    findings = []
    for path in changed_paths:
        if TEST_HINT.search(path) or TRIVIAL_HINT.search(path):
            continue
        stem = re.split(r"[\\/]", path)[-1].rsplit(".", 1)[0]
        has_matching_test = any(stem.lower() in t.lower() for t in test_paths)
        if not has_matching_test:
            findings.append(
                Finding(
                    "test-coverage",
                    "blocking",
                    path,
                    "changed source file has no corresponding changed test file",
                )
            )
    return findings


def run_all_checks(diff_text: str) -> list[Finding]:
    files = parse_diff(diff_text)
    findings: list[Finding] = []
    findings += find_secrets(files)
    findings += find_debug_statements(files)
    findings += find_todo_without_reference(files)
    findings += find_missing_tests(files)
    return findings


def format_findings_markdown(findings: list[Finding]) -> str:
    if not findings:
        return "No static-check findings."
    lines = ["### Static check findings"]
    for f in sorted(findings, key=lambda f: _CATEGORY_ORDER.get(f.category, 99)):
        tag = "BLOCKING" if f.severity == "blocking" else "note"
        lines.append(f"- [{tag}] ({f.category}) `{f.file}` — {f.message}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_findings_markdown(run_all_checks(sys.stdin.read())))
