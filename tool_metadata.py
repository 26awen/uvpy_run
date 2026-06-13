import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime


SOURCE_PREVIEW_LINES = 120


@dataclass
class DocSection:
    title: str
    lines: list[str]


@dataclass
class ToolMetadata:
    filename: str
    title: str
    description: str
    overview: str
    doc_sections: list[DocSection]
    version: str
    category: str
    author: str
    requires_python: str
    dependencies: list[str]
    usage_examples: list[str]
    remote_usage_examples: list[str]
    full_docstring: str
    source_lines: int
    updated_at: str
    source_preview: str
    source_preview_truncated: bool

    def to_dict(self):
        return asdict(self)


def parse_tool_metadata(file_path):
    """Parse display metadata from a public Python tool file."""
    filename = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        source_lines = content.splitlines()
        lines = content.split("\n")
        docstring_lines = extract_module_docstring_lines(lines)
        requires_python, dependencies = parse_pep723_metadata(lines)
        title, description, full_docstring, overview, sections, usage_examples = (
            parse_docstring_metadata(filename, docstring_lines)
        )

        return ToolMetadata(
            filename=filename,
            title=title,
            description=description,
            overview=overview,
            doc_sections=sections,
            version=parse_docstring_field(docstring_lines, "Version") or "N/A",
            category=parse_docstring_field(docstring_lines, "Category") or "N/A",
            author=parse_docstring_field(docstring_lines, "Author") or "N/A",
            requires_python=requires_python,
            dependencies=dependencies,
            usage_examples=usage_examples,
            remote_usage_examples=[],
            full_docstring=full_docstring,
            source_lines=len(source_lines),
            updated_at=datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
                "%Y-%m-%d"
            ),
            source_preview="\n".join(source_lines[:SOURCE_PREVIEW_LINES]),
            source_preview_truncated=len(source_lines) > SOURCE_PREVIEW_LINES,
        )
    except Exception as error:
        return fallback_metadata(filename, f"Error reading file: {error}")


def fallback_metadata(filename, full_docstring=""):
    return ToolMetadata(
        filename=filename,
        title=f"Python Script: {filename}",
        description=f"Python utility script: {filename}",
        overview="",
        doc_sections=[],
        version="N/A",
        category="N/A",
        author="N/A",
        requires_python="N/A",
        dependencies=[],
        usage_examples=[],
        remote_usage_examples=[],
        full_docstring=full_docstring,
        source_lines=0,
        updated_at="N/A",
        source_preview="",
        source_preview_truncated=False,
    )


def parse_pep723_metadata(lines):
    requires_python = "N/A"
    dependencies = []
    in_script_block = False
    in_dependencies = False

    for line in lines:
        stripped = line.strip()

        if stripped == "# /// script":
            in_script_block = True
            continue
        if stripped == "# ///":
            in_script_block = False
            in_dependencies = False
            break
        if not in_script_block:
            continue

        if stripped.startswith("# requires-python ="):
            requires_python_match = re.search(r'"([^"]*)"', stripped)
            if requires_python_match:
                requires_python = requires_python_match.group(1)

        if stripped.startswith("# dependencies = ["):
            in_dependencies = True
            deps_content = stripped[len("# dependencies = [") :]
            dependencies.extend(re.findall(r'"([^"]*)"', deps_content))
            if stripped.endswith("]"):
                in_dependencies = False
            continue

        if in_dependencies:
            dependencies.extend(re.findall(r'"([^"]*)"', stripped))
            if stripped.endswith("]"):
                in_dependencies = False

    return requires_python, dependencies


def extract_module_docstring_lines(lines):
    in_docstring = False
    docstring_lines = []

    for line in lines:
        stripped = line.strip()

        if '"""' in stripped and not in_docstring:
            in_docstring = True
            if stripped.count('"""') == 2:
                docstring_content = stripped.split('"""')[1].strip()
                if docstring_content:
                    docstring_lines.append(docstring_content)
                break

            after_quotes = stripped.split('"""', 1)[1].strip()
            if after_quotes:
                docstring_lines.append(after_quotes)
            continue

        if in_docstring:
            if '"""' in stripped:
                before_quotes = stripped.split('"""')[0].strip()
                if before_quotes:
                    docstring_lines.append(before_quotes)
                break
            if stripped:
                docstring_lines.append(stripped)

    return docstring_lines


def parse_docstring_metadata(filename, docstring_lines):
    if not docstring_lines:
        return (
            f"Python Script: {filename}",
            f"Python utility script: {filename}",
            "",
            "",
            [],
            [],
        )

    title = docstring_lines[0].strip()
    description = title[:100] + ("..." if len(title) > 100 else "")
    full_docstring = "\n".join(docstring_lines)
    overview, sections = parse_docstring_content(docstring_lines)
    usage_examples = parse_usage_examples(docstring_lines, filename)

    return title, description, full_docstring, overview, sections, usage_examples


def parse_docstring_field(docstring_lines, field_name):
    prefix = f"{field_name}:"

    for line in docstring_lines:
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.split(prefix, 1)[1].strip()

    return None


def parse_usage_examples(docstring_lines, filename):
    usage_examples = []
    collecting_examples = False

    for line in docstring_lines:
        stripped = line.strip()

        if stripped.startswith(("Usage Examples:", "Examples:")):
            collecting_examples = True
            continue

        if not collecting_examples:
            continue

        if stripped.startswith(("uv run ", "python ")):
            usage_examples.append(normalize_usage_example(stripped, filename))

    return usage_examples


def normalize_usage_example(example, filename):
    example = re.sub(
        r"uv run [a-zA-Z_][a-zA-Z0-9_]*\.py",
        f"uv run {filename}",
        example,
    )
    return re.sub(
        r"python [a-zA-Z_][a-zA-Z0-9_]*\.py",
        f"uv run {filename}",
        example,
    )


def parse_docstring_content(docstring_lines):
    """Split a module docstring into readable overview text and named sections."""
    overview_lines = []
    sections = []
    current_section = None
    collecting_examples = False

    for index, raw_line in enumerate(docstring_lines):
        line = raw_line.strip()
        if not line:
            continue
        if index == 0:
            continue
        if line.startswith(("Version:", "Category:", "Author:")):
            continue
        if line.startswith(("Usage Examples:", "Examples:")):
            collecting_examples = True
            current_section = None
            continue
        if collecting_examples and line.startswith(("uv run ", "python ")):
            continue
        if collecting_examples and line.endswith(":"):
            collecting_examples = False

        if line.endswith(":"):
            current_section = DocSection(title=line[:-1], lines=[])
            sections.append(current_section)
            continue

        if current_section is not None:
            current_section.lines.append(normalize_doc_list_item(line))
        else:
            overview_lines.append(line)

    sections = [section for section in sections if section.lines]
    return "\n".join(overview_lines).strip(), sections


def normalize_doc_list_item(line):
    """Remove source docstring list markers before rendering as HTML list items."""
    return re.sub(r"^[-*]\s+", "", line)


def build_remote_usage_examples(examples, base_url, filename):
    """Convert local-looking usage examples into copy-ready remote uv commands."""
    command_pattern = re.compile(
        r"^(?:uv run|python)\s+(?:https?://[^\s]+/)?[a-zA-Z_][a-zA-Z0-9_]*\.py\b"
    )

    return [
        command_pattern.sub(f"uv run {base_url}/{filename}", example)
        for example in examples
    ]
