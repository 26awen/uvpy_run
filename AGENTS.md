# AGENTS.md

This file is the working agreement for coding agents collaborating on uvpy.run.
Read it before making changes.

## Project Intent

uvpy.run is a curated directory of standalone Python tools that users run with
`uv run <url>`.

The product should help users answer four questions quickly:

1. What does this script do?
2. Can I understand and trust it?
3. What command should I copy?
4. Where can I inspect the source?

Do not drift toward a hosted code execution platform unless the user explicitly
chooses that direction. The current product is about publishing, explaining and
serving scripts, not executing arbitrary code on the server.

## Current Architecture

- `main.py` contains the Flask app and route handlers.
- `tool_metadata.py` contains script metadata parsing and command normalization.
- `templates/list_tools.html` renders the tool directory.
- `templates/script_detail.html` renders the detail page.
- `static_pyfiles/` contains the public Python scripts.
- `static/` contains small visual assets.
- `README.md` explains setup, usage and roadmap.

## Working Principles

- Preserve the site's lightweight character.
- Prefer simple Flask/Jinja/Python over adding frontend build tooling.
- Keep the retro terminal-adjacent visual identity, but prioritize readability.
- Make copy-ready commands prominent.
- Make source review and dependency review easy.
- Keep security guidance practical, not alarmist.
- Avoid broad rewrites when a targeted change solves the problem.

## Development Commands

Use uv. Do not install packages globally or mutate dependencies for one-off
checks.

Run the app:

```bash
FLASK_SECRET=dev FLASK_DEBUG=1 uv run flask --app main run --host 127.0.0.1 --port 9999
```

Compile check:

```bash
uv run python -m py_compile main.py tool_metadata.py static_pyfiles/*.py
```

Unit tests:

```bash
uv run python -m unittest discover -s tests
```

Route smoke check:

```bash
uv run python - <<'PY'
import os
import main

client = main.app.test_client()
paths = ["/"] + [
    f"/detail/{name[:-3]}"
    for name in sorted(os.listdir(main.STATIC_PYFILES_ROOT))
    if name.endswith(".py")
]

for path in paths:
    response = client.get(path, headers={"Host": "localhost:9999"})
    print(path, response.status_code, len(response.data))
    if response.status_code != 200:
        raise SystemExit(1)
PY
```

## Verification Expectations

For backend or template changes, run:

- `uv run python -m py_compile main.py tool_metadata.py static_pyfiles/*.py`
- `uv run python -m unittest discover -s tests`
- The route smoke check above.

For UX changes, also inspect at least:

- `/`
- `/detail/passwordgen`
- `/detail/brick`

Check desktop and mobile widths when layout changes. Watch for:

- horizontal overflow,
- clipped command text,
- inaccessible copy buttons,
- repeated list markers from docstring parsing,
- broken source preview,
- missing dependency metadata.

## Deployment Notes

Production deployment details live in `README.md` under `Production Deployment`.
Use that flow for remote updates: fetch first, stop Gunicorn, fast-forward
`main`, restart Gunicorn with the full `/home/wwd/.local/bin/uv` path, then
verify both `127.0.0.1:9999` on the host and `https://uvpy.run/` through the
Cloudflare Tunnel. Never write SSH passwords, tokens or Cloudflare credentials
into repository files.

## Tool Metadata Rules

Scripts should use PEP 723 metadata:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

Scripts should also include a module docstring with:

- title,
- short description,
- `Version:`,
- `Category:`,
- `Author:`,
- `Usage Examples:`,
- at least one named section after the examples, such as `Use It For:`,
  `Output:`, `Safety Notes:` or domain-specific sections like `Game Controls:`.

Usage examples may use local-looking script names such as:

```text
uv run passwordgen.py --help
```

The detail page is responsible for converting these to remote copy-ready
commands using the current base URL.

## UX Direction

The detail page should behave like a script decision page:

- title and summary first,
- primary run command near the top,
- copy feedback visible,
- examples copy-ready,
- metadata and dependencies visible,
- source preview available,
- mobile layout usable without horizontal scrolling.

The homepage should evolve into a discovery page:

- search,
- category filters,
- clear tool cards,
- visible copy/details/source actions.

## Near-Term Roadmap

Priority order:

1. Stabilize current detail page changes.
2. Audit and improve the existing tool catalog end to end, including script
   names, tool functionality, descriptions, usage examples and metadata quality.
3. Add route and metadata parsing tests.
4. Fix missing script 404 behavior.
5. Remove duplicated static route behavior if safe.
6. Improve homepage discovery with search and category filtering.
7. Keep metadata parsing in `tool_metadata.py`.
8. Generate sitemap from real script metadata.

## Change Boundaries

Do not:

- add a frontend framework without explicit user approval,
- add server-side script execution,
- remove the security notice or trust cues,
- rewrite all scripts for style only,
- rename public script URLs casually,
- change deployment assumptions without documenting them.

Prefer:

- small, reviewable patches,
- keeping script URLs stable,
- tests for parser behavior,
- clear docs when introducing conventions,
- preserving user edits in the working tree.

## Collaboration Style

The user is evolving this project interactively with Codex. When the next step is
unclear, propose a concrete path and explain tradeoffs briefly. When the task is
clear, implement and verify.

For roadmap-level work, keep a running distinction between:

- product UX,
- metadata/content quality,
- security/trust,
- engineering hygiene,
- deployment/SEO.
