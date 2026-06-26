import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from catalog_lint import format_issues, lint_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_PYFILES_ROOT = PROJECT_ROOT / "static_pyfiles"


class CatalogLintTests(unittest.TestCase):
    def test_current_catalog_passes_metadata_lint(self):
        issues = lint_catalog(STATIC_PYFILES_ROOT, check_help=False)

        self.assertEqual(issues, [])

    def test_lint_reports_missing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / "tools"
            tools_dir.mkdir()
            (tools_dir / "bad.py").write_text(
                '"""Bad tool"""\nprint("hello")\n',
                encoding="utf-8",
            )

            issues = lint_catalog(tools_dir, check_help=False)
            output = format_issues(issues)

            self.assertIn("bad.py: missing PEP 723 script block", output)
            self.assertIn("bad.py: missing requires-python", output)
            self.assertIn("bad.py: missing usage examples", output)

    def test_lint_runs_tool_help_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / "tools"
            tools_dir.mkdir()
            (tools_dir / "ok.py").write_text(
                textwrap.dedent(
                    '''
                    # /// script
                    # requires-python = ">=3.12"
                    # dependencies = []
                    # ///

                    """
                    Tiny ok tool

                    Checks the metadata lint happy path.

                    Version: 1.0.0
                    Category: Developer
                    Author: UVPY.RUN

                    Usage Examples:
                        uv run ok.py --help

                    Use It For:
                        - Testing metadata lint behavior
                    """

                    import argparse


                    def main():
                        parser = argparse.ArgumentParser()
                        parser.parse_args()


                    if __name__ == "__main__":
                        main()
                    '''
                ).lstrip(),
                encoding="utf-8",
            )

            issues = lint_catalog(tools_dir, check_help=True)

            self.assertEqual(issues, [])

    def test_lint_rejects_raw_python_usage_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / "tools"
            tools_dir.mkdir()
            (tools_dir / "bad.py").write_text(
                textwrap.dedent(
                    '''
                    # /// script
                    # requires-python = ">=3.12"
                    # dependencies = []
                    # ///

                    """
                    Bad usage tool

                    Shows a bad raw usage example.

                    Version: 1.0.0
                    Category: Developer
                    Author: UVPY.RUN

                    Usage Examples:
                        python bad.py --help

                    Use It For:
                        - Testing metadata lint behavior
                    """

                    import argparse


                    def main():
                        parser = argparse.ArgumentParser()
                        parser.parse_args()


                    if __name__ == "__main__":
                        main()
                    '''
                ).lstrip(),
                encoding="utf-8",
            )

            issues = lint_catalog(tools_dir, check_help=False)
            output = format_issues(issues)

            self.assertIn("bad.py: raw usage example should use uv run", output)
            self.assertIn(
                "bad.py: raw usage example must start with 'uv run bad.py'",
                output,
            )

    def test_lint_command_reports_success(self):
        result = subprocess.run(
            [sys.executable, "catalog_lint.py", "--skip-help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Catalog metadata lint passed:", result.stdout)

    def test_lint_command_returns_nonzero_for_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / "tools"
            tools_dir.mkdir()
            (tools_dir / "bad.py").write_text(
                '"""Bad tool"""\nprint("hello")\n',
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "catalog_lint.py",
                    "--tools-dir",
                    str(tools_dir),
                    "--skip-help",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Catalog metadata lint failed:", result.stderr)
            self.assertIn("bad.py: missing PEP 723 script block", result.stderr)


if __name__ == "__main__":
    unittest.main()
