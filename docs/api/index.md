# API Reference

Vigil exposes **three importable Python packages**.  Each package is installed independently
and has its own versioned release — you can use `vigil-core` alone if you only need the
data models and the license database, or pull in `vigil-licenses` for the full scanning
and reporting stack.

---

## Package Overview

| Package | Module | Key Symbols |
|---|---|---|
| `vigil-core` | [`vigil_core.license_db`](license-db.md) | `LicenseDatabase` |
| `vigil-core` | [`vigil_core.models`](models.md) | `LicenseInfo`, `DependencyInfo`, `ComplianceReport`, `LicenseConflict` |
| `vigil-core` | `vigil_core.package_resolver` | `PackageResolver` |
| `vigil-licenses` | [`vigil_licenses.scanner`](scanner.md) | `LicenseScanner`, `LicensePolicy` |
| `vigil-licenses` | [`vigil_licenses.reporter`](reporter.md) | `generate_report`, `ReportFormat` |

!!! note "Pydantic v2"
    All public data classes (`LicenseInfo`, `DependencyInfo`, `ComplianceReport`,
    `LicenseConflict`) are **Pydantic v2 models**.  They support the full Pydantic
    API: `model_dump()`, `model_dump_json()`, `model_validate()`, and JSON Schema
    generation via `model_json_schema()`.

---

## Installation

=== "Core only"

    ```vigil/pyproject.toml#L1-2
    pip install vigil-core
    ```

    Provides the license database, Pydantic models, and package resolver.
    No scanning or reporting capabilities.

=== "Full stack"

    ```vigil/pyproject.toml#L1-2
    pip install vigil-licenses
    ```

    Installs `vigil-core` automatically as a dependency, plus the scanner and
    reporter.  Requires `rich`, `jinja2`, and `pyyaml` (optional, for YAML policy
    files).

=== "Development / editable"

    ```vigil/pyproject.toml#L1-4
    git clone https://github.com/jokerz5575/vigil
    cd vigil
    make install
    ```

---

## Quick Smoke Test

```vigil/vigil-core/src/vigil_core/__init__.py#L1-10
from vigil_core.license_db import LicenseDatabase
from vigil_licenses.scanner import LicenseScanner, LicensePolicy
from vigil_licenses.reporter import generate_report, ReportFormat

policy = LicensePolicy(block=["GPL-3.0", "AGPL-3.0", "SSPL-1.0"])
scanner = LicenseScanner(policy=policy)
report  = scanner.scan()

print(f"Scanned {report.total_dependencies} packages")
print(f"Errors : {sum(1 for c in report.conflicts if c.severity.value == 'error')}")

generate_report(report, ReportFormat.TERMINAL)
```

---

## Sub-pages

| Page | What it covers |
|---|---|
| [LicenseDatabase](license-db.md) | Built-in SPDX database, alias normalization, conflict detection |
| [LicenseScanner & Policy](scanner.md) | `LicensePolicy` construction, `LicenseScanner.scan()` evaluation logic |
| [Reporter](reporter.md) | Terminal, JSON, and HTML report generation |
| [Models](models.md) | All Pydantic models and enums with field-level documentation |
