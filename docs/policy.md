# Policy Reference

Vigil's compliance behaviour is driven entirely by a single YAML file — `vigil.yaml` — that
lives in your project root. You can version-control it, peer-review it, and reuse it across
repositories, making license compliance a first-class engineering artefact rather than an
afterthought.

---

## File Format

```yaml
# vigil.yaml
policy:
  # Permissive / public-domain licenses that are safe for most projects.
  # A package NOT on this list will fail if the allow list is non-empty.
  allow:
    - MIT
    - Apache-2.0

  # Weak / file-level copyleft. Triggers a warning but does NOT fail the check.
  warn:
    - LGPL-2.1-or-later
    - MPL-2.0

  # Strong / network copyleft and non-OSI licenses.
  # Any match immediately fails the compliance check (exit code 1).
  block:
    - GPL-3.0-or-later
    - AGPL-3.0-or-later
    - SSPL-1.0

  # Fail the check when a package's license cannot be identified at all.
  # Recommended: true for regulated or security-sensitive environments.
  fail_on_unknown: false
```

### Keys

| Key | Type | Required | Description |
|---|---|---|---|
| `policy.allow` | list of SPDX strings | No | Licenses approved for use. When this list is non-empty, any license **not** on it is treated as unknown and subject to `fail_on_unknown`. |
| `policy.warn` | list of SPDX strings | No | Licenses that generate a warning. Does not affect the exit code unless `--fail-on-warning` is passed. |
| `policy.block` | list of SPDX strings | No | Licenses that immediately fail the scan. Takes highest priority. |
| `policy.fail_on_unknown` | boolean | No (default `false`) | When `true`, any package whose license cannot be identified also fails the scan. Set to `true` in regulated environments where unidentified licenses are unacceptable. |

---

## Tier Priority Order

When Vigil evaluates a dependency it applies the tiers in this order:

```
block  >  warn  >  allow-list check
```

1. **block** — checked first. A match here immediately produces an error and fails the scan,
   regardless of what is in `allow` or `warn`.
2. **warn** — checked second. A match here produces a warning. The scan continues but the
   license will appear in the warnings summary.
3. **allow-list** — checked last. If the license is on the list the package passes cleanly.
   If the allow list is non-empty and the license is **not** on it, the outcome depends on
   `fail_on_unknown`.

!!! note
    **Warn overrides allow.** If a license appears in both `warn` and `allow`, the `warn` check
    fires first and the package is flagged with a warning. This is intentional: it lets you build
    a broad `allow` list for automation while still surfacing specific licenses that warrant human
    review. Do not add a license to both lists; add it only to `warn` if you want a warning.

---

## ALLOW — Permissive & Public Domain

These ~65 licenses are safe for virtually all commercial and open-source projects. No
attribution beyond the license text is required (except where noted), and there is no
copyleft obligation.

### Public Domain / No Rights Reserved

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `CC0-1.0` | Creative Commons Zero v1.0 Universal | ✅ | ✅ |
| `Unlicense` | The Unlicense | ✅ | ✅ |
| `0BSD` | Zero-Clause BSD | ✅ | — |

### MIT Family

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `MIT` | MIT License | ✅ | ✅ |
| `MIT-0` | MIT No Attribution | ✅ | — |
| `MIT-Modern-Variant` | MIT License (Modern Variant) | ✅ | — |

### Apache

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `Apache-2.0` | Apache License 2.0 | ✅ | ✅ |

### BSD Family

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `BSD-2-Clause` | BSD 2-Clause "Simplified" | ✅ | ✅ |
| `BSD-3-Clause` | BSD 3-Clause "New" or "Revised" | ✅ | ✅ |
| `BSD-4-Clause` | BSD 4-Clause "Original" | — | ✅ |
| `BSD-4-Clause-UC` | BSD 4-Clause (University of California-Specific) | — | — |
| `BSD-2-Clause-Patent` | BSD-2-Clause Plus Patent Exception | ✅ | — |
| `BSD-3-Clause-LBNL` | Lawrence Berkeley National Labs BSD variant | ✅ | — |
| `BSD-3-Clause-Open-MPI` | BSD 3-Clause Open MPI variant | — | — |

### ISC / NCSA

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `ISC` | ISC License | ✅ | ✅ |
| `NCSA` | University of Illinois / NCSA Open Source License | ✅ | ✅ |

### Python Ecosystem

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `PSF-2.0` | Python Software Foundation License 2.0 | ✅ | ✅ |
| `Python-2.0` | Python License 2.0 | ✅ | ✅ |
| `CNRI-Python` | CNRI portion of the Python License | ✅ | — |

### Boost / C++

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `BSL-1.0` | Boost Software License 1.0 | ✅ | ✅ |

### Academic / Research

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `AFL-3.0` | Academic Free License v3.0 | ✅ | ✅ |
| `AFL-2.1` | Academic Free License v2.1 | ✅ | ✅ |

### Artistic / Perl

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `Artistic-2.0` | Artistic License 2.0 | ✅ | ✅ |

### Microsoft

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `MS-PL` | Microsoft Public License | ✅ | — |

### Oracle

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `UPL-1.0` | Oracle Universal Permissive License v1.0 | ✅ | — |

### Web / Networking

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `W3C` | W3C Software Notice and License | ✅ | ✅ |
| `Xnet` | X.Net License | ✅ | — |
| `curl` | curl License | — | — |

### X / X11 Family

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `X11` | X11 License (also known as MIT/X11) | — | ✅ |
| `XFree86-1.1` | XFree86 License 1.1 | — | — |
| `xpp` | XPP License | — | — |

### System Libraries

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `PostgreSQL` | PostgreSQL License | ✅ | — |
| `NTP` | NTP License | ✅ | — |
| `HPND` | Historical Permission Notice and Disclaimer | ✅ | — |
| `Libpng` | libpng License | — | — |
| `libtiff` | libtiff License | — | — |
| `IJG` | Independent JPEG Group License | — | — |
| `FTL` | Freetype Project License | — | — |

### Language Runtimes

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `Intel` | Intel Open Source License | ✅ | — |
| `PHP-3.0` | PHP License v3.0 | ✅ | — |
| `PHP-3.01` | PHP License v3.01 | ✅ | — |
| `Zend-2.0` | Zend Engine License v2.0 | — | — |
| `TCL` | TCL/TK License | — | — |

### Compression

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `Zlib` | zlib License (also known as zlib/libpng) | ✅ | ✅ |
| `zlib-acknowledgement` | zlib/libpng License with Acknowledgement | — | — |

### Zope / Python Web

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `ZPL-2.0` | Zope Public License 2.0 | ✅ | ✅ |
| `ZPL-2.1` | Zope Public License 2.1 | ✅ | — |

### Chinese Open Source

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `MulanPSL-2.0` | Mulan Permissive Software License 2.0 | ✅ | — |

### Miscellaneous OSI-Approved

| SPDX ID | Full Name | OSI | FSF |
|---|---|---|---|
| `WTFPL` | Do What The F\*ck You Want To Public License | — | ✅ |
| `EUDatagrid` | EU DataGrid Software License | ✅ | — |
| `Entessa` | Entessa Public License v1.0 | ✅ | — |
| `Naumen` | Naumen Public License | ✅ | — |
| `NBPL-1.0` | Net Boolean Public License v1 | — | — |
| `OSET-PL-2.1` | OSET Public License version 2.1 | ✅ | — |
| `SimPL-2.0` | Simple Public License 2.0 | ✅ | — |
| `Stanfordsnprintf` | Stanford Secure Computing Group snprintf License | — | — |
| `TOSL` | Transitive Open Source License | — | — |
| `TU-Berlin-1.0` | Technische Universitaet Berlin License 1.0 | — | — |
| `TU-Berlin-2.0` | Technische Universitaet Berlin License 2.0 | — | — |
| `Vim` | Vim License | — | — |
| `VSL-1.0` | Vovida Software License v1.0 | ✅ | — |

---

## WARN — Weak / File-Level Copyleft

These ~35 licenses trigger a warning but do **not** fail the compliance check by default.
The typical rule: modifications to the licensed *file* must be shared back, but you can link
against the library freely without tainting the rest of your project. Review with legal counsel
before shipping in closed-source commercial products.

### GNU LGPL Family

| SPDX ID | Full Name | Notes |
|---|---|---|
| `LGPL-2.0-only` | GNU Lesser General Public License v2.0 only | Link freely; file modifications must be shared |
| `LGPL-2.0-or-later` | GNU LGPL v2.0 or any later version | Same as above, forward-compatible |
| `LGPL-2.1` | GNU LGPL v2.1 | Most common LGPL in the wild (e.g. glibc) |
| `LGPL-2.1-only` | GNU LGPL v2.1 only | Pinned to v2.1 |
| `LGPL-2.1-or-later` | GNU LGPL v2.1 or any later version | Allows upgrade to v3 |
| `LGPL-3.0` | GNU LGPL v3.0 | Adds patent retaliation clauses vs. v2.1 |
| `LGPL-3.0-only` | GNU LGPL v3.0 only | Pinned to v3.0 |
| `LGPL-3.0-or-later` | GNU LGPL v3.0 or any later version | Forward-compatible |

### Mozilla Public License

| SPDX ID | Full Name | Notes |
|---|---|---|
| `MPL-1.0` | Mozilla Public License 1.0 | File-level copyleft |
| `MPL-1.1` | Mozilla Public License 1.1 | Adds explicit patent grant |
| `MPL-2.0` | Mozilla Public License 2.0 | Compatible with Apache-2.0 |
| `MPL-2.0-no-copyleft-exception` | MPL 2.0 without Copyleft Exception | Stricter — cannot combine with GPL |

### Eclipse Public License

| SPDX ID | Full Name | Notes |
|---|---|---|
| `EPL-1.0` | Eclipse Public License 1.0 | Module-level copyleft |
| `EPL-2.0` | Eclipse Public License 2.0 | Adds secondary GPL compatibility |

### CDDL

| SPDX ID | Full Name | Notes |
|---|---|---|
| `CDDL-1.0` | Common Development and Distribution License 1.0 | File-level copyleft; GPL-incompatible |
| `CDDL-1.1` | Common Development and Distribution License 1.1 | Adds patent retaliation clause |

### EUPL

| SPDX ID | Full Name | Notes |
|---|---|---|
| `EUPL-1.0` | European Union Public License 1.0 | EU law copyleft |
| `EUPL-1.1` | European Union Public License 1.1 | Adds language-specific annexes |
| `EUPL-1.2` | European Union Public License 1.2 | Compatible with GPL-2.0+, AGPL-3.0+ |

### Apple

| SPDX ID | Full Name | Notes |
|---|---|---|
| `APSL-2.0` | Apple Public Source License 2.0 | Modifications must be disclosed |

### Common Public

| SPDX ID | Full Name | Notes |
|---|---|---|
| `CPAL-1.0` | Common Public Attribution License 1.0 | Attribution UI requirement |
| `CPL-1.0` | Common Public License 1.0 | Predecessor to EPL |

### LaTeX

| SPDX ID | Full Name | Notes |
|---|---|---|
| `LPPL-1.3c` | LaTeX Project Public License v1.3c | Renamed-file copyleft |
| `LPPL-1.3a` | LaTeX Project Public License v1.3a | Older LPPL variant |

### Reciprocal

| SPDX ID | Full Name | Notes |
|---|---|---|
| `RPL-1.1` | Reciprocal Public License 1.1 | Broad reciprocal obligations |
| `RPL-1.5` | Reciprocal Public License 1.5 | Stronger deployment trigger |
| `MS-RL` | Microsoft Reciprocal License | File-level copyleft |
| `Nokia` | Nokia Open Source License | Network-deploy trigger in some reads |

### Open Software License

| SPDX ID | Full Name | Notes |
|---|---|---|
| `OSL-1.0` | Open Software License 1.0 | Attribution + copyleft |
| `OSL-1.1` | Open Software License 1.1 | — |
| `OSL-2.0` | Open Software License 2.0 | — |
| `OSL-2.1` | Open Software License 2.1 | — |
| `OSL-3.0` | Open Software License 3.0 | Network-use trigger (review carefully) |

### Sun / Oracle Legacy

| SPDX ID | Full Name | Notes |
|---|---|---|
| `SPL-1.0` | Sun Public License v1.0 | Legacy; similar to MPL |
| `SISSL` | Sun Industry Standards Source License v1.1 | Standards-related copyleft |
| `LPL-1.0` | Lucent Public License v1.0 | Bell Labs / Lucent copyleft |
| `LPL-1.02` | Lucent Public License v1.02 | Minor revision |

### Other Weak Copyleft

| SPDX ID | Full Name | Notes |
|---|---|---|
| `EFL-2.0` | Eiffel Forum License v2.0 | — |
| `QPL-1.0` | Q Public License 1.0 | Modifications must be patches |
| `QPL-1.0-INRIA-2004` | Q Public License 1.0 INRIA 2004 variant | — |
| `CUA-OPL-1.0` | CUA Office Public License v1.0 | — |

### CeCILL

| SPDX ID | Full Name | Notes |
|---|---|---|
| `CECILL-2.1` | CeCILL Free Software License Agreement v2.1 | French-law GPL equivalent; OSI-approved |

### IBM

| SPDX ID | Full Name | Notes |
|---|---|---|
| `IPL-1.0` | IBM Public License v1.0 | Predecessor to CPL |
| `Interbase-1.0` | Interbase Public License v1.0 | Database library copyleft |

### Creative Commons Share-Alike

| SPDX ID | Full Name | Notes |
|---|---|---|
| `CC-BY-SA-3.0` | Creative Commons Attribution Share Alike 3.0 Unported | Not recommended for software; content copyleft |
| `CC-BY-SA-4.0` | Creative Commons Attribution Share Alike 4.0 International | Share-alike obligation on adapted works |

---

## BLOCK — Strong Copyleft / Non-OSI / Commercial Restrictions

Any dependency carrying one of these licenses will **immediately fail** the compliance check
(exit code 1). These licenses either require you to open-source your entire project, impose
network-use copyleft, restrict commercial use, or are not recognised as open source at all.

### GNU GPL Family

| SPDX ID | Full Name | Reason |
|---|---|---|
| `GPL-2.0` | GNU General Public License v2.0 | Strong copyleft — entire project must be GPL |
| `GPL-2.0-only` | GNU GPL v2.0 only | Strong copyleft (pinned) |
| `GPL-2.0-or-later` | GNU GPL v2.0 or any later version | Strong copyleft; implies v3 is also matched |
| `GPL-3.0` | GNU General Public License v3.0 | Strong copyleft + anti-tivoisation |
| `GPL-3.0-only` | GNU GPL v3.0 only | Strong copyleft (pinned) |
| `GPL-3.0-or-later` | GNU GPL v3.0 or any later version | Strong copyleft; forward-compatible |

### GNU AGPL Family (Network Copyleft)

| SPDX ID | Full Name | Reason |
|---|---|---|
| `AGPL-1.0` | GNU Affero General Public License v1.0 | Network copyleft — SaaS triggers source disclosure |
| `AGPL-1.0-only` | GNU AGPL v1.0 only | Network copyleft (pinned) |
| `AGPL-1.0-or-later` | GNU AGPL v1.0 or any later version | Network copyleft; forward-compatible |
| `AGPL-3.0` | GNU Affero General Public License v3.0 | Network copyleft — most common AGPL in modern OSS |
| `AGPL-3.0-only` | GNU AGPL v3.0 only | Network copyleft (pinned) |
| `AGPL-3.0-or-later` | GNU AGPL v3.0 or any later version | Network copyleft; forward-compatible |

### Server-Side / Cloud Copyleft (Non-OSI)

| SPDX ID | Full Name | Reason |
|---|---|---|
| `SSPL-1.0` | Server Side Public License v1.0 (MongoDB) | Non-OSI; entire service stack must be open-sourced |
| `BUSL-1.1` | Business Source License 1.1 (HashiCorp, MariaDB) | Non-OSI; converts to OSS after a delay — not OSI-approved |

### Strong Copyleft System Libraries

| SPDX ID | Full Name | Reason |
|---|---|---|
| `Sleepycat` | Sleepycat License (Berkeley DB) | GPL-equivalent; linking triggers whole-project copyleft |

### Non-Commercial Creative Commons

| SPDX ID | Full Name | Reason |
|---|---|---|
| `CC-BY-NC-1.0` | Creative Commons Attribution Non-Commercial 1.0 | Non-commercial restriction |
| `CC-BY-NC-2.0` | Creative Commons Attribution Non-Commercial 2.0 | Non-commercial restriction |
| `CC-BY-NC-2.5` | Creative Commons Attribution Non-Commercial 2.5 | Non-commercial restriction |
| `CC-BY-NC-3.0` | Creative Commons Attribution Non-Commercial 3.0 | Non-commercial restriction |
| `CC-BY-NC-4.0` | Creative Commons Attribution Non-Commercial 4.0 | Non-commercial restriction |
| `CC-BY-NC-ND-4.0` | CC Attribution Non-Commercial No-Derivatives 4.0 | Non-commercial + no-derivatives |
| `CC-BY-NC-SA-4.0` | CC Attribution Non-Commercial Share-Alike 4.0 | Non-commercial + share-alike |

### Proprietary / Unlicensed

| SPDX ID | Full Name | Reason |
|---|---|---|
| `Commons-Clause` | Commons Clause restriction | Not a standalone license; adds commercial restriction on top of OSS |
| `Proprietary` | Proprietary (catch-all) | No rights granted without a separate commercial agreement |
| `UNLICENSED` | Explicitly unlicensed | No rights granted at all; legally equivalent to "all rights reserved" |

---

## Custom Policy Example

Below is a minimal `vigil.yaml` suited to a **SaaS company** shipping a closed-source product.
It approves the most widely used permissive licenses, flags anything copyleft for review, and
blocks all GPL/AGPL variants and non-commercial content licenses.

```yaml
# vigil.yaml — SaaS company baseline policy
policy:
  allow:
    # Public domain
    - CC0-1.0
    - Unlicense
    - 0BSD
    # MIT / Apache / BSD core
    - MIT
    - MIT-0
    - Apache-2.0
    - BSD-2-Clause
    - BSD-3-Clause
    - ISC
    # Python ecosystem
    - PSF-2.0
    - Python-2.0
    # Boost / zlib / common system libs
    - BSL-1.0
    - Zlib
    - Libpng
    - FTL
    - HPND
    # Other broadly permissive
    - UPL-1.0
    - W3C
    - PostgreSQL
    - NTP
    - curl

  warn:
    # Weak copyleft — legal review required before shipping
    - LGPL-2.1
    - LGPL-2.1-only
    - LGPL-2.1-or-later
    - LGPL-3.0-only
    - LGPL-3.0-or-later
    - MPL-2.0
    - EPL-2.0

  block:
    # Strong copyleft
    - GPL-2.0-only
    - GPL-2.0-or-later
    - GPL-3.0-only
    - GPL-3.0-or-later
    # Network copyleft — SaaS triggers source disclosure
    - AGPL-3.0-only
    - AGPL-3.0-or-later
    - SSPL-1.0
    # Non-OSI / commercial restrictions
    - BUSL-1.1
    - Commons-Clause
    - Proprietary
    - UNLICENSED
    # Non-commercial CC (not suitable for software in production)
    - CC-BY-NC-4.0
    - CC-BY-NC-SA-4.0
    - CC-BY-NC-ND-4.0

  # Fail if a package's license cannot be determined at all
  fail_on_unknown: true
```

!!! tip
    Store this file at the root of your repository and reference it in your CI workflow with
    `vigil scan --policy vigil.yaml`. Combine it with `--fail-on-warning` to treat any LGPL
    or MPL dependency as a pipeline failure until legal approval is recorded.
