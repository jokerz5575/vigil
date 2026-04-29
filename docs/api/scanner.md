# `LicenseScanner` & `LicensePolicy`

**Module:** `vigil_licenses.scanner`  
**Source:** `vigil-licenses/src/vigil_licenses/scanner.py`

This module provides the two entry-point classes for running a compliance scan:
`LicensePolicy` describes *what is acceptable*, and `LicenseScanner` reads the installed
environment, resolves licenses, and produces a `ComplianceReport`.

---

## `LicensePolicy`

Defines the allow-list, block-list, warn-list, and unknown-license behaviour for a scan.

### Constructor

```python
LicensePolicy(
    allow: list[str] | None = None,
    block: list[str] | None = None,
    warn:  list[str] | None = None,
    fail_on_unknown: bool = False,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allow` | `list[str] \| None` | `None` | If set, only these SPDX IDs are allowed without conflict. Any license absent from the list becomes an `ERROR`. A value of `None` disables the allow-list check entirely. |
| `block` | `list[str] \| None` | `[]` | SPDX IDs that always produce an `ERROR`, regardless of the allow list. |
| `warn` | `list[str] \| None` | `[]` | SPDX IDs that produce a `WARNING`.  Processed *before* the allow-list check (see note below). |
| `fail_on_unknown` | `bool` | `False` | If `True`, any dependency whose license cannot be identified is added as an `ERROR` conflict in the report. |

!!! warning "Warn-before-allow precedence"
    A license that appears in `warn` generates a `WARNING` even if it is *not* in the
    `allow` list.  The warn check short-circuits the rest of the evaluation for that
    dependency, so the allow-list `ERROR` is never reached.  Use this intentionally
    when you want to flag a license for review without hard-failing the scan.

    ```python
    # LGPL-3.0 is in warn — it produces a WARNING,
    # even though it is not in the allow list.
    policy = LicensePolicy(
        allow=["MIT", "Apache-2.0"],
        warn=["LGPL-3.0"],
    )
    ```

### `from_dict(data)`

```python
@classmethod
def from_dict(cls, data: dict) -> LicensePolicy
```

Constructs a `LicensePolicy` from a plain Python dict.  Supports two input shapes:

=== "Nested (policy wrapper)"

    ```python
    policy = LicensePolicy.from_dict({
        "policy": {
            "allow": ["MIT", "Apache-2.0", "BSD-3-Clause"],
            "block": ["GPL-3.0", "AGPL-3.0", "SSPL-1.0"],
            "warn":  ["LGPL-2.1", "LGPL-3.0", "MPL-2.0"],
            "fail_on_unknown": False,
        }
    })
    ```

=== "Flat (no wrapper)"

    ```python
    policy = LicensePolicy.from_dict({
        "allow": ["MIT", "Apache-2.0"],
        "block": ["GPL-3.0"],
        "warn":  ["LGPL-3.0"],
    })
    ```

Missing keys fall back to their constructor defaults (`allow=None`, `block=[]`, etc.).

### `from_yaml(path)`

```python
@classmethod
def from_yaml(cls, path: str | Path) -> LicensePolicy
```

Reads a YAML file from `path` and delegates to `from_dict()`.  Requires
[PyYAML](https://pypi.org/project/PyYAML/) to be installed.

```python
policy = LicensePolicy.from_yaml("vigil.yaml")
# or
policy = LicensePolicy.from_yaml(Path(__file__).parent / "policy.yaml")
```

If PyYAML is not installed the method raises:

```python
ImportError: PyYAML is required to load policy from YAML.
             Install it with: pip install pyyaml
```

!!! tip "YAML policy format"
    See the [Policy Reference](../policy.md) page for the full `vigil.yaml` schema
    and a complete annotated example.

---

## `LicenseScanner`

Scans Python dependencies against a `LicensePolicy` and returns a `ComplianceReport`.

### Constructor

```python
LicenseScanner(
    policy: LicensePolicy | None = None,
    license_db: LicenseDatabase | None = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `policy` | `LicensePolicy \| None` | `None` | Policy to enforce. Defaults to a permissive no-op policy (`LicensePolicy()`). |
| `license_db` | `LicenseDatabase \| None` | `None` | Database instance to use. Defaults to a fresh `LicenseDatabase()`. |

Both parameters accept pre-constructed instances, which is useful for dependency
injection in tests (see [Test Architecture](../testing.md#test-architecture)).

### `scan(requirements_file, project_name)`

```python
def scan(
    self,
    requirements_file: str | None = None,
    project_name: str | None = None,
) -> ComplianceReport
```

Resolves dependencies, evaluates each one against the policy, and returns a
`ComplianceReport`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `requirements_file` | `str \| None` | `None` | Path to a `requirements.txt` file. If `None`, scans all packages installed in the current Python environment. |
| `project_name` | `str \| None` | `None` | Embedded in the report's `project_name` field. |

#### Per-dependency evaluation order

For each resolved `DependencyInfo` the scanner applies the following logic:

1. **Unknown license** — if `dep.license_info` is `None`, add `"{name} ({raw})"` to
   `report.unknown_licenses`.  If `policy.fail_on_unknown` is `True`, also append an
   `ERROR` conflict.  Skip remaining checks for this dependency.

2. **Warn list** — if `dep.license_info.spdx_id` is in `policy.warn`, append a
   `WARNING` conflict and skip to the next dependency.  The allow-list check is
   *not* evaluated.

3. **Full conflict check** — call
   `db.check_conflict(name, spdx, policy_allow, policy_block)`.  Append the returned
   `LicenseConflict` if it is not `None`.

#### Full example

```python
from vigil_licenses.scanner import LicensePolicy, LicenseScanner
from vigil_licenses.reporter import generate_report, ReportFormat

# 1. Define a policy
policy = LicensePolicy(
    allow=[
        "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
        "ISC", "Unlicense", "CC0-1.0",
    ],
    block=["GPL-2.0", "GPL-3.0", "AGPL-3.0", "SSPL-1.0"],
    warn=["LGPL-2.1", "LGPL-3.0", "MPL-2.0"],
    fail_on_unknown=False,
)

# 2. Create the scanner
scanner = LicenseScanner(policy=policy)

# 3. Scan — either from requirements.txt …
report = scanner.scan(
    requirements_file="requirements.txt",
    project_name="my-project",
)

# … or the full installed environment
# report = scanner.scan(project_name="my-project")

# 4. Inspect the report
print(f"Scanned {report.total_dependencies} packages")
print(f"Errors : {sum(1 for c in report.conflicts if c.severity.value == 'error')}")
print(f"Warnings: {sum(1 for c in report.conflicts if c.severity.value == 'warning')}")

if report.has_errors:
    raise SystemExit(1)

# 5. Render a report
generate_report(report, ReportFormat.TERMINAL)
```

#### Scanning from `requirements.txt`

```python
scanner = LicenseScanner(policy=LicensePolicy.from_yaml("vigil.yaml"))
report  = scanner.scan(requirements_file="requirements.txt")

# All returned DependencyInfo objects have is_direct=True
assert all(d.is_direct for d in report.dependencies)
```

#### Loading a policy from YAML

```python
policy  = LicensePolicy.from_yaml("vigil.yaml")
scanner = LicenseScanner(policy=policy)
report  = scanner.scan()
```
