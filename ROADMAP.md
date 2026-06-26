# Roadmap, Status And Tool Backlog

This document tracks the implementation plan, current project shape,
maintenance notes and tool backlog for uvpy.run so the README can stay focused
on what the project is and how to use it.

## Current Shape

- `main.py` is the Flask application.
- `tool_metadata.py` parses script metadata for pages and future automation.
- `static_pyfiles/` contains the published Python tools.
- `templates/` contains the homepage and script detail pages.
- `static/` contains icons and other static assets.
- `robots.txt` and the dynamic `/sitemap.xml` route support search indexing.
- Open source repository: <https://github.com/26awen/uvpy_run>.

The app currently serves:

- `/` - tool directory page.
- `/detail/<script_name>` - human-readable detail page for a script.
- `/<script_name>.py` - raw Python script download/execution URL.
- `/robots.txt` and `/sitemap.xml`.

## Verification

Use these checks before handing off backend or template changes:

```bash
uv run python -m py_compile catalog_lint.py main.py tool_metadata.py static_pyfiles/*.py
```

```bash
uv run python -m unittest discover -s tests
```

```bash
uv run python catalog_lint.py
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

For UX changes, also inspect:

- `/`
- `/detail/passwordgen`
- `/detail/brick`

Check desktop and mobile widths for horizontal overflow, clipped command text,
inaccessible copy buttons, repeated list markers from docstring parsing, broken
source preview and missing dependency metadata.

## Production Deployment

Production currently runs the Flask app with Gunicorn on the remote host and is
exposed through an already-running Cloudflare Tunnel. The Tunnel points at the
local Gunicorn listener on port `9999`, so ordinary code deploys should only
need to update the repository and restart Gunicorn.

Current production facts:

- SSH target: `wwd@100.121.55.115`
- Project path: `/home/wwd/python_projects/uvpy_run`
- Branch: `main`
- Local app port: `9999`
- Gunicorn command:
  `/home/wwd/.local/bin/uv run gunicorn -w 4 -b 0.0.0.0:9999 main:app`

Do not put SSH passwords, tokens or Cloudflare credentials in this repository.
If SSH uses password auth, enter it interactively or through the calling tool's
secure prompt.

Recommended deploy flow:

```bash
ssh wwd@100.121.55.115
cd /home/wwd/python_projects/uvpy_run
```

Fetch first while the old app is still serving traffic:

```bash
git fetch origin main
git status --short --branch
git rev-parse --short HEAD
git rev-parse --short origin/main
```

If the worktree is clean and `origin/main` is the desired target, stop Gunicorn:

```bash
if [ -f gunicorn.pid ]; then
    kill "$(cat gunicorn.pid)" || true
fi

sleep 2
pgrep -af 'gunicorn.*main:app' || true
```

If old Gunicorn processes remain, inspect them before killing. Avoid broad
`pkill -f` commands that may match the current SSH shell command line.

Fast-forward the code and restart with the full `uv` path. The full path matters
because non-login SSH shells may not have `uv` on `PATH`.

```bash
git merge --ff-only origin/main

nohup /home/wwd/.local/bin/uv run gunicorn \
    -w 4 \
    -b 0.0.0.0:9999 \
    main:app \
    > gunicorn.log 2>&1 < /dev/null &

echo $! > gunicorn.pid
```

Keep runtime files local to the server:

```bash
grep -qxF 'gunicorn.log' .git/info/exclude || echo 'gunicorn.log' >> .git/info/exclude
grep -qxF 'gunicorn.pid' .git/info/exclude || echo 'gunicorn.pid' >> .git/info/exclude
```

Verify the service on the remote host:

```bash
git status --short --branch
pgrep -af 'gunicorn.*main:app'
curl -I --max-time 10 http://127.0.0.1:9999/
curl -I --max-time 10 http://127.0.0.1:9999/detail/passwordgen
tail -40 gunicorn.log
```

Then verify the Cloudflare Tunnel path from your local machine:

```bash
curl -I --max-time 20 https://uvpy.run/
curl -s --max-time 20 https://uvpy.run/detail/passwordgen | grep -m1 'Use It For'
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

Use It For:
    - Solving one clear terminal task
    - Producing copy-ready output or a small local file

Notes:
    - Mention filesystem, network, security, or long-running behavior here
"""
```

Preferred script behavior:

- Provide `--help` through `argparse`, `click`, or another CLI library.
- Keep side effects explicit and documented.
- Use clear error messages.
- Keep examples copy-ready and realistic.
- Add at least one named docstring section after examples so the detail page's
  "What it does" panel stays scannable.
- Avoid hidden network or filesystem behavior.

Run the local catalog lint before handing off script or metadata changes:

```bash
uv run python catalog_lint.py
```

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

## Collaboration Notes

This project is being developed through an ongoing human plus agent workflow.
See [AGENTS.md](AGENTS.md) for the working agreement, project priorities and
rules for future coding agents.

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

- [x] Normalize every script's PEP 723 block and docstring.
- [x] Ensure each tool supports `--help` where appropriate.
- [x] Review scripts for naming, examples and side effects.
- [x] Add tests for catalog metadata, usage examples and CLI help.
- [x] Add a local metadata lint command.
- [ ] Consider clearer public aliases for tools whose URLs should not be renamed casually.

Current stable categories are `Developer`, `File`, `Game`, `Image`, `Network`,
`Security`, `System`, `Text` and `Time`. New scripts should use one of these
categories unless the taxonomy is intentionally updated with tests.

### Phase 5: Automate SEO

- [x] Generate sitemap entries from the actual tool collection.
- [x] Generate JSON-LD and OpenGraph metadata from parsed tool metadata.
- [x] Avoid hand-maintaining URLs when scripts are added or removed.

### Phase 6: Production Hardening

- Add CI smoke checks.
- Add a health endpoint.
- Handle proxy HTTPS detection explicitly.
- Review deployment config for gunicorn, logging and environment variables.

## Tool Backlog

Good uvpy.run tools should be small, inspectable, copy-ready and useful from a
terminal. Prefer one-shot commands with clear input and output. Avoid tools that
need long-running sessions, complex authentication, hidden side effects or
environment-specific assumptions.

Network debugging tools are intentionally not part of the near-term backlog.
Python-level checks can be misleading for lower-level networking questions, so
those tools should wait until the product has a clearer stance on accuracy and
scope.

Interactive games are a deliberate catalog exception to the one-shot command
preference. Keep new game scripts terminal-native and local-only: no Tkinter,
Pygame or browser UI unless explicitly chosen later. Favor readable ASCII or
Rich/Textual terminal output, copy-ready `uv run` examples, visible controls and
small testable game-state functions.

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

- [x] Improve `passwordgen.py` with cryptographic randomness and clearer validation.
- [x] Improve `flask_secret.py` into a more general secret generator.
- [ ] `jwtpeek.py` - decode JWT headers and payloads without verification.
- [ ] `totp_uri.py` - inspect otpauth URLs without exposing secrets by default.

### Image And Media Utilities

- [x] Merge `imgtr.py` and `imgtrans.py` into `image.py`.
- [ ] `imgresize.py` - resize one image or a directory of images.
- [ ] `imgcompress.py` - compress common image formats.
- [ ] `exifstrip.py` - remove image metadata.
- [ ] `favicon_gen.py` - generate favicon assets from a source image.

### File And System Utilities

- [ ] Improve `disk_usage.py` with clearer output and edge-case handling.
- [x] Improve `mkdir_batch.py` with dry-run and safer conflict handling.
- [ ] `rename_batch.py` - batch rename files, defaulting to dry-run.
- [ ] `find_large.py` - find large files under a directory.
- [ ] `backup_manifest.py` - generate a file hash manifest.

### Generation Utilities

- [x] Improve `qr.py` title/category for clearer discovery.
- [x] Add more copy-ready QR examples.
- [ ] `qrcode_wifi.py` - generate Wi-Fi QR codes.
- [ ] `lorem.py` - generate placeholder text.
- [ ] `fake_data.py` - generate small fake datasets for demos.
- [ ] `cron_explain.py` - explain cron expressions in plain language.

### Existing Tool Triage

- [ ] Keep and polish: `passwordgen.py`, `flask_secret.py`, `qr.py`.
- [ ] Keep but standardize: `disk_usage.py`, `mkdir_batch.py`, `nospace.py`,
      `today.py`.
- [x] Merge image transform/conversion behavior into `image.py`.
- [ ] Keep as showcase or fun extras: `snake.py`, `brick.py`.
- [ ] Treat future arcade additions as terminal-first; `brick.py` is a legacy
      GUI-style exception, not the model for new games.
- [ ] Keep as advanced/self-use tools with clearer docs:
      `aria2rpc_watch.py`, `terminal_proxy_ip.py`.
- [x] Normalize: `demo.py`.

### Terminal Arcade Candidates

These should stay terminal-based and inspectable, with no server-side execution
and no graphical window dependency:

- [ ] `space_invaders.py` - ASCII invaders, waves, score, lives and simple
      projectile timing. Best first candidate because the playfield is obvious
      in a terminal and the game logic can stay compact.
- [ ] `frogger.py` - cross lanes of cars and moving logs using deterministic
      row movement, simple collision checks and escalating speed.
- [ ] `pacman_lite.py` - fixed maze, pellets, one or two ghosts and optional
      power pellets. Keep the first version small enough to review easily.
- [ ] `tetris.py` - falling tetrominoes with line clears, next-piece preview
      and level speed. Higher implementation cost, but a strong terminal
      showcase if the state machine is well tested.
- [ ] `asteroids.py` - wraparound field with a rotating ship, thrust, shots and
      splitting rocks. Start with four-direction or eight-direction movement
      before considering smoother physics.
- [ ] `bomber_dash.py` - compact Bomberman-inspired grid with timed bombs,
      breakable blocks and simple enemy movement.
- [ ] `climber.py` - Donkey Kong-inspired ladders, platforms and rolling
      hazards using ASCII characters.
