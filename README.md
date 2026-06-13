# uvpy.run

uvpy.run is a small Flask site for publishing standalone Python tools that can
be run directly from a URL with [uv](https://github.com/astral-sh/uv).

The product goal is simple: make it easy to discover a script, understand what
it does, review its source and dependencies, then copy a command like this:

```bash
uv run https://uvpy.run/passwordgen.py
```

Each hosted tool should be a self-contained Python file. Dependencies and Python
version requirements belong in the script itself using
[PEP 723](https://peps.python.org/pep-0723/) inline script metadata.

## Current Shape

- `main.py` is the Flask application.
- `tool_metadata.py` parses script metadata for pages and future automation.
- `static_pyfiles/` contains the published Python tools.
- `templates/` contains the homepage and script detail pages.
- `static/` contains icons and other static assets.
- `robots.txt` and `sitemap.xml` support search indexing.
- Open source repository: <https://github.com/26awen/uvpy_run>.

The app currently serves:

- `/` - tool directory page.
- `/detail/<script_name>` - human-readable detail page for a script.
- `/<script_name>.py` - raw Python script download/execution URL.
- `/robots.txt` and `/sitemap.xml`.

## Quick Start

Install uv if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Run the Flask app locally:

```bash
FLASK_SECRET=dev FLASK_DEBUG=1 uv run flask --app main run --host 127.0.0.1 --port 9999
```

Open:

```text
http://127.0.0.1:9999/
http://127.0.0.1:9999/detail/passwordgen
```

Run a hosted script from the local server:

```bash
uv run http://127.0.0.1:9999/passwordgen.py --help
```

## Verification

Use these checks before handing off changes:

```bash
uv run python -m py_compile main.py tool_metadata.py static_pyfiles/*.py
```

```bash
uv run python -m unittest discover -s tests
```

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

## Tool File Standard

Every script in `static_pyfiles/` should aim to include:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.0.0",
# ]
# ///

"""
Short tool title

One or two paragraphs explaining what the script does.

Version: 1.0.0
Category: Utility
Author: UVPY.RUN

Usage Examples:
    uv run tool_name.py --help
    uv run tool_name.py example-argument
"""
```

Preferred script behavior:

- Provide `--help` through `argparse`, `click`, or another CLI library.
- Keep side effects explicit and documented.
- Use clear error messages.
- Keep examples copy-ready and realistic.
- Avoid hidden network or filesystem behavior.

## Security Model

uvpy.run does not execute scripts on the server for users. It serves raw Python
files and documentation pages. Users run scripts locally with `uv run`.

Because remote script execution carries risk, the product should keep trust
signals visible:

- raw source access,
- dependency list,
- Python version requirement,
- line count,
- update date,
- copy-ready examples,
- reminders to review before running.

## Roadmap

### Phase 0: Stabilize Current UX

- [x] Keep the redesigned detail page stable.
- [x] Add smoke tests around route rendering and metadata parsing.
- [x] Fix the catch-all script route so missing files return a real 404 status.
- [x] Remove or resolve duplicated static route behavior.

### Phase 1: Improve Discovery

- [x] Add homepage search.
- [x] Add category filtering.
- [x] Show tool counts and clearer categories.
- [x] Give each tool card clear actions: copy command, details, source.

### Phase 2: Standardize Metadata

- [x] Extract script parsing from `main.py` into a dedicated module.
- [x] Define a `ToolMetadata` shape.
- [x] Parse PEP 723 data, docstring sections, examples and source facts once.
- [x] Add tests for real scripts in `static_pyfiles/`.

### Phase 3: Strengthen Trust

- Improve source preview and dependency visibility.
- Add license/hash information where useful.
- Consider a lightweight "verified" marker for reviewed scripts.
- Make security reminders useful without making the site feel scary.

### Phase 4: Raise Tool Quality

- Normalize every script's PEP 723 block and docstring.
- Ensure each tool supports `--help` where appropriate.
- Add a local metadata lint command.
- Review scripts for naming, examples and side effects.

## Tool Backlog

Good uvpy.run tools should be small, inspectable, copy-ready and useful from a
terminal. Prefer one-shot commands with clear input and output. Avoid tools that
need long-running sessions, complex authentication, hidden side effects or
environment-specific assumptions.

Network debugging tools are intentionally not part of the near-term backlog.
Python-level checks can be misleading for lower-level networking questions, so
those tools should wait until the product has a clearer stance on accuracy and
scope.

### First Batch

These are good candidates for the next implementation pass because they are
useful, low risk and can become examples for future tool quality:

- [ ] `jsonfmt.py` - format, minify and validate JSON from stdin or a file.
- [ ] `timestamp.py` - convert Unix timestamps, ISO strings and local time.
- [ ] `hashsum.py` - compute file or text hashes such as SHA-256 and BLAKE2.
- [ ] `base64tool.py` - encode and decode Base64 safely from stdin or args.
- [ ] `slugify.py` - convert titles or filenames into URL-friendly slugs.
- [ ] `treeview.py` - print a compact directory tree with ignore patterns.

### Developer Utilities

- [ ] `yamlfmt.py` - validate and format YAML.
- [ ] `tomlcheck.py` - validate TOML files.
- [ ] `envcheck.py` - compare `.env` files against an example file.
- [ ] `gitignore_gen.py` - generate common `.gitignore` templates.
- [ ] `uuidgen.py` - generate UUID, ULID or NanoID values.

### Text Utilities

- [ ] `caseconv.py` - convert between snake, camel, kebab and title case.
- [ ] `dedupe_lines.py` - deduplicate, sort and count lines.
- [ ] `extract_urls.py` - extract URLs, emails or IP-looking strings from text.
- [ ] `wordcount.py` - count lines, words, characters and bytes.
- [ ] `urlencode.py` - URL encode and decode strings.

### Security And Secret Helpers

- [ ] Improve `passwordgen.py` with clearer options and examples.
- [ ] Improve `flask_secret.py` into a more general secret generator.
- [ ] `jwtpeek.py` - decode JWT headers and payloads without verification.
- [ ] `totp_uri.py` - inspect otpauth URLs without exposing secrets by default.

### Image And Media Utilities

- [ ] Clarify or merge `imgtr.py` and `imgtrans.py`.
- [ ] `imgresize.py` - resize one image or a directory of images.
- [ ] `imgcompress.py` - compress common image formats.
- [ ] `exifstrip.py` - remove image metadata.
- [ ] `favicon_gen.py` - generate favicon assets from a source image.

### File And System Utilities

- [ ] Improve `disk_usage.py` with clearer output and edge-case handling.
- [ ] Improve `mkdir_batch.py` with dry-run and safer conflict handling.
- [ ] `rename_batch.py` - batch rename files, defaulting to dry-run.
- [ ] `find_large.py` - find large files under a directory.
- [ ] `backup_manifest.py` - generate a file hash manifest.

### Generation Utilities

- [ ] Improve `qr.py` and add more copy-ready examples.
- [ ] `qrcode_wifi.py` - generate Wi-Fi QR codes.
- [ ] `lorem.py` - generate placeholder text.
- [ ] `fake_data.py` - generate small fake datasets for demos.
- [ ] `cron_explain.py` - explain cron expressions in plain language.

### Existing Tool Triage

- [ ] Keep and polish: `passwordgen.py`, `flask_secret.py`, `qr.py`.
- [ ] Keep but standardize: `disk_usage.py`, `mkdir_batch.py`, `nospace.py`,
      `cld.py`.
- [ ] Clarify naming and scope: `imgtr.py`, `imgtrans.py`.
- [ ] Keep as showcase or fun extras: `snake.py`, `brick.py`.
- [ ] Keep as advanced/self-use tools with clearer docs:
      `aria2rpc_watch.py`, `terminal_proxy_ip.py`.
- [ ] Move or normalize: `demo.py`.

### Phase 5: Automate SEO

- Generate sitemap entries from the actual tool collection.
- Generate JSON-LD and OpenGraph metadata from parsed tool metadata.
- Avoid hand-maintaining URLs when scripts are added or removed.

### Phase 6: Production Hardening

- Add CI smoke checks.
- Add a health endpoint.
- Handle proxy HTTPS detection explicitly.
- Review deployment config for gunicorn, logging and environment variables.

## Collaboration Notes

This project is being developed through an ongoing human plus agent workflow.
See `AGENTS.md` for the working agreement, project priorities and rules for
future coding agents.
