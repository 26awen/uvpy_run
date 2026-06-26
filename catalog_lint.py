import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from tool_metadata import build_remote_usage_examples, parse_tool_metadata


ALLOWED_CATEGORIES = {
    "Developer",
    "File",
    "Game",
    "Image",
    "Network",
    "Security",
    "System",
    "Text",
    "Time",
}


@dataclass(frozen=True)
class LintIssue:
    filename: str
    message: str


def iter_tool_paths(tools_dir):
    return sorted(Path(tools_dir).glob("*.py"))


def lint_catalog(tools_dir="static_pyfiles", base_url="https://uvpy.run", check_help=True):
    tools_path = Path(tools_dir)
    issues = []
    tool_paths = iter_tool_paths(tools_path)

    if not tools_path.exists():
        return [LintIssue(str(tools_path), "tools directory does not exist")]
    if not tool_paths:
        return [LintIssue(str(tools_path), "no Python tools found")]

    for path in tool_paths:
        issues.extend(lint_tool(path, base_url=base_url, check_help=check_help))

    return issues


def lint_tool(path, base_url="https://uvpy.run", check_help=True):
    path = Path(path)
    issues = []
    filename = path.name

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        return [LintIssue(filename, f"could not read file: {error}")]

    module_docstring = parse_module_docstring(content, filename, issues)
    info = parse_tool_metadata(path).to_dict()

    if "# /// script" not in content:
        issues.append(LintIssue(filename, "missing PEP 723 script block"))
    if content.count("# ///") < 2:
        issues.append(LintIssue(filename, "missing PEP 723 closing marker"))

    if module_docstring is None:
        issues.append(LintIssue(filename, "missing module docstring"))
    else:
        required_fields = ("Version:", "Category:", "Author:", "Usage Examples:")
        for field_name in required_fields:
            if field_name not in module_docstring:
                issues.append(LintIssue(filename, f"missing docstring field {field_name}"))
        issues.extend(
            lint_raw_usage_examples(
                filename,
                raw_usage_examples(module_docstring),
            )
        )

    for issue in (
        require_present(info, filename, "requires_python", "missing requires-python"),
        require_present(info, filename, "title", "missing title"),
        require_present(info, filename, "overview", "missing overview"),
        require_present(info, filename, "version", "missing Version"),
        require_present(info, filename, "category", "missing Category"),
        require_present(info, filename, "author", "missing Author"),
    ):
        if issue is not None:
            issues.append(issue)

    if info["title"].startswith("Python Script:"):
        issues.append(LintIssue(filename, "title is still using fallback metadata"))
    if info["category"] != "N/A" and info["category"] not in ALLOWED_CATEGORIES:
        categories = ", ".join(sorted(ALLOWED_CATEGORIES))
        issues.append(
            LintIssue(
                filename,
                f"category {info['category']!r} is not one of: {categories}",
            )
        )
    if not info["doc_sections"]:
        issues.append(LintIssue(filename, "missing at least one named docstring section"))
    if not info["usage_examples"]:
        issues.append(LintIssue(filename, "missing usage examples"))
    if not isinstance(info["dependencies"], list):
        issues.append(LintIssue(filename, "dependencies must parse as a list"))
    else:
        for dependency in info["dependencies"]:
            if not isinstance(dependency, str) or not dependency.strip():
                issues.append(LintIssue(filename, "dependencies must be non-empty strings"))

    issues.extend(lint_usage_examples(filename, info["usage_examples"], base_url))

    if check_help:
        issues.extend(lint_help_command(path))

    return issues


def parse_module_docstring(content, filename, issues):
    try:
        return ast.get_docstring(ast.parse(content))
    except SyntaxError as error:
        issues.append(LintIssue(filename, f"file does not parse as Python: {error}"))
        return None


def require_present(info, filename, key, message):
    value = info.get(key)
    if value in (None, "", "N/A"):
        return LintIssue(filename, message)
    return None


def lint_usage_examples(filename, examples, base_url):
    issues = []
    local_prefix = f"uv run {filename}"
    remote_prefix = f"uv run {base_url.rstrip('/')}/{filename}"

    for example in examples:
        if not example.startswith(local_prefix):
            issues.append(
                LintIssue(
                    filename,
                    f"usage example must start with {local_prefix!r}: {example}",
                )
            )
        if f"python {filename}" in example:
            issues.append(
                LintIssue(filename, f"usage example should use uv run, not python: {example}")
            )

        mentioned_scripts = re.findall(
            r"(?:uv run|python)\s+([a-zA-Z_][a-zA-Z0-9_]*\.py)",
            example,
        )
        if mentioned_scripts != [filename]:
            issues.append(
                LintIssue(
                    filename,
                    f"usage example should mention only {filename}: {example}",
                )
            )

    remote_examples = build_remote_usage_examples(
        examples,
        base_url.rstrip("/"),
        filename,
    )
    for remote_example in remote_examples:
        if not remote_example.startswith(remote_prefix):
            issues.append(
                LintIssue(
                    filename,
                    f"remote example is not copy-ready: {remote_example}",
                )
            )

    return issues


def raw_usage_examples(module_docstring):
    examples = []
    collecting_examples = False

    for raw_line in module_docstring.splitlines():
        line = raw_line.strip()

        if line.startswith(("Usage Examples:", "Examples:")):
            collecting_examples = True
            continue
        if collecting_examples and line.endswith(":"):
            collecting_examples = False
            continue
        if collecting_examples and line.startswith(("uv run ", "python ")):
            examples.append(line)

    return examples


def lint_raw_usage_examples(filename, examples):
    issues = []
    local_prefix = f"uv run {filename}"

    for example in examples:
        if example.startswith("python "):
            issues.append(
                LintIssue(filename, f"raw usage example should use uv run: {example}")
            )
        if not example.startswith(local_prefix):
            issues.append(
                LintIssue(
                    filename,
                    f"raw usage example must start with {local_prefix!r}: {example}",
                )
            )

    return issues


def lint_help_command(path):
    result = subprocess.run(
        [sys.executable, str(path), "--help"],
        cwd=path.parent.parent,
        capture_output=True,
        text=True,
        timeout=20,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return [LintIssue(path.name, f"--help exited with {result.returncode}: {output}")]
    if "usage:" not in output.lower():
        return [LintIssue(path.name, "--help output should include a usage line")]
    return []


def format_issues(issues):
    return "\n".join(f"{issue.filename}: {issue.message}" for issue in issues)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint uvpy.run tool metadata and copy-ready examples."
    )
    parser.add_argument(
        "--tools-dir",
        default="static_pyfiles",
        help="Directory containing public Python tool files.",
    )
    parser.add_argument(
        "--base-url",
        default="https://uvpy.run",
        help="Public base URL used to verify remote examples.",
    )
    parser.add_argument(
        "--skip-help",
        action="store_true",
        help="Skip executing each tool's --help command.",
    )

    args = parser.parse_args(argv)
    issues = lint_catalog(
        tools_dir=args.tools_dir,
        base_url=args.base_url,
        check_help=not args.skip_help,
    )

    if issues:
        print("Catalog metadata lint failed:", file=sys.stderr)
        print(format_issues(issues), file=sys.stderr)
        return 1

    count = len(iter_tool_paths(args.tools_dir))
    print(f"Catalog metadata lint passed: {count} scripts checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
