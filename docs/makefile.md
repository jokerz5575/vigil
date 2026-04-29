# Makefile Reference

The Vigil repository ships a single `Makefile` at the repository root that automates every stage
of the development lifecycle — installing dependencies, running tests, linting, type-checking,
building docs, and publishing packages.  All three packages (`vigil-core`, `vigil-licenses`,
`vigil-cli`) are installed in *editable* mode, so source changes take effect immediately without
a re-install step.

---

## Quick-Reference Table

| Target | Description |
|---|---|
| `make install` | Install all three packages in editable mode plus dev dependencies |
| `make install-docs` | Install MkDocs Material and pymdown-extensions |
| `make test` | Run the full test suite — verbose, short traceback |
| `make test-fast` | Same as `test` but stops at the first failure (`-x`) |
| `make test-cov` | Full suite with terminal + HTML coverage report |
| `make test-xml` | Full suite producing JUnit XML + coverage XML for CI |
| `make test-module MOD=<name>` | Run a single test module by name |
| `make lint` | Ruff static analysis over all source trees (read-only) |
| `make format` | Ruff auto-formatter over all source trees |
| `make typecheck` | Mypy static type checker over all source trees |
| `make check` | `lint` + `typecheck` in one step |
| `make docs-serve` | Live-reload local preview at `http://127.0.0.1:8000` |
| `make docs-build` | Build static site into `site/` |
| `make docs-deploy` | Force-push built site to the `gh-pages` branch |
| `make build` | Build distributable wheels for all three packages via Hatch |
| `make scan` | Run a license compliance scan against Vigil's own environment |
| `make clean` | Remove all build, cache, and coverage artefacts |

---

## Recommended Workflows

### First-time setup

Run these four steps once after cloning the repository:

=== "Linux / macOS"

    ```vigil/Makefile#L1-4
    python3 -m venv .venv
    source .venv/bin/activate
    make install
    make test
    ```

=== "Windows"

    ```vigil/Makefile#L1-4
    python3 -m venv .venv
    .venv\Scripts\activate
    make install
    make test
    ```

After `make test` completes you should see **454 tests passed** and no failures.

### Daily development loop

```vigil/Makefile#L1-4
make test-fast   # fastest feedback — stops at first failure
make lint        # catch style issues before committing
# fix any issues, then:
make test-cov    # full picture with per-line coverage
```

### Before opening a pull request

1. Run `make check` — lint and type-check in one shot.
2. Run `make test-cov` — confirm overall coverage has not dropped below 90 %.
3. Open `htmlcov/index.html` in a browser to inspect any uncovered branches.

---

## Install Targets

### `make install`

Upgrades pip, then installs all three packages in editable mode together with
`pytest`, `pytest-cov`, and `pyyaml`:

```vigil/Makefile#L1-8
pip install --upgrade pip
pip install -e "vigil-core[dev]"
pip install -e "vigil-licenses[dev]"
pip install -e "vigil-cli[dev]"
pip install pytest pytest-cov pyyaml
```

**When to use:** once after cloning, and again whenever `pyproject.toml` changes in
any of the three sub-packages.

### `make install-docs`

```vigil/Makefile#L1-2
pip install "mkdocs-material>=9.5" "pymdown-extensions>=10.0"
```

**When to use:** before running any `docs-*` target for the first time.

---

## Testing Targets

### `make test`

```vigil/Makefile#L1-2
pytest tests/ -v --tb=short
```

Runs the complete test suite in verbose mode with a short traceback on failure.
Use this for a final check before pushing.

### `make test-fast`

```vigil/Makefile#L1-2
pytest tests/ -v --tb=short -x
```

Identical to `make test` with the `-x` flag, which makes pytest exit immediately
on the first failing test.  Ideal during active development when you want tight
feedback cycles.

!!! tip "Single-module shortcut"
    To focus on one test module during a debugging session use:

    ```vigil/Makefile#L1-2
    make test-module MOD=test_scanner
    ```

    This expands to `pytest tests/test_scanner.py -v --tb=short`.  You can also
    target a single class or function directly with pytest:

    ```vigil/Makefile#L1-2
    pytest tests/test_scanner.py::TestLicenseScannerMocked::test_blocked_license_raises_error -v
    ```

### `make test-cov`

```vigil/Makefile#L1-5
pytest tests/ -v --tb=short \
    --cov=vigil_core --cov=vigil_licenses \
    --cov-report=term-missing \
    --cov-report=html:htmlcov
```

Runs the suite and writes two coverage reports:

- **Terminal** — printed inline after the test results, showing missed lines.
- **HTML** — written to `htmlcov/index.html`; open in a browser for branch-level
  detail.

**When to use:** before opening a PR, and in CI to track regressions.

### `make test-xml`

```vigil/Makefile#L1-5
pytest tests/ -v --tb=short \
    --cov=vigil_core --cov=vigil_licenses \
    --cov-report=xml:coverage.xml \
    --junitxml=test-results.xml
```

Emits machine-readable artifacts for CI pipelines:

| File | Purpose |
|---|---|
| `coverage.xml` | Cobertura-format coverage — upload to Codecov / SonarCloud |
| `test-results.xml` | JUnit XML — parsed by GitHub Actions test reporter |

**When to use:** automated CI runs only; the terminal output is less readable than
`make test-cov`.

### `make test-module MOD=<name>`

```vigil/Makefile#L1-2
pytest tests/$(MOD).py -v --tb=short
```

**Example:**

```vigil/Makefile#L1-2
make test-module MOD=test_license_db
make test-module MOD=test_reporter
```

**When to use:** when working on a specific module and wanting fast, targeted feedback
without waiting for the full 454-test suite.

---

## Code Quality Targets

### `make lint`

```vigil/Makefile#L1-2
ruff check vigil-core/src vigil-licenses/src vigil-cli/src
```

Read-only static analysis — reports style and logic issues without modifying any files.

### `make format`

```vigil/Makefile#L1-2
ruff format vigil-core/src vigil-licenses/src vigil-cli/src
```

Auto-formats all source trees in place.  Run this *before* `make lint`.

### `make typecheck`

```vigil/Makefile#L1-2
mypy vigil-core/src vigil-licenses/src vigil-cli/src
```

Runs Mypy with the project's `pyproject.toml` configuration.

### `make check`

```vigil/Makefile#L1-2
make lint
make typecheck
```

Convenience alias — runs lint and type-check in sequence.  Either step failing causes
the recipe to abort.

**When to use:** before opening a PR to catch both style issues and type errors at once.

---

## Documentation Targets

### `make docs-serve`

```vigil/Makefile#L1-2
mkdocs serve
```

Starts a live-reload development server at `http://127.0.0.1:8000`.  Any change to
a Markdown file or `mkdocs.yml` triggers an instant browser refresh.

**When to use:** while authoring or reviewing documentation locally.

### `make docs-build`

```vigil/Makefile#L1-2
mkdocs build --clean
```

Produces a fully static site in the `site/` directory.  The `--clean` flag removes
stale files from previous builds.

**When to use:** to verify the production build locally before deployment, or to inspect
generated HTML artefacts.

### `make docs-deploy`

```vigil/Makefile#L1-2
mkdocs gh-deploy --force --clean
```

Builds the site and force-pushes it to the `gh-pages` branch of the repository.  GitHub
Pages then serves the updated site from `https://jokerz5575.github.io/vigil/`.

!!! warning "CI deploys automatically"
    The GitHub Actions workflow deploys docs on every push to `master`.  Run
    `make docs-deploy` manually only when you need to push a hotfix to the live site
    outside of the normal CI flow.

---

## Build Targets

### `make build`

```vigil/Makefile#L1-6
pip install --quiet hatch
cd vigil-core     && hatch build
cd vigil-licenses && hatch build
cd vigil-cli      && hatch build
```

Builds source distributions and wheels for all three packages.  Artefacts land in:

```vigil/Makefile#L1-3
vigil-core/dist/
vigil-licenses/dist/
vigil-cli/dist/
```

**When to use:** before a release tag, or to inspect the wheel contents locally.

---

## Utility Targets

### `make scan`

```vigil/Makefile#L1-2
vigil scan --policy vigil.yaml
```

Runs Vigil against its *own* installed environment — a "dogfood" compliance check.
Useful for verifying that the policy file is valid and that no newly added dependency
violates the project's own license policy.

### `make clean`

Removes all ephemeral artefacts:

| Removed | Why |
|---|---|
| `__pycache__/`, `*.pyc` | Python bytecode cache |
| `.pytest_cache/` | pytest metadata |
| `.mypy_cache/` | Mypy incremental cache |
| `.ruff_cache/` | Ruff cache |
| `htmlcov/` | HTML coverage report |
| `site/` | MkDocs build output |
| `dist/`, `*.egg-info` | Build artefacts |
| `.coverage`, `coverage.xml` | Coverage data files |
| `test-results.xml` | JUnit XML |

---

## Variables

Every tool invocation is controlled by an overridable Make variable.  Pass a different
value on the command line to point at an alternative binary or interpreter.

| Variable | Default | Purpose |
|---|---|---|
| `PYTHON` | `python3` | Python interpreter used for any `$(PYTHON)` invocations |
| `PIP` | `pip` | Package installer |
| `PYTEST` | `pytest` | Test runner |
| `RUFF` | `ruff` | Linter / formatter |
| `MYPY` | `mypy` | Static type checker |
| `HATCH` | `hatch` | Build backend CLI |
| `MKDOCS` | `mkdocs` | Documentation builder |

**Example — running the test suite under a specific interpreter:**

```vigil/Makefile#L1-2
make test PYTEST="python -m pytest"
make test PYTHON=python3.12
```

!!! note "Variables apply to all targets"
    Variable overrides propagate to every recipe that references the variable, so
    `make test-cov PYTEST="python -m pytest"` works exactly as expected.
