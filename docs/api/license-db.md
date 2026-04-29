# `LicenseDatabase`

**Module:** `vigil_core.license_db`  
**Source:** `vigil-core/src/vigil_core/license_db.py`

`LicenseDatabase` is an in-memory store of SPDX license metadata and a conflict-detection
engine.  It is instantiated once and reused across the entire scan lifecycle.

```python
from vigil_core.license_db import LicenseDatabase

db = LicenseDatabase()
```

---

## Built-in License Catalogue

The database is seeded from the private `_LICENSE_DATA` dict at module load time.  All
14 entries are available immediately — no network call or file I/O is required.

| SPDX ID | Name | Family | OSI | FSF | Commercial |
|---|---|---|---|---|---|
| `MIT` | MIT License | PERMISSIVE | ✓ | ✓ | ✓ |
| `Apache-2.0` | Apache License 2.0 | PERMISSIVE | ✓ | ✓ | ✓ |
| `BSD-2-Clause` | BSD 2-Clause "Simplified" | PERMISSIVE | ✓ | ✓ | ✓ |
| `BSD-3-Clause` | BSD 3-Clause "New" or "Revised" | PERMISSIVE | ✓ | ✓ | ✓ |
| `ISC` | ISC License | PERMISSIVE | ✓ | ✓ | ✓ |
| `LGPL-2.1` | GNU Lesser GPL v2.1 | WEAK_COPYLEFT | ✓ | ✓ | ✓ |
| `LGPL-3.0` | GNU Lesser GPL v3.0 | WEAK_COPYLEFT | ✓ | ✓ | ✓ |
| `MPL-2.0` | Mozilla Public License 2.0 | WEAK_COPYLEFT | ✓ | ✓ | ✓ |
| `GPL-2.0` | GNU General Public License v2.0 | STRONG_COPYLEFT | ✓ | ✓ | ✓ |
| `GPL-3.0` | GNU General Public License v3.0 | STRONG_COPYLEFT | ✓ | ✓ | ✓ |
| `AGPL-3.0` | GNU Affero GPL v3.0 | NETWORK_COPYLEFT | ✓ | ✓ | ✓ |
| `SSPL-1.0` | Server Side Public License v1 | NETWORK_COPYLEFT | ✗ | ✗ | ✗ |
| `Unlicense` | The Unlicense | PUBLIC_DOMAIN | ✓ | ✓ | ✓ |
| `CC0-1.0` | Creative Commons Zero v1.0 Universal | PUBLIC_DOMAIN | ✗ | ✓ | ✓ |

---

## Methods

### `__init__()`

```python
LicenseDatabase()
```

No arguments.  Constructs `LicenseInfo` objects from `_LICENSE_DATA` and stores them
in an internal `dict[str, LicenseInfo]` keyed by SPDX ID.

---

### `get(spdx_id)`

```python
def get(self, spdx_id: str) -> LicenseInfo | None
```

Exact-match lookup.  The key is **case-sensitive** — `"mit"` returns `None`, `"MIT"`
returns the full `LicenseInfo`.

```python
db = LicenseDatabase()

info = db.get("MIT")
assert info is not None
assert info.name == "MIT License"
assert info.osi_approved is True

missing = db.get("mit")   # wrong case
assert missing is None
```

---

### `normalize(raw_license)`

```python
def normalize(self, raw_license: str) -> str | None
```

Converts a free-form license string to a canonical SPDX ID.  The resolution order is:

1. Strip leading/trailing whitespace.
2. Try exact match against the SPDX key dictionary.
3. Lower-case the string, replace `-` and `_` with spaces, then look up in
   `_LICENSE_ALIASES`.
4. Try the original lower-cased string as-is in `_LICENSE_ALIASES`.
5. Return `None` if none of the above succeed.

```python
db = LicenseDatabase()

# Exact SPDX IDs pass through
assert db.normalize("MIT") == "MIT"
assert db.normalize("Apache-2.0") == "Apache-2.0"

# Aliases are resolved case-insensitively
assert db.normalize("Apache License, Version 2.0") == "Apache-2.0"
assert db.normalize("  mit  ") == "MIT"   # whitespace stripped

# Unknown strings return None
assert db.normalize("Bespoke Proprietary 1.0") is None
```

!!! note "24 built-in aliases"
    The `_LICENSE_ALIASES` dictionary maps 24 common non-SPDX strings (such as
    `"apache 2.0"`, `"gplv3"`, `"public domain"`, `"cc0"`) to their canonical SPDX
    identifiers.  This covers the most frequent values emitted by `pip` metadata and
    PyPI classifiers.

---

### `resolve(raw_license)`

```python
def resolve(self, raw_license: str) -> LicenseInfo | None
```

Convenience method that calls `normalize()` then `get()` in one step.

```python
db = LicenseDatabase()

info = db.resolve("Apache License, Version 2.0")
assert info is not None
assert info.spdx_id == "Apache-2.0"
assert info.family.value == "permissive"
```

---

### `check_conflict(...)`

```python
def check_conflict(
    self,
    package_name: str,
    license_spdx: str,
    project_license: str | None = None,
    policy_allow: list[str] | None = None,
    policy_block: list[str] | None = None,
) -> LicenseConflict | None
```

Returns a `LicenseConflict` if a policy or inherent license property triggers a
conflict, otherwise `None`.

#### Priority order

Checks are evaluated in the following sequence — the first match wins:

1. **Block list** — if `policy_block` is set and `license_spdx` is in it, return
   `ConflictSeverity.ERROR`.
2. **Allow list** — if `policy_allow` is set and `license_spdx` is *not* in it, return
   `ConflictSeverity.ERROR`.
3. **SSPL guard** — if `license_spdx == "SSPL-1.0"`, return `ConflictSeverity.ERROR`.
   This check fires even when `SSPL-1.0` appears in the allow list, because SSPL is
   not OSI-approved and prohibits commercial cloud usage.
4. **Generic network-copyleft** — if the license family is `NETWORK_COPYLEFT` (e.g.
   `AGPL-3.0`), return `ConflictSeverity.WARNING` prompting a legal review.
5. **No conflict** — return `None`.

!!! warning "SSPL-1.0 bug fix"
    Prior to the current implementation, `SSPL-1.0` fell through to the generic
    network-copyleft branch and produced only a `WARNING`.  A dedicated guard (step 3
    above) now correctly produces an `ERROR` regardless of the allow list.  If you
    previously relied on `SSPL-1.0` generating a warning, update your policy to
    explicitly block it instead.

#### Examples

```python
from vigil_core.license_db import LicenseDatabase
from vigil_core.models import ConflictSeverity

db = LicenseDatabase()

# 1. Block list takes highest priority
c = db.check_conflict("my-lib", "GPL-3.0", policy_block=["GPL-3.0"])
assert c is not None
assert c.severity == ConflictSeverity.ERROR
assert "explicitly blocked" in c.reason

# 2. Not in allow list
c = db.check_conflict("my-lib", "MIT", policy_allow=["Apache-2.0"])
assert c.severity == ConflictSeverity.ERROR

# 3. SSPL is always an error — even if in the allow list
c = db.check_conflict("mongo-driver", "SSPL-1.0", policy_allow=["SSPL-1.0"])
assert c.severity == ConflictSeverity.ERROR

# 4. AGPL without any explicit policy → WARNING
c = db.check_conflict("my-saas-dep", "AGPL-3.0")
assert c.severity == ConflictSeverity.WARNING

# 5. Permissive license, no policy → no conflict
c = db.check_conflict("requests", "MIT")
assert c is None
```

---

### `all_spdx_ids()`

```python
def all_spdx_ids(self) -> list[str]
```

Returns the list of all SPDX IDs in the built-in database, in insertion order.

```python
db = LicenseDatabase()
ids = db.all_spdx_ids()

assert "MIT" in ids
assert len(ids) >= 14
assert len(ids) == len(set(ids))   # no duplicates
```

---

## Alias Reference

The 24 built-in entries in `_LICENSE_ALIASES` (keyed as lower-cased strings):

| Alias | Resolves to |
|---|---|
| `mit` | `MIT` |
| `apache 2` | `Apache-2.0` |
| `apache 2.0` | `Apache-2.0` |
| `apache software license` | `Apache-2.0` |
| `apache license, version 2.0` | `Apache-2.0` |
| `bsd` | `BSD-3-Clause` |
| `bsd license` | `BSD-3-Clause` |
| `new bsd license` | `BSD-3-Clause` |
| `simplified bsd` | `BSD-2-Clause` |
| `isc license` | `ISC` |
| `mozilla public license 2.0` | `MPL-2.0` |
| `gpl` | `GPL-3.0` |
| `gplv2` | `GPL-2.0` |
| `gplv3` | `GPL-3.0` |
| `gnu gpl v3` | `GPL-3.0` |
| `lgpl` | `LGPL-3.0` |
| `lgplv2` | `LGPL-2.1` |
| `lgplv3` | `LGPL-3.0` |
| `agpl` | `AGPL-3.0` |
| `agplv3` | `AGPL-3.0` |
| `public domain` | `Unlicense` |
| `cc0` | `CC0-1.0` |
| `psf` | `PSF-2.0` |
| `python software foundation license` | `PSF-2.0` |
