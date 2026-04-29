# Getting Started

This guide walks you through installing Vigil, running your first scan, applying a policy file,
choosing an output format, and integrating with GitHub Actions.

---

## Prerequisites

- **Python 3.9 or later**
- **pip** (comes with Python)
- A Python project whose dependencies are installed in the current environment
  (virtualenv, conda env, or system Python)

---

## Installation

=== "pip (stable)"

    Install the scanner library and the CLI in one shot:

    ```bash
    pip install vigil-licenses vigil-cli
    ```

    This pulls in `vigil-core` automatically as a shared dependency.

=== "from source (editable)"

    Clone the repository and install all three packages in editable mode so that
    changes to the source are reflected immediately — no reinstall needed:

    ```bash
    git clone https://github.com/jokerz5575/vigil.git
    cd vigil

    pip install -e vigil-core
    pip install -e vigil-licenses
    pip install -e vigil-cli
    ```

    Or use the provided `Makefile` shortcut, which also installs all dev dependencies:

    ```bash
    make install
    ```

---

## Your First Scan

Run `vigil scan` with no arguments to inspect every package currently installed in
your Python environment:

```bash
vigil scan
```

Vigil will:

1. **Resolve** all installed distributions via `importlib.metadata`.
2. **Look up** each package's license against the built-in `LicenseDatabase`.
3. **Print** a rich terminal table showing package name, version, detected SPDX
   identifier, license family, and any conflicts.
4. **Exit 0** when no blocking violations are found.

!!! tip
    Run `vigil scan --help` to see all available options, including `--package`,
    `--requirements`, `--policy`, `--format`, `--output`, and `--fail-on-warning`.

---

## Using a Policy File

Without a policy file, Vigil only flags licenses it knows are problematic by default
(e.g. AGPL). To enforce your organisation's exact rules, point Vigil at a `vigil.yaml`:

```yaml
policy:
  allow:
    - MIT
    - Apache-2.0
    - BSD-3-Clause
  warn:
    - LGPL-2.1-or-later
  block:
    - GPL-3.0-or-later
  fail_on_unknown: false
```

Then pass it on the command line:

```bash
vigil scan --policy vigil.yaml
```

Any dependency whose license matches a `block` entry causes Vigil to exit with a
non-zero status code. `warn` entries are reported but do not fail the check unless
you also pass `--fail-on-warning`.

See the [Policy Reference](policy.md) for the full `vigil.yaml` format and a
catalogue of all ~110 pre-vetted SPDX identifiers.

!!! warning
    **GPL and AGPL in commercial projects** — if your product is closed-source or
    SaaS, shipping a dependency licensed under `GPL-2.0-or-later`, `GPL-3.0-only`,
    or any `AGPL-*` variant may require you to open-source your entire codebase or
    obtain a commercial licence from the upstream author. Always add these to your
    `block` list and consult legal counsel before proceeding.

---

## Output Formats

Vigil supports three output formats, selectable with the `--format` flag.

**Terminal (default)** — human-readable Rich table, printed to stdout:

```bash
vigil scan --policy vigil.yaml --format terminal
```

**JSON** — machine-readable, suitable for downstream tooling or dashboards:

```bash
vigil scan --policy vigil.yaml --format json
vigil scan --policy vigil.yaml --format json --output report.json
```

**HTML** — self-contained standalone report you can share or archive:

```bash
vigil scan --policy vigil.yaml --format html --output compliance-report.html
```

---

## GitHub License Scraper

When a package has no license metadata on PyPI, Vigil can automatically
search GitHub, find the canonical repository, and read the LICENSE file at the
exact version tag — giving you a **version-specific source URL** for every
resolution.

=== "Environment variable (recommended for CI)"

    ```bash
    export GITHUB_TOKEN=ghp_yourtoken
    vigil scan --policy vigil.yaml
    ```

=== "CLI flag"

    ```bash
    vigil scan --policy vigil.yaml --github-token ghp_yourtoken
    ```

!!! tip
    Without a token, Vigil still uses the GitHub API but is limited to
    **10 search requests / minute** (unauthenticated). With a token the limit
    is **5 000 requests / hour**. Generate a token at
    [github.com/settings/tokens](https://github.com/settings/tokens) — only
    **public repository read access** is required (no scopes needed for public
    repos).

!!! note "What the scraper returns"
    For each GitHub-resolved package, the terminal and HTML reports show a
    dedicated **🐙 GitHub-Resolved Licenses** table with the SPDX identifier
    and a **version-specific permalink** to the LICENSE file, e.g.
    `https://github.com/psf/requests/blob/v2.31.0/LICENSE`.

---

## CI/CD Integration

### GitHub Actions

Add the following workflow to `.github/workflows/compliance.yml` to run a license
compliance check on every push and pull request:

```yaml
name: License Compliance

on:
  push:
    branches: ["main", "master"]
  pull_request:

jobs:
  compliance:
    name: Vigil — license scan
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install project dependencies
        run: pip install -e ".[dev]"   # adjust to your install command

      - name: Install Vigil
        run: pip install vigil-licenses vigil-cli

      - name: Run compliance scan
        run: vigil scan --policy vigil.yaml --format terminal

      - name: Upload HTML report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: compliance-report.html
        continue-on-error: true
```

### Exit Codes

| Exit code | Meaning |
|---|---|
| `0` | All checks passed — no blocking violations found |
| `1` | One or more `block`-tier licenses detected (or warnings, if `--fail-on-warning` is set) |

Use these codes to gate pull request merges or deployment pipelines:

```bash
# Fail the build if any blocked license is present
vigil scan --policy vigil.yaml || exit 1

# Fail the build on warnings too (strict mode)
vigil scan --policy vigil.yaml --fail-on-warning || exit 1
```
