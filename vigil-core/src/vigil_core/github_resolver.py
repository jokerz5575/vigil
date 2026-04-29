"""
GitHubLicenseResolver
~~~~~~~~~~~~~~~~~~~~~
Falls back to the GitHub REST API when a package's license cannot be
determined from its PyPI metadata.

Algorithm
---------
1. Search GitHub for repositories matching the package name.
2. Score candidates (name similarity, star count, fork / archived penalties).
3. Reject candidates whose confidence score falls below ``min_confidence``.
4. For the winning repository, find the tag that best matches the package
   version so that the source URL points to the exact release, not just
   the default branch tip.
5. Fetch the license metadata at that ref via ``GET /repos/{owner}/{repo}/license``.
6. Return a :class:`GitHubLicenseResult` containing the SPDX ID **and** a
   version-specific permalink to the license file, e.g.
   ``https://github.com/psf/requests/blob/v2.31.0/LICENSE``.

Authentication
--------------
Unauthenticated requests are rate-limited to 10 searches / minute and
60 requests / hour.  Pass a GitHub personal-access token (or a
``GITHUB_TOKEN`` / ``VIGIL_GITHUB_TOKEN`` environment variable) to raise
those limits to 30 searches / minute and 5 000 requests / hour.

Usage::

    from vigil_core.github_resolver import GitHubLicenseResolver

    resolver = GitHubLicenseResolver(token="ghp_...")
    result = resolver.resolve("requests", "2.31.0")
    if result:
        print(result.spdx_id)      # "Apache-2.0"
        print(result.source_url)   # "https://github.com/psf/requests/blob/v2.31.0/LICENSE"
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from typing import Any, cast

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GitHubLicenseResult:
    """
    The outcome of a successful GitHub license lookup.

    Attributes:
        spdx_id:           SPDX identifier as returned by the GitHub API
                           (e.g. ``"Apache-2.0"``).
        license_name:      Human-readable license name
                           (e.g. ``"Apache License 2.0"``).
        source_url:        **Version-specific** permalink to the LICENSE file,
                           e.g. ``https://github.com/psf/requests/blob/v2.31.0/LICENSE``.
                           Falls back to the default-branch URL when no matching
                           release tag can be found.
        repo_url:          Canonical repository URL
                           (e.g. ``https://github.com/psf/requests``).
        ref:               The git ref used for the lookup (tag name or branch),
                           e.g. ``"v2.31.0"`` or ``"main"``.
        ref_is_version_tag: ``True`` when *ref* is a release tag that matches
                            the requested package version; ``False`` when the
                            lookup fell back to the default branch.
        confidence:        Repository-match confidence score in ``[0.0, 1.0]``.
    """

    spdx_id: str
    license_name: str
    source_url: str
    repo_url: str
    ref: str
    ref_is_version_tag: bool
    confidence: float


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


class GitHubLicenseResolver:
    """
    Resolves package licenses via the GitHub REST API.

    The resolver is safe to reuse across many packages — it maintains an
    in-process cache so that repeated lookups for the same
    ``(package, version)`` pair never trigger additional HTTP requests.
    Use it as a context manager (``with GitHubLicenseResolver() as r:``) to
    ensure the underlying connection pool is closed properly.
    """

    _GITHUB_API: str = "https://api.github.com"
    _DEFAULT_TIMEOUT: float = 10.0
    _DEFAULT_MIN_CONFIDENCE: float = 0.45

    def __init__(
        self,
        token: str | None = None,
        min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        """
        Args:
            token:          GitHub personal-access token.  Falls back to the
                            ``GITHUB_TOKEN`` or ``VIGIL_GITHUB_TOKEN``
                            environment variables when *None*.
            min_confidence: Minimum repository-match score (0–1) required
                            before a candidate is accepted.  Lower values
                            increase recall at the cost of precision.
            timeout:        HTTP request timeout in seconds.
        """
        resolved_token = (
            token or os.environ.get("GITHUB_TOKEN") or os.environ.get("VIGIL_GITHUB_TOKEN")
        )
        self._min_confidence = min_confidence
        # (package_name_lower, version) -> result | None
        self._cache: dict[tuple[str, str], GitHubLicenseResult | None] = {}

        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if resolved_token:
            headers["Authorization"] = f"Bearer {resolved_token}"
            logger.debug("GitHubLicenseResolver: authenticated (rate limit: 5 000 req/h)")
        else:
            logger.debug(
                "GitHubLicenseResolver: unauthenticated (rate limit: 60 req/h). "
                "Set GITHUB_TOKEN to raise the limit."
            )

        self._http = httpx.Client(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> GitHubLicenseResolver:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        package_name: str,
        version: str,
    ) -> GitHubLicenseResult | None:
        """
        Attempt to find the license for *package_name* at *version*.

        Returns a :class:`GitHubLicenseResult` when a high-confidence
        repository match is found **and** the repo exposes a recognized
        license file.  Returns ``None`` in all other cases (no match,
        low confidence, network error, rate limit, no license file).

        Results are cached in memory: repeated calls with the same
        ``(package_name, version)`` pair are free.
        """
        cache_key = (package_name.lower(), version)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._resolve(package_name, version)
        self._cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _resolve(
        self,
        package_name: str,
        version: str,
    ) -> GitHubLicenseResult | None:
        # Step 1 — find candidate repositories
        try:
            candidates = self._search_repos(package_name)
        except httpx.HTTPStatusError as exc:
            logger.debug(
                "GitHub search HTTP error for %r: %s %s",
                package_name,
                exc.response.status_code,
                exc.response.text[:200],
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("GitHub search failed for %r: %s", package_name, exc)
            return None

        if not candidates:
            logger.debug("No GitHub candidates found for %r", package_name)
            return None

        # Step 2 — score and pick the best candidate
        scored = sorted(
            ((self._score_candidate(c, package_name), c) for c in candidates),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best_repo = scored[0]

        if best_score < self._min_confidence:
            logger.debug(
                "Best GitHub candidate for %r scored %.2f (threshold %.2f) — skipping",
                package_name,
                best_score,
                self._min_confidence,
            )
            return None

        owner: str = best_repo["owner"]["login"]
        repo: str = best_repo["name"]
        default_branch: str = best_repo.get("default_branch", "main")

        logger.debug(
            "Selected repo %s/%s (score=%.2f) for %r@%s",
            owner,
            repo,
            best_score,
            package_name,
            version,
        )

        # Step 3 — find the tag that matches the requested version
        ref, is_version_tag = self._find_ref(owner, repo, version, default_branch)

        if is_version_tag:
            logger.debug("Resolved version tag %r for %r@%s", ref, package_name, version)
        else:
            logger.debug(
                "No version tag found for %r@%s — using default branch %r",
                package_name,
                version,
                ref,
            )

        # Step 4 — fetch license metadata at that ref
        try:
            license_payload = self._get_license(owner, repo, ref)
        except httpx.HTTPStatusError as exc:
            logger.debug(
                "GitHub license fetch HTTP error for %s/%s@%s: %s",
                owner,
                repo,
                ref,
                exc.response.status_code,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "GitHub license fetch failed for %s/%s@%s: %s",
                owner,
                repo,
                ref,
                exc,
            )
            return None

        if license_payload is None:
            logger.debug("No license file found in %s/%s@%s", owner, repo, ref)
            return None

        spdx_id: str = license_payload.get("license", {}).get("spdx_id", "") or ""
        if not spdx_id or spdx_id == "NOASSERTION":
            logger.debug(
                "GitHub repo %s/%s has no recognised SPDX ID (got %r)",
                owner,
                repo,
                spdx_id,
            )
            return None

        return GitHubLicenseResult(
            spdx_id=spdx_id,
            license_name=license_payload.get("license", {}).get("name", spdx_id),
            source_url=license_payload["html_url"],
            repo_url=f"https://github.com/{owner}/{repo}",
            ref=ref,
            ref_is_version_tag=is_version_tag,
            confidence=best_score,
        )

    # ------------------------------------------------------------------
    # GitHub API helpers
    # ------------------------------------------------------------------

    def _search_repos(self, package_name: str) -> list[dict[str, Any]]:
        """Return the top-10 GitHub repository candidates for *package_name*."""
        # Normalise separators so both "my-pkg" and "my_pkg" are searched
        query = package_name.replace("_", "-")
        resp = self._http.get(
            f"{self._GITHUB_API}/search/repositories",
            params={
                "q": f"{query} language:python",
                "sort": "stars",
                "order": "desc",
                "per_page": "10",
            },
        )
        if resp.status_code == 403:
            logger.warning(
                "GitHub API rate limit exceeded while searching for %r. "
                "Set GITHUB_TOKEN to increase the limit.",
                package_name,
            )
            return []
        resp.raise_for_status()
        return cast(list[dict[str, Any]], resp.json().get("items", []))

    def _get_tags(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Fetch up to 100 tags for *owner*/*repo*."""
        resp = self._http.get(
            f"{self._GITHUB_API}/repos/{owner}/{repo}/tags",
            params={"per_page": "100"},
        )
        resp.raise_for_status()
        return cast(list[dict[str, Any]], resp.json())

    def _get_license(
        self,
        owner: str,
        repo: str,
        ref: str,
    ) -> dict[str, Any] | None:
        """
        Fetch the license metadata for *owner*/*repo* at *ref*.

        Returns the parsed JSON payload or ``None`` if no license file exists
        (404) or the API rate limit is hit (403).
        """
        resp = self._http.get(
            f"{self._GITHUB_API}/repos/{owner}/{repo}/license",
            params={"ref": ref},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code == 403:
            logger.warning(
                "GitHub API rate limit exceeded while fetching license for %s/%s.",
                owner,
                repo,
            )
            return None
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        # Guard against repos that have a license field set to null
        if not data.get("license"):
            return None
        return data

    # ------------------------------------------------------------------
    # Scoring & tag-matching helpers
    # ------------------------------------------------------------------

    def _score_candidate(
        self,
        repo: dict[str, Any],
        package_name: str,
    ) -> float:
        """
        Return a confidence score in ``[0.0, 1.0]`` for how well *repo*
        matches *package_name*.

        The name match is the dominant signal; stars, fork status, and
        archived status are secondary adjustments.
        """
        pkg = package_name.lower()
        name = repo.get("name", "").lower()
        full_name = repo.get("full_name", "").lower()

        # --- Primary: name similarity ---
        if name == pkg:
            name_score = 1.0
        elif name in (pkg.replace("-", "_"), pkg.replace("_", "-")):
            name_score = 0.92
        elif name.startswith(pkg + "-") or name.startswith(pkg + "_"):
            name_score = 0.75
        elif name.endswith("-" + pkg) or name.endswith("_" + pkg):
            name_score = 0.65
        elif pkg in name:
            name_score = 0.55
        elif pkg.replace("-", "_") in name or pkg.replace("_", "-") in name:
            name_score = 0.50
        else:
            # No meaningful name overlap — discard immediately
            return 0.0

        # --- Secondary adjustments ---
        # Popularity: log-scaled bonus capped at +0.15
        stars: int = repo.get("stargazers_count", 0)
        popularity = min(0.15, math.log10(max(1, stars)) / 20.0)

        # Forks are usually not the canonical home of the project
        fork_penalty = -0.25 if repo.get("fork", False) else 0.0

        # Archived repos may have stale license info
        archived_penalty = -0.10 if repo.get("archived", False) else 0.0

        # Small bonus when the package name also appears in the owner name
        # (e.g. "requests" in "psf/requests" — owner is "psf", not a bonus here,
        # but "numpy" in "numpy/numpy" would score the bonus)
        owner_name = full_name.split("/")[0] if "/" in full_name else ""
        org_bonus = 0.05 if pkg in owner_name else 0.0

        raw = name_score + popularity + fork_penalty + archived_penalty + org_bonus
        return min(1.0, max(0.0, raw))

    def _find_ref(
        self,
        owner: str,
        repo: str,
        version: str,
        default_branch: str,
    ) -> tuple[str, bool]:
        """
        Return ``(ref, is_version_tag)`` for *version* in *owner*/*repo*.

        Tries a prioritised list of common tag naming conventions before
        falling back to *default_branch*.
        """
        # Common tag naming conventions, ordered by prevalence
        candidates = [
            f"v{version}",  # v2.31.0  ← most common
            version,  # 2.31.0
            f"v{version}.0",  # v2.31  → v2.31.0 (some projects add a patch segment)
            f"{version}.0",  # 2.31.0.0
            f"{repo}-{version}",  # requests-2.31.0
            f"{repo}-v{version}",  # requests-v2.31.0
            f"release-{version}",  # release-2.31.0
            f"release/{version}",  # release/2.31.0
            f"release/v{version}",  # release/v2.31.0
        ]

        try:
            tags = self._get_tags(owner, repo)
        except Exception:  # noqa: BLE001
            logger.debug(
                "Could not fetch tags for %s/%s — falling back to default branch",
                owner,
                repo,
            )
            return default_branch, False

        tag_name_set = {t["name"] for t in tags}
        for candidate in candidates:
            if candidate in tag_name_set:
                return candidate, True

        # No exact match found
        return default_branch, False
