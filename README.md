# uvpy.run

<p align="center">
  <img src="static/favicon-512.png" alt="uvpy.run website icon" width="96" height="96">
</p>

uvpy.run is a small directory of standalone Python tools that can be run
directly from a URL with [uv](https://github.com/astral-sh/uv).

The goal is simple: help you find a script, understand what it does, review its
source and dependencies, then copy a command you can run locally.

```bash
uv run https://uvpy.run/passwordgen.py
```

Every hosted tool is a self-contained Python file. When a tool needs
dependencies or a specific Python version, those requirements live inside the
script using [PEP 723](https://peps.python.org/pep-0723/) inline metadata.

## What You Can Do

- Browse small command-line tools by purpose.
- Open a detail page that explains what a script does before running it.
- Review the raw source and dependency metadata.
- Copy a ready-to-run `uv run` command.

uvpy.run serves and explains scripts. It does not execute arbitrary user code on
the server.

## Try It

Install uv if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Run a hosted script:

```bash
uv run https://uvpy.run/passwordgen.py --help
```

Inspect the source first:

```text
https://uvpy.run/passwordgen.py
```

## Run Locally

```bash
FLASK_SECRET=dev FLASK_DEBUG=1 uv run flask --app main run --host 127.0.0.1 --port 9999
```

Then open:

```text
http://127.0.0.1:9999/
http://127.0.0.1:9999/detail/passwordgen
```

You can also run a local script URL:

```bash
uv run http://127.0.0.1:9999/passwordgen.py --help
```

## Project Notes

Development status, implementation priorities, deployment notes, tool standards
and the backlog live in [ROADMAP.md](ROADMAP.md).

Agent collaboration rules live in [AGENTS.md](AGENTS.md).

Open source repository: <https://github.com/26awen/uvpy_run>.
