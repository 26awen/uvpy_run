# Roadmap And Tool Backlog

This document tracks the concrete implementation plan for uvpy.run so the
README can stay focused on what the project is and how to use it.

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
- [ ] Add a local metadata lint command.
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

- [x] Clarify `imgtr.py` and `imgtrans.py` as single-image transform vs batch conversion tools.
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
- [ ] Add more copy-ready QR examples.
- [ ] `qrcode_wifi.py` - generate Wi-Fi QR codes.
- [ ] `lorem.py` - generate placeholder text.
- [ ] `fake_data.py` - generate small fake datasets for demos.
- [ ] `cron_explain.py` - explain cron expressions in plain language.

### Existing Tool Triage

- [ ] Keep and polish: `passwordgen.py`, `flask_secret.py`, `qr.py`.
- [ ] Keep but standardize: `disk_usage.py`, `mkdir_batch.py`, `nospace.py`,
      `cld.py`.
- [x] Clarify naming and scope in metadata: `imgtr.py`, `imgtrans.py`.
- [ ] Keep as showcase or fun extras: `snake.py`, `brick.py`.
- [ ] Keep as advanced/self-use tools with clearer docs:
      `aria2rpc_watch.py`, `terminal_proxy_ip.py`.
- [x] Normalize: `demo.py`.
