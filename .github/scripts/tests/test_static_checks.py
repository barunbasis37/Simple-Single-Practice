"""TDD tests for static_checks.py (Step 7 of the PR-bot assignment).

These tests were written before static_checks.py existed — run them first
to see them fail on import, then implement static_checks.py until they
pass. Run with: python -m unittest discover -s .github/scripts/tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from static_checks import (  # noqa: E402
    Finding,
    find_debug_statements,
    find_missing_tests,
    find_secrets,
    find_todo_without_reference,
    format_findings_markdown,
    parse_diff,
    run_all_checks,
)


def diff(*files: tuple[str, list[str]]) -> str:
    """Build a minimal unified diff with only the header lines the parser needs."""
    chunks = []
    for path, added_lines in files:
        body = "\n".join(f"+{line}" for line in added_lines)
        chunks.append(
            f"diff --git a/{path} b/{path}\n"
            f"--- a/{path}\n"
            f"+++ b/{path}\n"
            f"@@ -0,0 +1,{len(added_lines)} @@\n"
            f"{body}"
        )
    return "\n".join(chunks)


class ParseDiffTests(unittest.TestCase):
    def test_maps_file_to_its_added_lines_only(self):
        text = diff(("a.py", ["x = 1", "y = 2"]))
        files = parse_diff(text)
        self.assertEqual(files["a.py"], ["x = 1", "y = 2"])

    def test_multiple_files_stay_separate(self):
        text = diff(("a.py", ["one"]), ("b.py", ["two"]))
        files = parse_diff(text)
        self.assertEqual(files["a.py"], ["one"])
        self.assertEqual(files["b.py"], ["two"])


class SecretDetectionTests(unittest.TestCase):
    def test_detects_hardcoded_api_key(self):
        text = diff(("app/config.py", ['API_KEY = "sk-test-1234567890abcdef"']))
        findings = find_secrets(parse_diff(text))
        self.assertTrue(any(f.category == "security" for f in findings))
        self.assertTrue(all(f.severity == "blocking" for f in findings))

    def test_detects_aws_access_key_id(self):
        text = diff(("infra/deploy.sh", ["AWS_KEY=AKIAABCDEFGHIJKLMNOP"]))
        findings = find_secrets(parse_diff(text))
        self.assertEqual(1, len(findings))

    def test_does_not_flag_ordinary_code(self):
        text = diff(("app/math.py", ["def add(a, b):", "    return a + b"]))
        findings = find_secrets(parse_diff(text))
        self.assertEqual([], findings)


class DebugStatementTests(unittest.TestCase):
    def test_detects_console_log(self):
        text = diff(("web/app.js", ["console.log('debugging')"]))
        findings = find_debug_statements(parse_diff(text))
        self.assertEqual(1, len(findings))
        self.assertEqual("style", findings[0].category)

    def test_ignores_debug_statements_in_test_files(self):
        text = diff(("web/app.test.js", ["console.log('ok in a test')"]))
        findings = find_debug_statements(parse_diff(text))
        self.assertEqual([], findings)


class TodoDetectionTests(unittest.TestCase):
    def test_flags_todo_without_issue_reference(self):
        text = diff(("a.py", ["# TODO clean this up later"]))
        findings = find_todo_without_reference(parse_diff(text))
        self.assertEqual(1, len(findings))

    def test_allows_todo_with_issue_reference(self):
        text = diff(("a.py", ["# TODO(#123): clean this up later"]))
        findings = find_todo_without_reference(parse_diff(text))
        self.assertEqual([], findings)


class MissingTestDetectionTests(unittest.TestCase):
    def test_flags_new_source_file_with_no_test_change(self):
        text = diff(("Services/Calculator.cs", ["public int Add(int a, int b) => a + b;"]))
        findings = find_missing_tests(parse_diff(text))
        self.assertEqual(1, len(findings))
        self.assertEqual("test-coverage", findings[0].category)

    def test_does_not_flag_when_matching_test_file_changed(self):
        text = diff(
            ("Services/Calculator.cs", ["public int Add(int a, int b) => a + b;"]),
            ("Tests/CalculatorTests.cs", ["Assert.Equal(3, new Calculator().Add(1, 2));"]),
        )
        findings = find_missing_tests(parse_diff(text))
        self.assertEqual([], findings)

    def test_skips_trivial_model_files(self):
        text = diff(("Models/Category.cs", ["public string Name { get; set; }"]))
        findings = find_missing_tests(parse_diff(text))
        self.assertEqual([], findings)

    def test_skips_docs_and_config_files(self):
        text = diff(("README.md", ["Some docs update"]))
        findings = find_missing_tests(parse_diff(text))
        self.assertEqual([], findings)


class KnownBugSamplePrTests(unittest.TestCase):
    """The assignment's own acceptance criterion: the bot must flag a known
    bug in a sample PR. This sample PR bakes in two known issues: a
    hardcoded secret and an untested new source file."""

    def test_flags_known_bug_sample_pr(self):
        sample_pr_diff = diff(
            (
                "Services/PaymentClient.cs",
                [
                    'private const string ApiKey = "sk-live-1234567890abcdef";',
                    "public bool Charge(decimal amount) => amount > 0;",
                ],
            )
        )

        findings = run_all_checks(sample_pr_diff)

        categories = {f.category for f in findings}
        self.assertIn("security", categories)
        self.assertIn("test-coverage", categories)
        self.assertTrue(any(f.severity == "blocking" for f in findings))


class FormatFindingsTests(unittest.TestCase):
    def test_empty_findings_says_so(self):
        self.assertEqual("No static-check findings.", format_findings_markdown([]))

    def test_nonempty_findings_render_as_bullets_grouped_by_severity(self):
        findings = [
            Finding("style", "note", "a.js", "leftover debug statement"),
            Finding("security", "blocking", "b.py", "hardcoded secret"),
        ]
        rendered = format_findings_markdown(findings)
        self.assertIn("BLOCKING", rendered)
        self.assertIn("b.py", rendered)
        self.assertIn("a.js", rendered)
        # Security (blocking) should be listed before style (non-blocking).
        self.assertLess(rendered.index("b.py"), rendered.index("a.js"))


if __name__ == "__main__":
    unittest.main()
