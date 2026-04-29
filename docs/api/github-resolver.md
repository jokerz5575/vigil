# `GitHubLicenseResolver`

**Module:** `vigil_core.github_resolver`
**Source:** `vigil-core/src/vigil_core/github_resolver.py`

The GitHub resolver is a fallback back-end that kicks in automatically
when a package's license cannot be determined from its PyPI metadata.
It searches GitHub for the canonical repository, finds the release tag
that matches the installed version, and reads the LICENSE file at that
exact ref — returning both the SPDX identifier **and** a version-specific
permalink to the license text.

---

## How it works

```
Package with unknown license
         │
         ▼
  Search GitHub API  GET /search/repositories?q={name}+language:python
         │
         ▼
  Score candidates   name similarity · stars · fork/archived penalties
         │
   score ≥ 0.45?  ──No──▶  return None
         │Yes
         ▼
  Find version tag   GET /repos/{owner}/{repo}/tags
  tries: v{ver}, {ver}, {repo}-{ver}, release/v{ver}, …
         │
   tag found? ──No──▶  use default branch (noted in source_url)
         │Yes
         ▼
  Fetch license      GET /repos/{owner}/{repo}/license?ref={tag}
         │
  SPDX present?  ──No──▶  return None
         │Yes
         ▼
  GitHubLicenseResult(spdx_id, source_url, …)
```

---

## `GitHubLicenseResult`

A **frozen dataclass** returned on every successful lookup.

```python
from vigil_core.github_resolver import GitHubLicenseResult
```

| Field | Type | Description |
|---|---|---|
| `spdx_id` | `str` | SPDX identifier, e.g. `"Apache-2.0"` |
| `license_name` | `str` | Full name, e.g. `"Apache License 2.0"` |
| `source_url` | `str` | **Version-specific** permalink to the LICENSE file, e.g. `https://github.com/psf/requests/blob/v2.31.0/LICENSE`. Falls back to the default-branch URL when no matching tag is found (with a note appended). |
| `repo_url` | `str` | `https://github.com/owner/repo` |
| `ref` | `str` | Git ref used, e.g. `"v2.31.0"` or `"main"` |
| `ref_is_version_tag` | `bool` | `True` when a release tag matching the version was found |
| `confidence` | `float` | Repository-match score in `[0.0, 1.0]` |

---

## `GitHubLicenseResolver`

```python
from vigil_core.github_resolver import GitHubLicenseResolver

resolver = GitHubLicenseResolver(token="ghp_...")
result = resolver.resolve("requests", "2.31.0")
if result:
    print(result.spdx_id)    # "Apache-2.0"
    print(result.source_url) # "https://github.com/psf/requests/blob/v2.31.0/LICENSE"
```

### Constructor

```python
GitHubLicenseResolver(
    token: str | None = None,
    min_confidence: float = 0.45,
    timeout: float = 10.0,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `token` | `str \| None` | `None` | GitHub personal-access token. Falls back to `GITHUB_TOKEN` or `VIGIL_GITHUB_TOKEN` env vars. Without a token, the API is limited to 60 requests/hour. |
| `min_confidence` | `float` | `0.45` | Minimum name-similarity score required before a candidate repository is accepted. Higher values improve precision at the cost of recall. |
| `timeout` | `float` | `10.0` | HTTP timeout in seconds for each individual API call. |

!!! tip "Getting a token"
    Go to [github.com/settings/tokens](https://github.com/settings/tokens) and
    create a **classic token** or a **fine-grained token** with no scopes — public
    repository read access is anonymous and does not require any permission grant.

---

### `resolve(package_name, version)`

```python
def resolve(self, package_name: str, version: str) -> GitHubLicenseResult | None
```

Attempt to resolve the license for `package_name` at `version`.

- Returns a `GitHubLicenseResult` on success.
- Returns `None` when: no matching repo found, confidence too low, rate
  limited, no license file in the repo, or any network error.
- Results are **cached in memory**: repeated calls for the same
  `(package_name, version)` pair never trigger additional HTTP requests.

---

### Context manager

The resolver wraps an `httpx.Client` connection pool.  Use it as a context
manager when you control the lifecycle:

```python
with GitHubLicenseResolver(token="ghp_...") as resolver:
    result = resolver.resolve("click", "8.1.7")
```

Or call `resolver.close()` manually when done.

---

## Repository scoring

The resolver scores each search result on a `[0.0, 1.0]` scale and rejects
candidates below `min_confidence`.

| Signal | Weight |
|---|---|
| Exact name match (`name == pkg`) | 1.0 base |
| Hyphen / underscore variant | 0.92 base |
| Name starts with `pkg-` or `pkg_` | 0.75 base |
| Name ends with `-pkg` or `_pkg` | 0.65 base |
| `pkg` appears anywhere in name | 0.55 base |
| Stars (log-scaled popularity bonus) | up to +0.15 |
| Fork | −0.25 |
| Archived | −0.10 |
| Package name in org/owner name | +0.05 |

!!! warning "Known precision limitation"
    Some packages have their canonical repo under a different name (e.g.
    `hatchling` lives in `pypa/hatch`).  When the correct repo scores below the
    threshold and a less-relevant but similarly-named repo scores above it, a
    false positive may result.

    **v1.1 fix:** cross-validate the matched repo URL against the package's PyPI
    `Home-page` / `Project-URL` metadata before accepting the match.

---

## Version tag detection

For a package at version `2.31.0`, the resolver tries these tag patterns
**in order** and takes the first match:

| Priority | Pattern | Example |
|---|---|---|
| 1 | `v{ver}` | `v2.31.0` ← most common |
| 2 | `{ver}` | `2.31.0` |
| 3 | `v{ver}.0` | `v2.31.0` |
| 4 | `{ver}.0` | `2.31.0.0` |
| 5 | `{repo}-{ver}` | `requests-2.31.0` |
| 6 | `{repo}-v{ver}` | `requests-v2.31.0` |
| 7 | `release-{ver}` | `release-2.31.0` |
| 8 | `release/{ver}` | `release/2.31.0` |
| 9 | `release/v{ver}` | `release/v2.31.0` |
| — | *(fallback)* | default branch (`main` / `master`) |

When the fallback is used, `result.ref_is_version_tag` is `False` and
the source URL includes a note: `…  [branch: main, no version tag found]`.

---

## Integration with `PackageResolver`

The resolver is injected into `PackageResolver` automatically by `LicenseScanner`
when a GitHub token is available.  You can also construct it manually:

```python
from vigil_core.github_resolver import GitHubLicenseResolver
from vigil_core.package_resolver import PackageResolver
from vigil_core.license_db import LicenseDatabase

gh = GitHubLicenseResolver(token="ghp_...")
resolver = PackageResolver(
    license_db=LicenseDatabase(),
    github_resolver=gh,
)
deps = resolver.resolve_installed()

for dep in deps:
    if dep.license_resolved_by == "github":
        print(f"{dep.name}: {dep.license_spdx} — {dep.license_source_url}")
```

---

## Rate limits

| Mode | Search limit | Other API calls |
|---|---|---|
| Unauthenticated | 10 / minute | 60 / hour |
| Authenticated (`GITHUB_TOKEN`) | 30 / minute | 5 000 / hour |

The resolver logs a `WARNING` when rate-limited and returns `None` for
affected packages — the rest of the scan continues uninterrupted.
