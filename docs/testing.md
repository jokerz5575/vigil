# Test Suite Reference

Vigil ships a comprehensive test suite with **532 tests** across eight focused modules,
achieving **93 % overall coverage** of the core library code.  Tests are written with
[pytest](https://pytest.org) and share fixtures defined in a central `conftest.py`.

---

## Running the Tests

=== "Full suite"

    ```bash
    make test
    # expands to: pytest tests/ -v --tb=short
    ```

=== "Stop on first failure"

    ```bash
    make test-fast
    # expands to: pytest tests/ -v --tb=short -x
    ```

=== "With coverage"

    ```bash
    make test-cov
    # terminal + HTML report in htmlcov/
    ```

=== "CI / XML output"

    ```bash
    make test-xml
    # coverage.xml + test-results.xml
    ```

=== "Single module"

    ```bash
    make test-module MOD=test_license_db
    make test-module MOD=test_scanner
    make test-module MOD=test_reporter
    ```

!!! tip "Running a single test"
    You can drill down to a specific class or test function with pytest directly:

    ```bash
    pytest tests/test_scanner.py::TestLicenseScannerMocked::test_blocked_license_raises_error -v
    ```

---

## Test Architecture

### `tests/conftest.py`

All shared fixtures are defined in `tests/conftest.py` and are automatically
available to every test module.

| Fixture | Scope | Description |
|---|---|---|
| `db` | function | A fresh `LicenseDatabase` instance |
| `dep_factory` | function | Factory function — see below |
| `report_factory` | function | Builds a `ComplianceReport` with optional `conflicts` and `dependencies` |
| `scanner_factory` | function | Builds a `LicenseScanner` with a mock `PackageResolver` injected |
| `strict_policy` | function | `LicensePolicy` with `allow=["MIT","Apache-2.0","BSD-3-Clause"]`, `block=["GPL-3.0","AGPL-3.0","SSPL-1.0"]` |
| `permissive_policy` | function | `LicensePolicy()` — no allow list, no block list |
| `tmp_requirements` | function | Writes a temporary `requirements.txt` to a `tmp_path` and returns its path |
| `tmp_yaml_policy` | function | Writes a temporary YAML policy file and returns its path |
| `vigil_yaml_path` | session | Absolute path to the repository's own `vigil.yaml` |

#### `dep_factory`

Builds a `DependencyInfo` object with sensible defaults, accepting any field as a
keyword argument:

```python
dep = dep_factory(name="requests", version="2.31.0", license_spdx="MIT")
dep = dep_factory(
    name="copyleft-lib",
    version="1.0.0",
    license_spdx="GPL-3.0",
    license_info=db.get("GPL-3.0"),
)
```

Inline `LicenseInfo` can be passed directly, avoiding a separate `db.get()` call.

#### `scanner_factory`

Injects a **mock `PackageResolver`** into the scanner so that `scan()` never calls
`importlib.metadata` or hits the live environment.  The factory accepts a list of
`DependencyInfo` objects that the mock resolver will return:

```python
scanner = scanner_factory(
    deps=[
        dep_factory(name="requests", license_spdx="MIT", license_info=db.get("MIT")),
        dep_factory(name="bad-lib",  license_spdx="GPL-3.0", license_info=db.get("GPL-3.0")),
    ],
    policy=strict_policy,
)
```

The only tests that bypass the mock and call `resolve_installed()` against the real
environment are in the `TestLicenseScannerRealInstall` class.

---

## Test Modules

### `test_license_db.py` — 173 tests

Exercises every method of `LicenseDatabase`.

**`TestGet`**

- All 14 built-in SPDX IDs are retrievable from the database
- `spdx_id` field on the returned object matches the lookup key
- `LicenseFamily` is correct for every known license
- `osi_approved` flag is correct (`SSPL=False`, `CC0=False`, `MIT=True`, …)
- `fsf_libre` flag is correct (`SSPL=False`, `MIT=True`, …)
- `allows_commercial_use` flag is correct (`SSPL=False`, all others `=True`)
- `network_clause` flag is set only on `AGPL-3.0` and `SSPL-1.0`
- Public-domain licenses (`Unlicense`, `CC0-1.0`) require no attribution
- `get()` returns `None` for unknown, empty, or wrong-case inputs

**`TestNormalize`**

- Exact SPDX IDs pass through unchanged (all 14)
- All 24 aliases in `_LICENSE_ALIASES` are resolved correctly
- Normalization is case-insensitive for aliases
- Leading / trailing whitespace is stripped before matching
- Returns `None` for unknown strings and empty input

**`TestResolve`**

- `resolve()` returns a `LicenseInfo` for known aliases
- `resolve()` returns `None` for unknown strings

**`TestCheckConflict`**

- Blocked license → `ConflictSeverity.ERROR`; reason mentions the SPDX ID
- Empty / `None` block list does not block anything
- License absent from allow list → `ERROR`
- License present in allow list → `None` (no conflict)
- Empty allow list `[]` is falsy → no allow-list restriction
- Block takes priority when a license is in both allow and block
- `SSPL-1.0` without any policy → `ERROR` (bug-fix: was previously `WARNING`)
- `SSPL-1.0` with explicit block → `ERROR`
- `SSPL-1.0` in allow list is still an `ERROR` (SSPL guard fires first)
- `AGPL-3.0` without any policy → `WARNING` (network-copyleft clause)
- `AGPL-3.0` warning reason mentions "network"
- `AGPL-3.0` in allow list still generates `WARNING`
- Permissive licenses (`MIT`, `Apache-2.0`, `BSD-3-Clause`, `ISC`) → `None`
- Strong copyleft (`GPL-2.0`, `GPL-3.0`) without policy → `None`
- Completely unknown SPDX not in block or allow → `None`
- Package name and license SPDX are preserved in conflict object

**`TestAllSpdxIds`**

- Returns a plain list
- Contains at least 14 entries
- All 14 expected IDs are present
- All values are strings
- No duplicates
- Every returned ID is retrievable via `get()`

---

### `test_models.py` — 81 tests

Covers all Pydantic model fields, defaults, properties, and methods.

**`TestLicenseInfo`**

- `is_permissive()` is `True` only for `PERMISSIVE` family
- `is_copyleft()` is `True` for `WEAK` / `STRONG` / `NETWORK` copyleft families
- All 7 `LicenseFamily` values covered by parametrized tests
- Default field values match spec (`osi_approved=False`, `url=None`, …)

**`TestDependencyInfo`**

- `display_name` property formats as `"name==version"`
- Default fields are `None` / `True` as specified
- Optional fields (`homepage`, `author`, `description`) accept values

**`TestComplianceReport`**

- `has_errors` is `True` when any conflict has severity `ERROR`
- `has_errors` is `False` when conflicts are only `WARNING`s
- `has_warnings` is `True` / `False` accordingly
- Both flags can be `True` simultaneously (mixed-severity report)
- Empty report has zero counts and `False` flags
- `license_families()` groups packages by family string
- Deps without `license_info` are excluded from `license_families()`

---

### `test_scanner.py` — 68 tests

Covers `LicensePolicy` construction and `LicenseScanner.scan()` logic.

**`TestLicensePolicy`**

- Default policy has `allow=None`, `block=[]`, `warn=[]`, `fail_on_unknown=False`
- `from_dict()` with full nested `{"policy": {…}}` structure
- `from_dict()` with partial data (missing keys use defaults)
- `from_dict()` with flat structure (no `"policy"` wrapper)
- `from_yaml()` loads a real YAML file into a `LicensePolicy` object
- `from_yaml()` raises `FileNotFoundError` for a missing path

**`TestLicenseScannerMocked`**

- All-permissive deps → no conflicts at all
- Blocked dep → `ERROR` with correct package name and SPDX ID
- Dep in warn list → `WARNING` (not `ERROR`)
- Warn list overrides missing-from-allow: dep in warn but not allow → `WARNING`
- Allow list: dep in list → no conflict
- Allow list: dep not in list → `ERROR`
- Unknown license with `fail_on_unknown=False` → no error, added to `unknown_licenses`
- Unknown license with `fail_on_unknown=True` → `ERROR` conflict
- `AGPL-3.0` with no explicit policy → `WARNING`
- `license_summary` counts are correct (`MIT×2`, `Apache×1`, etc.)
- Multiple deps produce multiple conflicts with correct severities
- `is_direct=False` → correct `direct_dependencies` count
- `project_name` is passed through to the report
- Empty dep list → 0 conflicts, 0 dependencies

**`TestLicenseScannerRealInstall`**

- `scan()` on real environment completes without raising
- `scan()` with a `requirements.txt` file finds at least 1 package

---

### `test_reporter.py` — 57 tests

Verifies JSON, HTML, and terminal report rendering.

**`TestJSONReport`**

- `_render_json()` returns valid JSON (parseable by `json.loads`)
- JSON contains required top-level keys
- `project_name` value is preserved
- `conflicts` array has correct length and per-entry fields
- `severity` is serialised as a lowercase string (`"error"` / `"warning"`)
- `generate_report()` with JSON format returns the same string
- `generate_report()` with `output_path` writes file; file contains valid JSON

**`TestHTMLReport`**

- `_render_html()` returns a non-empty string
- Output contains `<!DOCTYPE html>`
- Project name appears in the rendered HTML
- Package name and SPDX ID appear when there are conflicts
- "No license conflicts" message appears for conflict-free reports
- `generate_report()` with HTML format returns the HTML string
- `generate_report()` with `output_path` writes the file

**`TestTerminalReport`**

- `generate_report()` with `TERMINAL` format returns `""`
- Does not raise for empty / error / warning reports

**`TestReportFormat`**

- Enum string values: `TERMINAL=="terminal"`, `JSON=="json"`, `HTML=="html"`

---

### `test_package_resolver.py` — 35 tests

Exercises `PackageResolver` against the live `importlib.metadata` environment.

**`TestResolveInstalled`**

- Returns a list of `DependencyInfo` objects
- Every item has a non-empty `name` and `version`
- `pytest` itself is present in the results
- `pypi_url` (when set) contains `"pypi.org/project"`

**`TestResolveFromRequirements`**

- Known installed packages are resolved (`pytest`, `pydantic`)
- All returned items have `is_direct=True`
- Unknown packages get `version="unknown"`
- Comment lines and blank lines are ignored
- `==` version pins are stripped (`pytest==8.0.0` → `name="pytest"`)
- `>=` version constraints are stripped (`pydantic>=2.0` → `name="pydantic"`)

**`TestFromDistribution`**

- Real `pydantic` distribution → `DependencyInfo` with `name="pydantic"`
- Custom `LicenseDatabase` is stored as `resolver._db`

---

### `test_policy_yaml.py` — 47 tests

Validates the repository's own `vigil.yaml` policy file, both structurally and
functionally.

**`TestVigilYamlStructure`**

- `vigil.yaml` exists on disk
- Loads as valid YAML (non-`None` dict)
- Has top-level `"policy"` key
- Has `"allow"`, `"block"`, `"warn"` sub-keys under `"policy"`
- Every entry in each list is a plain string
- `fail_on_unknown` (if present) is a bool

**`TestVigilYamlContent`**

- `allow` contains `MIT`, `Apache-2.0`, `BSD-3-Clause`, `ISC`, `Unlicense`, `CC0-1.0`
- `block` contains `GPL-2.0`, `GPL-3.0`, `AGPL-3.0`, `SSPL-1.0`
- `warn` contains `LGPL-2.1`, `LGPL-3.0`, `MPL-2.0`
- No duplicate entries in `allow`, `block`, or `warn`
- `allow ∩ block = ∅` (completely disjoint)
- `warn ∩ block = ∅` (completely disjoint)
- `allow ∩ warn = ∅` (completely disjoint)
- `allow` has ≥ 30 entries (extended policy)
- `block` contains the `-only` / `-or-later` GPL variants
- `warn` contains at least one EPL variant and `MPL-2.0`

**`TestVigilYamlLoadedAsPolicy`**

- `LicensePolicy.from_yaml(vigil_yaml_path)` loads without error
- Loaded policy has ≥ 30 allow entries containing `"MIT"`
- Loaded policy `block` contains `"GPL-3.0"`
- `db.check_conflict("gpl-lib", "GPL-3.0", policy_block=…)` → `ERROR`
- `db.check_conflict("safe-lib", "MIT", policy_allow=…)` → `None`

---

## Coverage Report

Run `make test-cov` to reproduce this output:

```python
Name                                            Stmts   Miss Branch BrPart  Cover
vigil-core/src/vigil_core/license_db.py            36      0     14      0   100%
vigil-core/src/vigil_core/models.py                74      0      4      0   100%
vigil-core/src/vigil_core/package_resolver.py      59      3     24      4    92%
vigil-licenses/src/vigil_licenses/reporter.py      72      2     26      4    94%
vigil-licenses/src/vigil_licenses/scanner.py       53      2     12      0    97%
TOTAL                                             294      7     80      8    96%
```

The three files below 100 % all relate to live-environment or optional-dependency paths:

| File | Uncovered lines | Reason |
|---|---|---|
| `package_resolver.py` | 3 statements / 4 branches | Exception handler in `_from_distribution` and edge cases in live `resolve_installed()` |
| `reporter.py` | 2 statements / 4 branches | `rich` rendering paths for empty-conflict edge cases |
| `scanner.py` | 2 statements | `ImportError` guard for the optional `pyyaml` dependency |

---

## Writing New Tests

Follow these guidelines when adding tests to the suite:

- **Use fixtures from `conftest.py`** rather than constructing objects inline.
  `dep_factory`, `scanner_factory`, and `report_factory` keep test bodies short and
  readable.

- **Never call `resolve_installed()` directly** in scanner tests.  Use `scanner_factory`
  with an explicit `deps` list so the test is isolated from the live environment.
  Reserve real-environment tests for the `TestLicenseScannerRealInstall` class.

- **Mark slow or integration tests** with `@pytest.mark.slow` so they can be skipped
  during fast feedback loops:

    ```python
    @pytest.mark.slow
    def test_pypi_api_fallback():
        ...
    ```

    Run the marked tests explicitly with:

    ```bash
    pytest -m slow
    ```

- **Use `@pytest.mark.parametrize`** for any test that applies the same logic to
  multiple inputs.  The `TestCheckConflict` and `TestLicenseInfo` sections in
  `test_license_db.py` and `test_models.py` are good examples to follow.
