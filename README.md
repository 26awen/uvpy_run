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
- `robots.txt` and the dynamic `/sitemap.xml` route support search indexing.
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

## Production Deployment

Production currently runs the Flask app with Gunicorn on the remote host and is
exposed through an already-running Cloudflare Tunnel. The Tunnel points at the
local Gunicorn listener on port `9999`, so ordinary code deploys should only need
to update the repository and restart Gunicorn.

Current production facts:

- SSH target: `wwd@100.121.55.115`
- Project path: `/home/wwd/python_projects/uvpy_run`
- Branch: `main`
- Local app port: `9999`
- Gunicorn command:
  `/home/wwd/.local/bin/uv run gunicorn -w 4 -b 0.0.0.0:9999 main:app`

Do not put SSH passwords, tokens, or Cloudflare credentials in this repository.
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

## Roadmap And Tool Backlog

Detailed implementation priorities and candidate tools live in
[ROADMAP.md](ROADMAP.md). The short version:

- Keep uvpy.run as a lightweight directory for inspectable Python scripts.
- Improve discovery, trust signals and metadata quality.
- Add small, copy-ready CLI tools one at a time.

## Collaboration Notes

This project is being developed through an ongoing human plus agent workflow.
See `AGENTS.md` for the working agreement, project priorities and rules for
future coding agents.
