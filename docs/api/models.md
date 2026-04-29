# Models

**Module:** `vigil_core.models`  
**Source:** `vigil-core/src/vigil_core/models.py`

All data classes in Vigil are **Pydantic v2 models** (or `str`-based enums).  They
support `model_dump()`, `model_dump_json()`, `model_validate()`, `model_json_schema()`,
and the full Pydantic validation pipeline.

---

## Enums

### `LicenseFamily`

High-level classification of a license's copyleft characteristics.

```vigil/vigil-core/src/vigil_core/models.py#L1-10
class LicenseFamily(str, Enum):
    PERMISSIVE       = "permissive"        # MIT, Apache-2.0, BSD, ISC
    WEAK_COPYLEFT    = "weak_copyleft"     # LGPL, MPL
    STRONG_COPYLEFT  = "strong_copyleft"   # GPL
    NETWORK_COPYLEFT = "network_copyleft"  # AGPL, SSPL
    PROPRIETARY      = "proprietary"
    PUBLIC_DOMAIN    = "public_domain"     # Unlicense, CC0
    UNKNOWN          = "unknown"
```

| Value | String | Example licenses |
|---|---|---|
| `PERMISSIVE` | `"permissive"` | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC |
| `WEAK_COPYLEFT` | `"weak_copyleft"` | LGPL-2.1, LGPL-3.0, MPL-2.0 |
| `STRONG_COPYLEFT` | `"strong_copyleft"` | GPL-2.0, GPL-3.0 |
| `NETWORK_COPYLEFT` | `"network_copyleft"` | AGPL-3.0, SSPL-1.0 |
| `PROPRIETARY` | `"proprietary"` | — (not in the built-in DB) |
| `PUBLIC_DOMAIN` | `"public_domain"` | Unlicense, CC0-1.0 |
| `UNKNOWN` | `"unknown"` | Unrecognised or missing license metadata |

---

### `ConflictSeverity`

The urgency level of a detected license conflict.

```vigil/vigil-core/src/vigil_core/models.py#L1-6
class ConflictSeverity(str, Enum):
    ERROR   = "error"    # Must fix — blocks compliance
    WARNING = "warning"  # Should review — potential issue
    INFO    = "info"     # Informational only
```

| Value | String | When raised |
|---|---|---|
| `ERROR` | `"error"` | Blocked license, license absent from allow list, or SSPL-1.0 |
| `WARNING` | `"warning"` | License in the warn list, or AGPL-3.0 without an explicit policy |
| `INFO` | `"info"` | Reserved for future use |

---

## Models

### `LicenseInfo`

Represents a single resolved software license with its full SPDX metadata.

```vigil/vigil-core/src/vigil_core/models.py#L1-14
class LicenseInfo(BaseModel):
    spdx_id:               str
    name:                  str
    family:                LicenseFamily
    osi_approved:          bool = False
    fsf_libre:             bool = False
    allows_commercial_use: bool = True
    requires_attribution:  bool = False
    requires_share_alike:  bool = False
    network_clause:        bool = False
    url:                   str | None = None
```

#### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `spdx_id` | `str` | — | Canonical SPDX identifier, e.g. `"MIT"` |
| `name` | `str` | — | Full human-readable license name |
| `family` | `LicenseFamily` | — | High-level family classification |
| `osi_approved` | `bool` | `False` | Approved by the Open Source Initiative |
| `fsf_libre` | `bool` | `False` | Classified as free by the Free Software Foundation |
| `allows_commercial_use` | `bool` | `True` | `False` only for SSPL-1.0 |
| `requires_attribution` | `bool` | `False` | Attribution clause in the license |
| `requires_share_alike` | `bool` | `False` | Copyleft share-alike requirement |
| `network_clause` | `bool` | `False` | `True` for AGPL-3.0 and SSPL-1.0 |
| `url` | `str \| None` | `None` | Link to the SPDX license page |

#### Methods

**`is_permissive() -> bool`**

Returns `True` if `family == LicenseFamily.PERMISSIVE`.

**`is_copyleft() -> bool`**

Returns `True` if `family` is any of `WEAK_COPYLEFT`, `STRONG_COPYLEFT`, or
`NETWORK_COPYLEFT`.

```vigil/vigil-core/src/vigil_core/models.py#L1-10
from vigil_core.license_db import LicenseDatabase

db = LicenseDatabase()
mit = db.get("MIT")

assert mit.is_permissive() is True
assert mit.is_copyleft() is False

gpl = db.get("GPL-3.0")
assert gpl.is_permissive() is False
assert gpl.is_copyleft() is True
```

---

### `DependencyInfo`

Represents a resolved Python package dependency with its license and PyPI metadata.

```vigil/vigil-core/src/vigil_core/models.py#L1-14
class DependencyInfo(BaseModel):
    name:         str
    version:      str
    license_spdx: str | None         = None
    license_info: LicenseInfo | None = None
    is_direct:    bool               = True
    homepage:     str | None         = None
    repository:   str | None         = None
    author:       str | None         = None
    description:  str | None         = None
    pypi_url:     str | None         = None
```

#### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | — | Package name as it appears in PyPI |
| `version` | `str` | — | Installed version string |
| `license_spdx` | `str \| None` | `None` | Normalized SPDX ID, or the raw license string if normalization failed |
| `license_info` | `LicenseInfo \| None` | `None` | Full license metadata; `None` if the license could not be resolved |
| `is_direct` | `bool` | `True` | `True` for packages listed in `requirements.txt`; may be `False` for transitive deps when resolved from the full environment |
| `homepage` | `str \| None` | `None` | From `Home-page` in package metadata |
| `repository` | `str \| None` | `None` | Repository URL (if available) |
| `author` | `str \| None` | `None` | From `Author` in package metadata |
| `description` | `str \| None` | `None` | From `Summary` in package metadata |
| `pypi_url` | `str \| None` | `None` | Auto-constructed as `https://pypi.org/project/{name}/` |

#### Property: `display_name`

```vigil/vigil-core/src/vigil_core/models.py#L1-4
@property
def display_name(self) -> str:
    return f"{self.name}=={self.version}"
```

Formats the dependency as `"name==version"`, matching the pip freeze style.

```vigil/vigil-core/src/vigil_core/models.py#L1-4
dep = DependencyInfo(name="requests", version="2.31.0")
assert dep.display_name == "requests==2.31.0"
```

---

### `LicenseConflict`

Represents a single detected compliance issue for a specific package.

```vigil/vigil-core/src/vigil_core/models.py#L1-8
class LicenseConflict(BaseModel):
    package:        str
    license_spdx:   str
    severity:       ConflictSeverity
    reason:         str
    recommendation: str | None = None
```

#### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `package` | `str` | — | Name of the offending package |
| `license_spdx` | `str` | — | SPDX ID of the license that caused the conflict |
| `severity` | `ConflictSeverity` | — | `ERROR`, `WARNING`, or `INFO` |
| `reason` | `str` | — | Human-readable explanation of why the conflict was raised |
| `recommendation` | `str \| None` | `None` | Suggested remediation action |

---

### `ComplianceReport`

The top-level result returned by `LicenseScanner.scan()`.

```vigil/vigil-core/src/vigil_core/models.py#L1-14
class ComplianceReport(BaseModel):
    generated_at:        datetime             = Field(default_factory=datetime.utcnow)
    project_name:        str | None           = None
    total_dependencies:  int                  = 0
    direct_dependencies: int                  = 0
    dependencies:        list[DependencyInfo] = Field(default_factory=list)
    conflicts:           list[LicenseConflict]= Field(default_factory=list)
    unknown_licenses:    list[str]            = Field(default_factory=list)
    license_summary:     dict[str, int]       = Field(default_factory=dict)
```

#### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `generated_at` | `datetime` | `datetime.utcnow()` | Timestamp of the scan |
| `project_name` | `str \| None` | `None` | Optional project identifier embedded in the report |
| `total_dependencies` | `int` | `0` | Total number of resolved packages |
| `direct_dependencies` | `int` | `0` | Number of packages with `is_direct=True` |
| `dependencies` | `list[DependencyInfo]` | `[]` | All resolved dependencies |
| `conflicts` | `list[LicenseConflict]` | `[]` | All detected conflicts |
| `unknown_licenses` | `list[str]` | `[]` | `"{name} ({raw})"` strings for unresolvable licenses |
| `license_summary` | `dict[str, int]` | `{}` | Mapping of SPDX ID → package count (excludes unknowns) |

#### Properties

**`has_errors -> bool`**

`True` if any conflict has `severity == ConflictSeverity.ERROR`.

**`has_warnings -> bool`**

`True` if any conflict has `severity == ConflictSeverity.WARNING`.

#### Method: `license_families()`

```vigil/vigil-core/src/vigil_core/models.py#L1-4
def license_families(self) -> dict[str, list[str]]
```

Groups package names by their resolved license family.  Dependencies without a
`license_info` are excluded.

```vigil/vigil-core/src/vigil_core/models.py#L1-8
families = report.license_families()
# Example output:
# {
#     "permissive":    ["requests", "click", "pydantic"],
#     "weak_copyleft": ["some-lgpl-lib"],
# }
```

#### Usage example

```vigil/vigil-core/src/vigil_core/models.py#L1-30
from datetime import datetime
from vigil_core.models import (
    ComplianceReport,
    LicenseConflict,
    ConflictSeverity,
    DependencyInfo,
)
from vigil_core.license_db import LicenseDatabase

db = LicenseDatabase()
mit_info = db.get("MIT")

dep = DependencyInfo(
    name="requests",
    version="2.31.0",
    license_spdx="MIT",
    license_info=mit_info,
)
conflict = LicenseConflict(
    package="bad-lib",
    license_spdx="GPL-3.0",
    severity=ConflictSeverity.ERROR,
    reason="GPL-3.0 is explicitly blocked by your policy.",
    recommendation="Find an alternative package with a compatible license.",
)

report = ComplianceReport(
    project_name="my-project",
    total_dependencies=2,
    direct_dependencies=2,
    dependencies=[dep],
    conflicts=[conflict],
    license_summary={"MIT": 1},
)

assert report.has_errors is True
assert report.has_warnings is False
assert report.license_families() == {"permissive": ["requests"]}

# Serialise to JSON
json_str = report.model_dump_json(indent=2)
```
