# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

#### `vigil.yaml` — Comprehensive Open Source License Policy
Extended the root policy file from 14 license entries to **~110 SPDX identifiers**,
organized into three well-documented tiers:

- **`allow`** (~65 licenses) — Permissive & public-domain licenses safe for most
  commercial and open-source projects. Grouped into named families:
  - Public Domain: `CC0-1.0`, `Unlicense`, `0BSD`
  - MIT family: `MIT`, `MIT-0`, `MIT-Modern-Variant`
  - Apache: `Apache-2.0`
  - BSD family: all 7 variants (`BSD-2-Clause`, `BSD-3-Clause`, `BSD-4-Clause`,
    `BSD-4-Clause-UC`, `BSD-2-Clause-Patent`, LBNL & Open-MPI variants)
  - ISC / NCSA
  - Python ecosystem: `PSF-2.0`, `Python-2.0`, `CNRI-Python`
  - Boost: `BSL-1.0`
  - Academic: `AFL-2.1`, `AFL-3.0`
  - System libraries: `Zlib`, `Libpng`, `libtiff`, `IJG`, `FTL`, `HPND`, `NTP`,
    `PostgreSQL`, `curl`
  - Language runtimes: `PHP-3.0`, `PHP-3.01`, `Zend-2.0`, `TCL`, `Intel`
  - Web/standard: `W3C`, `X11`, `XFree86-1.1`, `Xnet`
  - Zope/Python web: `ZPL-2.0`, `ZPL-2.1`
  - Others: `WTFPL`, `UPL-1.0`, `MS-PL`, `Artistic-2.0`, `MulanPSL-2.0`,
    `VSL-1.0`, `SimPL-2.0`, etc.

- **`warn`** (~35 licenses) — Weak / file-level copyleft. Triggers a warning but
  does not fail the compliance check:
  - GNU LGPL family: all `-only` / `-or-later` variants for 2.0, 2.1, and 3.0
  - Mozilla (MPL): 1.0, 1.1, 2.0, and the no-copyleft-exception variant
  - Eclipse (EPL): 1.0 and 2.0
  - CDDL: 1.0 and 1.1
  - EUPL: 1.0, 1.1, and 1.2
  - Apple: `APSL-2.0`
  - Sun/Oracle legacy: `SPL-1.0`, `SISSL`, `LPL-1.0/1.02`
  - Others: `CPAL-1.0`, `CPL-1.0`, `LPPL-1.3c`, `OSL-1.0–3.0`, `RPL-1.1/1.5`,
    `Nokia`, `MS-RL`, `CeCILL-2.1`, `IPL-1.0`, `CC-BY-SA-3.0/4.0`, etc.

- **`block`** (~20 licenses) — Strong / network copyleft, non-OSI, commercial
  restrictions. Any match immediately fails the compliance check:
  - GNU GPL family: `GPL-2.0`, `GPL-3.0`, and all `-only`/`-or-later` variants
  - GNU AGPL family: `AGPL-1.0`, `AGPL-3.0`, and all variants
  - Non-OSI / cloud copyleft: `SSPL-1.0` (MongoDB), `BUSL-1.1` (HashiCorp/MariaDB)
  - Strong copyleft: `Sleepycat` (Berkeley DB)
  - Non-commercial CC: all `CC-BY-NC-*` variants
  - Proprietary catch-alls: `Commons-Clause`, `Proprietary`, `UNLICENSED`

#### Test Suite — 454 tests, 96% coverage
Brand-new test infrastructure covering the entire codebase:

| File | Tests | What's covered |
|---|---|---|
| `tests/conftest.py` | — | Shared fixtures: `db`, `dep_factory`, `report_factory`, `scanner_factory`, `strict_policy`, `permissive_policy`, `tmp_requirements`, `tmp_yaml_policy` |
| `tests/test_license_db.py` | 173 | All 14 SPDX IDs, all 24 aliases, all 6 `check_conflict` branches, flag correctness, case-sensitivity, `all_spdx_ids()` |
| `tests/test_models.py` | 81 | `is_permissive()` / `is_copyleft()` for all 7 `LicenseFamily` values, `display_name`, all defaults, `has_errors`/`has_warnings`, `license_families()` grouping |
| `tests/test_scanner.py` | 68 | Policy construction + YAML loading, blocked/warned/allowed licenses, `warn` overrides allow-list, `fail_on_unknown`, AGPL default warning, summary counts, mixed conflicts, real-env smoke tests |
| `tests/test_reporter.py` | 57 | JSON validity + all fields, HTML structure + conflict rendering, terminal no-raise, file output, enum values |
| `tests/test_package_resolver.py` | 35 | `resolve_installed`, `resolve_from_requirements` (version stripping, comments, missing packages), `_from_distribution` with real packages |
| `tests/test_policy_yaml.py` | 47 | YAML structure, all list types, no duplicates, `allow ∩ block = ∅`, `warn ∩ block = ∅`, ≥30 allow entries, policy round-trip via `LicensePolicy.from_yaml` |

#### `Makefile` — Developer build automation

| Target | Action |
|---|---|
| `make install` | Installs all three packages (editable) + all dev deps |
| `make test` | Full test suite |
| `make test-fast` | Stops on first failure (`-x`) |
| `make test-cov` | Coverage with terminal output + `htmlcov/index.html` |
| `make test-xml` | JUnit XML + coverage XML for CI |
| `make lint` / `make format` | `ruff check` / `ruff format` |
| `make typecheck` | `mypy` over all source trees |
| `make build` | Builds wheels for all three packages via `hatch` |
| `make scan` | Dogfoods `vigil scan --policy vigil.yaml` |
| `make clean` | Removes all caches, `dist/`, `htmlcov/`, etc. |

#### Package metadata & missing files
- Added `vigil-licenses/README.md` and `vigil-cli/README.md` (required by hatchling)
- Added `pyyaml>=6.0` to `vigil-licenses` runtime dependencies
  (`LicensePolicy.from_yaml` previously had a silent `ImportError` fallback)
- Added `pytest-cov>=5.0.0` and `pyyaml>=6.0` to `vigil-core` dev extras
- Added `pytest-cov>=5.0.0` to `vigil-licenses` dev extras
- Added `[tool.coverage.run]` and `[tool.coverage.report]` to root `pyproject.toml`

### Fixed

#### `vigil-core` — Dead-code SSPL `ERROR` check in `LicenseDatabase.check_conflict`
`SSPL-1.0` has `family == NETWORK_COPYLEFT`. The generic network-copyleft branch
fired first, returning only a `WARNING` instead of the intended `ERROR`. The
SSPL-specific `ERROR` check immediately below it was therefore unreachable.

**Fix:** moved the `SSPL-1.0` guard *above* the `NETWORK_COPYLEFT` family check so
that it fires first and correctly returns `ConflictSeverity.ERROR` even when no
explicit block policy is configured.

---

## [0.1.0] — 2024 (Initial Release)

### Added
- `vigil-core`: shared foundation — `LicenseDatabase`, `PackageResolver`, Pydantic models
- `vigil-licenses`: `LicenseScanner`, `LicensePolicy`, compliance reporter (terminal / JSON / HTML)
- `vigil-cli`: Typer-based CLI (`vigil scan`, `vigil licenses check`, `vigil licenses report`)
- Initial `vigil.yaml` with 7 allowed, 3 warned, and 4 blocked licenses
- GitHub Actions CI workflow (test matrix Python 3.9–3.12, dogfood compliance check, PyPI publish)
