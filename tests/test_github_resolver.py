"""
Comprehensive tests for vigil_core.github_resolver.GitHubLicenseResolver.

All GitHub API interactions are fully mocked — no real HTTP requests are ever
made.  The preferred mocking strategy is:

* Patch ``vigil_core.github_resolver.httpx.Client`` at construction time so
  the ``__init__`` never opens a real connection pool.
* Then replace ``resolver._http`` with a :class:`unittest.mock.MagicMock`
  whose ``.get()`` side-effect routes responses by URL substring.

Test classes
------------
TestGitHubLicenseResult        – frozen dataclass contract
TestScoreCandidate             – _score_candidate() scoring rules
TestFindRef                    – _find_ref() tag-matching logic
TestResolveHappyPath           – full resolve() pipeline success paths
TestResolveEdgeCases           – error / edge-case paths (rate limits, 404, etc.)
TestCache                      – in-memory caching behaviour
TestContextManager             – context-manager protocol (__enter__ / __exit__)
TestPackageResolverIntegration – PackageResolver + GitHubLicenseResolver wiring
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from vigil_core.github_resolver import GitHubLicenseResolver, GitHubLicenseResult
from vigil_core.license_db import LicenseDatabase
from vigil_core.package_resolver import PackageResolver

# ---------------------------------------------------------------------------
# FrozenInstanceError compatibility shim (became a public symbol in 3.11)
# ---------------------------------------------------------------------------
try:
    from dataclasses import FrozenInstanceError  # type: ignore[attr-defined]
except ImportError:  # Python < 3.11
    FrozenInstanceError = AttributeError  # type: ignore[misc,assignment]


# ===========================================================================
# Payload builder helpers
# ===========================================================================


def _search_response(items: list) -> dict:
    """Build a fake /search/repositories response payload."""
    return {"items": items, "total_count": len(items)}


def _repo(
    name: str,
    owner: str = "testorg",
    stars: int = 1000,
    fork: bool = False,
    archived: bool = False,
    default_branch: str = "main",
) -> dict:
    """Build a minimal fake GitHub repository dict."""
    return {
        "name": name,
        "full_name": f"{owner}/{name}",
        "owner": {"login": owner},
        "stargazers_count": stars,
        "fork": fork,
        "archived": archived,
        "default_branch": default_branch,
    }


def _tags(*names: str) -> list:
    """Build a fake list of tag dicts."""
    return [{"name": n} for n in names]


def _license_payload(spdx_id: str, license_name: str, html_url: str) -> dict:
    """Build a fake /repos/{owner}/{repo}/license response payload."""
    return {
        "html_url": html_url,
        "license": {
            "spdx_id": spdx_id,
            "name": license_name,
            "key": spdx_id.lower(),
        },
    }


# ===========================================================================
# HTTP mock helpers
# ===========================================================================


def _mock_response(status_code: int = 200, json_data: object = None) -> MagicMock:
    """
    Build a mock that behaves like an ``httpx.Response``.

    * ``status_code`` is exposed as an attribute.
    * ``json()`` returns *json_data* (defaults to ``{}``).
    * ``raise_for_status()`` raises ``httpx.HTTPStatusError`` for 4xx/5xx codes,
      otherwise is a no-op.
    * ``text`` is set to an empty string (used in logging).
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = ""

    if status_code >= 400:
        http_err = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None

    return resp


def _make_http_mock(
    search_json: object = None,
    tags_json: object = None,
    license_json: object = None,
    search_status: int = 200,
    tags_status: int = 200,
    license_status: int = 200,
) -> MagicMock:
    """
    Return a mock ``_http`` client whose ``.get(url, **kwargs)`` method routes
    responses to the three GitHub endpoints by URL substring:

    * ``/search/repositories`` → search response
    * ``/tags``               → tags list
    * ``/license``            → license payload
    """

    def _get(url: str, **kwargs: object) -> MagicMock:
        if "/search/repositories" in url:
            return _mock_response(search_status, search_json)
        if "/tags" in url:
            return _mock_response(tags_status, tags_json)
        if "/license" in url:
            return _mock_response(license_status, license_json)
        return _mock_response(200, {})

    mock = MagicMock()
    mock.get.side_effect = _get
    return mock


# ===========================================================================
# Resolver factory — suppresses real httpx.Client construction
# ===========================================================================


def _make_resolver(min_confidence: float = 0.45) -> GitHubLicenseResolver:
    """
    Build a :class:`GitHubLicenseResolver` without opening a real HTTP
    connection pool.  The ``_http`` attribute is a :class:`MagicMock` and can
    be replaced per-test via ``resolver._http = _make_http_mock(...)``.
    """
    with patch("vigil_core.github_resolver.httpx.Client"):
        resolver = GitHubLicenseResolver(token="test-token", min_confidence=min_confidence)
    return resolver


# ===========================================================================
# Reusable fixtures / constants
# ===========================================================================

_REQUESTS_REPO = _repo("requests", owner="psf", stars=50_000, default_branch="main")
_MIT_SOURCE_URL = "https://github.com/psf/requests/blob/v2.31.0/LICENSE"
_MIT_PAYLOAD = _license_payload("MIT", "MIT License", _MIT_SOURCE_URL)


# ===========================================================================
# TestGitHubLicenseResult
# ===========================================================================


class TestGitHubLicenseResult:
    """Verify the frozen dataclass contract for GitHubLicenseResult."""

    def _make(self, **overrides: object) -> GitHubLicenseResult:
        defaults: dict = dict(
            spdx_id="MIT",
            license_name="MIT License",
            source_url="https://github.com/example/repo/blob/v1.0.0/LICENSE",
            repo_url="https://github.com/example/repo",
            ref="v1.0.0",
            ref_is_version_tag=True,
            confidence=0.95,
        )
        defaults.update(overrides)
        return GitHubLicenseResult(**defaults)  # type: ignore[arg-type]

    def test_is_frozen(self):
        """Assigning to any field must raise FrozenInstanceError."""
        result = self._make()
        with pytest.raises(FrozenInstanceError):
            result.spdx_id = "Apache-2.0"  # type: ignore[misc]

    def test_frozen_prevents_new_attribute(self):
        """Setting a brand-new attribute on the frozen instance must also raise."""
        result = self._make()
        with pytest.raises(FrozenInstanceError):
            result.extra_field = "oops"  # type: ignore[attr-defined]

    def test_fields(self):
        """All seven fields are stored correctly."""
        result = GitHubLicenseResult(
            spdx_id="Apache-2.0",
            license_name="Apache License 2.0",
            source_url="https://github.com/psf/requests/blob/v2.31.0/LICENSE",
            repo_url="https://github.com/psf/requests",
            ref="v2.31.0",
            ref_is_version_tag=True,
            confidence=0.98,
        )
        assert result.spdx_id == "Apache-2.0"
        assert result.license_name == "Apache License 2.0"
        assert result.source_url == "https://github.com/psf/requests/blob/v2.31.0/LICENSE"
        assert result.repo_url == "https://github.com/psf/requests"
        assert result.ref == "v2.31.0"
        assert result.ref_is_version_tag is True
        assert result.confidence == pytest.approx(0.98)

    def test_ref_is_version_tag_false(self):
        """ref_is_version_tag=False is preserved correctly."""
        result = self._make(ref="main", ref_is_version_tag=False)
        assert result.ref_is_version_tag is False

    def test_confidence_zero_is_valid(self):
        """A confidence of exactly 0.0 is stored without modification."""
        result = self._make(confidence=0.0)
        assert result.confidence == pytest.approx(0.0)


# ===========================================================================
# TestScoreCandidate
# ===========================================================================


class TestScoreCandidate:
    """
    Unit-tests for GitHubLicenseResolver._score_candidate().

    The HTTP client is never used by this method, so we construct the
    resolver once via the suppressed-httpx factory.
    """

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.r = _make_resolver()

    # ------------------------------------------------------------------ #
    # Name-similarity tiers
    # ------------------------------------------------------------------ #

    def test_exact_name_match_scores_highest(self):
        """pkg == name → base score 1.0; with popularity bonus it can hit the 1.0 cap."""
        repo = _repo("requests", stars=10_000)
        assert self.r._score_candidate(repo, "requests") >= 1.0

    def test_hyphen_underscore_variant(self):
        """my_pkg matches my-pkg as a hyphen/underscore variant (base 0.92)."""
        repo = _repo("my_pkg", stars=500)
        assert self.r._score_candidate(repo, "my-pkg") >= 0.9

    def test_underscore_hyphen_variant(self):
        """my-pkg matches my_pkg (reverse variant check)."""
        repo = _repo("my-pkg", stars=500)
        assert self.r._score_candidate(repo, "my_pkg") >= 0.9

    def test_prefix_match(self):
        """requests-mock starts with 'requests-' → base score 0.75, total > 0."""
        repo = _repo("requests-mock", stars=1000)
        score = self.r._score_candidate(repo, "requests")
        assert 0.0 < score < 1.0

    def test_suffix_match(self):
        """django-requests ends with '-requests' → base score 0.65, total > 0."""
        repo = _repo("django-requests", stars=500)
        score = self.r._score_candidate(repo, "requests")
        assert 0.0 < score < 1.0

    def test_substring_match(self):
        """myrequestslib contains 'requests' → base score 0.55, total > 0."""
        repo = _repo("myrequestslib", stars=200)
        score = self.r._score_candidate(repo, "requests")
        assert 0.0 < score < 1.0

    def test_no_name_overlap_returns_zero(self):
        """Flask has no overlap with 'requests'; score must be exactly 0.0."""
        repo = _repo("flask", stars=50_000)
        assert self.r._score_candidate(repo, "requests") == 0.0

    # ------------------------------------------------------------------ #
    # Secondary adjustments
    # ------------------------------------------------------------------ #

    def test_fork_is_penalised(self):
        """A forked repo with the same name should score lower than its non-fork twin."""
        non_fork = _repo("requests", stars=1000, fork=False)
        fork = _repo("requests", stars=1000, fork=True)
        assert self.r._score_candidate(fork, "requests") < self.r._score_candidate(
            non_fork, "requests"
        )

    def test_archived_is_penalised(self):
        """An archived repo should score lower than an active one with identical attributes.

        Use stars=0 so the popularity bonus is 0 and the 1.0 exact-name base score
        is NOT boosted further — archived gets 0.90 while active stays at 1.0.
        """
        active = _repo("requests", stars=0, archived=False)
        archived = _repo("requests", stars=0, archived=True)
        assert self.r._score_candidate(archived, "requests") < self.r._score_candidate(
            active, "requests"
        )

    def test_popular_repo_scores_higher(self):
        """A repo with 50 000 stars should outscore one with 1 star (all else equal).

        Use a prefix-match name ('requests-lib', base 0.75) so the raw scores
        are 0.90 vs 0.75 — both safely below the 1.0 cap.
        """
        popular = _repo("requests-lib", stars=50_000)
        obscure = _repo("requests-lib", stars=1)
        assert self.r._score_candidate(popular, "requests") > self.r._score_candidate(
            obscure, "requests"
        )

    def test_org_name_bonus(self):
        """When the package name appears in the owner slug, a +0.05 bonus is applied.

        Use a suffix-match name ('python-numpy', base 0.65) and stars=1 so the
        raw scores are 0.70 (with bonus) vs 0.65 (without) — both below the cap.
        """
        with_bonus = _repo("python-numpy", owner="numpy", stars=1)
        without_bonus = _repo("python-numpy", owner="someorg", stars=1)
        assert self.r._score_candidate(with_bonus, "numpy") > self.r._score_candidate(
            without_bonus, "numpy"
        )

    def test_score_capped_at_one(self):
        """Even with every possible bonus the score must never exceed 1.0."""
        repo = _repo("numpy", owner="numpy", stars=1_000_000)
        assert self.r._score_candidate(repo, "numpy") <= 1.0

    def test_score_never_negative(self):
        """Fork + archived + zero stars must not produce a negative score."""
        repo = _repo("requests", stars=0, fork=True, archived=True)
        assert self.r._score_candidate(repo, "requests") >= 0.0

    def test_fork_and_archived_penalties_are_independent(self):
        """Both fork and archived penalties apply simultaneously."""
        fork_only = _repo("requests", stars=1000, fork=True, archived=False)
        both = _repo("requests", stars=1000, fork=True, archived=True)
        assert self.r._score_candidate(both, "requests") < self.r._score_candidate(
            fork_only, "requests"
        )

    def test_exact_match_beats_prefix_match(self):
        """The 'requests' repo itself should score higher than 'requests-mock'."""
        exact = _repo("requests", stars=1000)
        prefix = _repo("requests-mock", stars=1000)
        assert self.r._score_candidate(exact, "requests") > self.r._score_candidate(
            prefix, "requests"
        )

    def test_case_insensitive_pkg_name(self):
        """Package name is lower-cased before comparison; 'Requests' == 'requests'."""
        repo = _repo("requests", stars=1000)
        score_lower = self.r._score_candidate(repo, "requests")
        score_upper = self.r._score_candidate(repo, "Requests")
        assert score_lower == pytest.approx(score_upper)


# ===========================================================================
# TestFindRef
# ===========================================================================


class TestFindRef:
    """
    Unit-tests for GitHubLicenseResolver._find_ref().

    ``_get_tags`` is patched on the resolver instance so no HTTP calls are made.
    """

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.r = _make_resolver()

    def _set_tags(self, *names: str) -> None:
        """Replace _get_tags with a mock that returns the given tag names."""
        self.r._get_tags = MagicMock(return_value=_tags(*names))

    # ------------------------------------------------------------------ #
    # Tag-naming conventions
    # ------------------------------------------------------------------ #

    def test_v_prefix_tag_found(self):
        self._set_tags("v2.31.0", "v2.30.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "v2.31.0"
        assert is_tag is True

    def test_bare_version_tag_found(self):
        self._set_tags("2.31.0", "2.30.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "2.31.0"
        assert is_tag is True

    def test_repo_prefixed_tag(self):
        self._set_tags("requests-2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "requests-2.31.0"
        assert is_tag is True

    def test_repo_v_prefixed_tag(self):
        self._set_tags("requests-v2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "requests-v2.31.0"
        assert is_tag is True

    def test_release_hyphen_tag(self):
        self._set_tags("release-2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "release-2.31.0"
        assert is_tag is True

    def test_release_slash_tag(self):
        self._set_tags("release/v2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "release/v2.31.0"
        assert is_tag is True

    def test_release_slash_bare_tag(self):
        self._set_tags("release/2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "release/2.31.0"
        assert is_tag is True

    def test_patch_extended_tag(self):
        """v{ver}.0 convention (e.g. 'v2.31.0.0') is tried when the bare version is missing."""
        self._set_tags("v2.31.0.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "v2.31.0.0"
        assert is_tag is True

    # ------------------------------------------------------------------ #
    # Fall-back behaviour
    # ------------------------------------------------------------------ #

    def test_no_matching_tag_falls_back_to_default_branch(self):
        self._set_tags("v1.0.0", "v0.9.0")  # no match for 2.31.0
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "main"
        assert is_tag is False

    def test_empty_tag_list_falls_back_to_default_branch(self):
        self._set_tags()  # no tags at all
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "main"
        assert is_tag is False

    def test_tag_fetch_exception_falls_back(self):
        """A network error in _get_tags must NOT propagate to the caller."""
        self.r._get_tags = MagicMock(side_effect=RuntimeError("network refused"))
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "main"
        assert is_tag is False

    def test_tag_fetch_http_error_falls_back(self):
        """An httpx transport error in _get_tags must also be silently absorbed."""
        self.r._get_tags = MagicMock(side_effect=httpx.ConnectError("timed out"))
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "develop")
        assert ref == "develop"
        assert is_tag is False

    def test_custom_default_branch_used_when_no_match(self):
        """The caller-supplied default branch (not 'main') must be returned."""
        self._set_tags("v99.0.0")  # unrelated tag
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "develop")
        assert ref == "develop"
        assert is_tag is False

    # ------------------------------------------------------------------ #
    # Priority ordering
    # ------------------------------------------------------------------ #

    def test_priority_order_v_prefix_wins_over_bare(self):
        """v2.31.0 appears second in the tag list but must be preferred over 2.31.0."""
        self._set_tags("2.31.0", "v2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "v2.31.0"
        assert is_tag is True

    def test_priority_order_v_prefix_beats_repo_prefix(self):
        """v2.31.0 should win over requests-2.31.0 (earlier in candidate list)."""
        self._set_tags("requests-2.31.0", "v2.31.0")
        ref, is_tag = self.r._find_ref("psf", "requests", "2.31.0", "main")
        assert ref == "v2.31.0"
        assert is_tag is True


# ===========================================================================
# TestResolveHappyPath
# ===========================================================================


class TestResolveHappyPath:
    """
    Full end-to-end happy-path tests for :meth:`GitHubLicenseResolver.resolve`.

    Each test wires a routed HTTP mock onto ``resolver._http`` and verifies the
    returned :class:`GitHubLicenseResult` fields.
    """

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.r = _make_resolver()

    def _wire(
        self,
        search_items: list,
        tag_names: list[str],
        lic_payload: dict,
        **kwargs: object,
    ) -> None:
        self.r._http = _make_http_mock(
            search_json=_search_response(search_items),
            tags_json=_tags(*tag_names),
            license_json=lic_payload,
            **kwargs,  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------------ #
    # Core result fields
    # ------------------------------------------------------------------ #

    def test_returns_result_with_version_tag(self):
        """Full happy path: search → tag found → license MIT → valid result."""
        self._wire([_REQUESTS_REPO], ["v2.31.0", "v2.30.0"], _MIT_PAYLOAD)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        assert result.spdx_id == "MIT"
        assert result.ref == "v2.31.0"
        assert result.ref_is_version_tag is True
        assert "/blob/v2.31.0/" in result.source_url

    def test_uses_default_branch_when_no_tag(self):
        """When no version tag matches, ref should be the default branch."""
        branch_payload = _license_payload(
            "MIT",
            "MIT License",
            "https://github.com/psf/requests/blob/main/LICENSE",
        )
        self._wire([_REQUESTS_REPO], ["v1.0.0"], branch_payload)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        assert result.ref == "main"
        assert result.ref_is_version_tag is False

    def test_source_url_is_version_specific(self):
        """source_url must be the html_url from the license API response."""
        self._wire([_REQUESTS_REPO], ["v2.31.0"], _MIT_PAYLOAD)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        assert result.source_url == _MIT_SOURCE_URL

    def test_repo_url_is_correct(self):
        """repo_url must be https://github.com/{owner}/{repo}."""
        self._wire([_REQUESTS_REPO], ["v2.31.0"], _MIT_PAYLOAD)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        assert result.repo_url == "https://github.com/psf/requests"

    def test_confidence_stored_in_result(self):
        """result.confidence must equal the score produced by _score_candidate."""
        self._wire([_REQUESTS_REPO], ["v2.31.0"], _MIT_PAYLOAD)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        expected = self.r._score_candidate(_REQUESTS_REPO, "requests")
        assert result.confidence == pytest.approx(expected)

    def test_license_name_stored_in_result(self):
        """license_name field must match the 'name' from the API payload."""
        payload = _license_payload(
            "Apache-2.0",
            "Apache License 2.0",
            "https://github.com/psf/requests/blob/v2.31.0/LICENSE",
        )
        self._wire([_REQUESTS_REPO], ["v2.31.0"], payload)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        assert result.spdx_id == "Apache-2.0"
        assert result.license_name == "Apache License 2.0"

    def test_returns_none_for_unresolvable_package(self):
        """A search returning zero items must yield None."""
        self._wire([], [], {})
        assert self.r.resolve("no-such-package", "1.0.0") is None

    def test_result_is_githuplicenseresult_instance(self):
        """The happy-path return value must be a GitHubLicenseResult."""
        self._wire([_REQUESTS_REPO], ["v2.31.0"], _MIT_PAYLOAD)
        result = self.r.resolve("requests", "2.31.0")
        assert isinstance(result, GitHubLicenseResult)

    def test_multiple_candidates_best_score_wins(self):
        """When multiple repos are returned, the highest-scoring one is used."""
        # 'requests' exact match beats 'requests-legacy' prefix match
        legacy = _repo("requests-legacy", owner="testorg", stars=50_000)
        self._wire([legacy, _REQUESTS_REPO], ["v2.31.0"], _MIT_PAYLOAD)
        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        # The winner must be the 'psf/requests' repo
        assert result.repo_url == "https://github.com/psf/requests"


# ===========================================================================
# TestResolveEdgeCases
# ===========================================================================


class TestResolveEdgeCases:
    """
    Error-path and edge-case tests.

    Covers rate limits, 404s, NOASSERTION, null license fields, network errors,
    and low-confidence matches.
    """

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.r = _make_resolver()

    def _wire(self, **kwargs: object) -> None:
        self.r._http = _make_http_mock(**kwargs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    # Empty / low-confidence search results
    # ------------------------------------------------------------------ #

    def test_no_candidates_returns_none(self):
        """An empty search result set must return None without raising."""
        self._wire(search_json=_search_response([]))
        assert self.r.resolve("requests", "2.31.0") is None

    def test_low_confidence_returns_none(self):
        """A candidate whose name has no overlap with the package name scores 0.0 < 0.45."""
        self._wire(
            search_json=_search_response([_repo("flask", stars=50_000)]),
            tags_json=_tags(),
            license_json=_license_payload(
                "MIT",
                "MIT License",
                "https://github.com/pallets/flask/blob/main/LICENSE",
            ),
        )
        assert self.r.resolve("requests", "2.31.0") is None

    def test_below_min_confidence_threshold_returns_none(self):
        """With min_confidence=0.9, an underscore-variant match (0.92 base) that
        gets fork-penalised to below 0.9 must still return None."""
        r = _make_resolver(min_confidence=0.99)
        r._http = _make_http_mock(
            search_json=_search_response([_repo("requests", stars=1, fork=True)]),
            tags_json=_tags("v1.0.0"),
            license_json=_MIT_PAYLOAD,
        )
        assert r.resolve("requests", "1.0.0") is None

    # ------------------------------------------------------------------ #
    # HTTP error codes
    # ------------------------------------------------------------------ #

    def test_rate_limit_on_search_returns_none(self):
        """A 403 from /search/repositories must cause resolve() to return None."""
        self._wire(search_status=403)
        assert self.r.resolve("requests", "2.31.0") is None

    def test_rate_limit_on_license_returns_none(self):
        """A 403 from the license endpoint must cause resolve() to return None."""
        self._wire(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_status=403,
        )
        assert self.r.resolve("requests", "2.31.0") is None

    def test_404_license_returns_none(self):
        """A 404 from the license endpoint (no LICENSE file) must return None."""
        self._wire(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_status=404,
        )
        assert self.r.resolve("requests", "2.31.0") is None

    def test_500_on_search_returns_none(self):
        """A 5xx server error on search must be absorbed and return None."""
        self._wire(search_status=500)
        assert self.r.resolve("requests", "2.31.0") is None

    # ------------------------------------------------------------------ #
    # Malformed / missing license data
    # ------------------------------------------------------------------ #

    def test_noassertion_spdx_returns_none(self):
        """NOASSERTION is treated as 'no recognised license' → None."""
        self._wire(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_json=_license_payload(
                "NOASSERTION",
                "Other",
                "https://github.com/psf/requests/blob/v2.31.0/LICENSE",
            ),
        )
        assert self.r.resolve("requests", "2.31.0") is None

    def test_empty_spdx_id_returns_none(self):
        """An empty SPDX ID string is equivalent to missing → None."""
        payload = {
            "html_url": "https://github.com/psf/requests/blob/v2.31.0/LICENSE",
            "license": {"spdx_id": "", "name": "Unknown", "key": "unknown"},
        }
        self._wire(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_json=payload,
        )
        assert self.r.resolve("requests", "2.31.0") is None

    def test_null_license_field_returns_none(self):
        """When the GitHub API returns ``"license": null`` the result must be None."""
        payload = {
            "html_url": "https://github.com/psf/requests/blob/main/LICENSE",
            "license": None,
        }
        self._wire(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_json=payload,
        )
        assert self.r.resolve("requests", "2.31.0") is None

    def test_missing_license_key_in_payload_returns_none(self):
        """If the payload has no 'license' key at all, result must be None."""
        payload = {"html_url": "https://github.com/psf/requests/blob/main/LICENSE"}
        self._wire(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_json=payload,
        )
        assert self.r.resolve("requests", "2.31.0") is None

    # ------------------------------------------------------------------ #
    # Network errors
    # ------------------------------------------------------------------ #

    def test_network_error_on_search_returns_none(self):
        """A ConnectError during /search/repositories must be absorbed → None."""
        mock_http = MagicMock()
        mock_http.get.side_effect = httpx.ConnectError("connection refused")
        self.r._http = mock_http
        assert self.r.resolve("requests", "2.31.0") is None

    def test_network_error_on_search_does_not_propagate(self):
        """Even an unexpected RuntimeError from _http.get must not reach the caller."""
        mock_http = MagicMock()
        mock_http.get.side_effect = RuntimeError("unexpected error")
        self.r._http = mock_http
        # Must return None without raising
        result = self.r.resolve("requests", "2.31.0")
        assert result is None

    def test_network_error_on_tags_falls_back_to_default_branch(self):
        """
        When _get_tags raises (network error), _find_ref falls back to the
        default branch.  resolve() must still succeed if the license fetch works.
        """
        branch_lic = _license_payload(
            "MIT",
            "MIT License",
            "https://github.com/psf/requests/blob/main/LICENSE",
        )

        def _get(url: str, **kwargs: object) -> MagicMock:
            if "/search/repositories" in url:
                return _mock_response(200, _search_response([_REQUESTS_REPO]))
            if "/tags" in url:
                raise httpx.ConnectError("timeout on tags")
            if "/license" in url:
                return _mock_response(200, branch_lic)
            return _mock_response(200, {})

        mock_http = MagicMock()
        mock_http.get.side_effect = _get
        self.r._http = mock_http

        result = self.r.resolve("requests", "2.31.0")
        assert result is not None
        assert result.ref == "main"
        assert result.ref_is_version_tag is False


# ===========================================================================
# TestCache
# ===========================================================================


class TestCache:
    """Verify the (package_name_lower, version) → result in-memory cache."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.r = _make_resolver()

    def _wire_success(self) -> None:
        self.r._http = _make_http_mock(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v2.31.0"),
            license_json=_MIT_PAYLOAD,
        )

    def _wire_failure(self) -> None:
        self.r._http = _make_http_mock(search_json=_search_response([]))

    # ------------------------------------------------------------------ #
    # Cache hit
    # ------------------------------------------------------------------ #

    def test_hit_returns_same_object(self):
        """A second call with the same key must return the identical object."""
        self._wire_success()
        result1 = self.r.resolve("requests", "2.31.0")
        call_count = self.r._http.get.call_count

        result2 = self.r.resolve("requests", "2.31.0")

        assert result1 is result2
        assert self.r._http.get.call_count == call_count  # no extra HTTP calls

    def test_none_result_is_cached(self):
        """A failed lookup (None) must be cached; the second call must not hit HTTP."""
        self._wire_failure()
        result1 = self.r.resolve("unknown-pkg-xyz", "1.0")
        assert result1 is None
        call_count = self.r._http.get.call_count

        result2 = self.r.resolve("unknown-pkg-xyz", "1.0")
        assert result2 is None
        assert self.r._http.get.call_count == call_count

    # ------------------------------------------------------------------ #
    # Cache key semantics
    # ------------------------------------------------------------------ #

    def test_cache_is_case_insensitive_on_package_name(self):
        """'Requests' and 'requests' must share the same cache entry."""
        self._wire_success()
        result_mixed = self.r.resolve("Requests", "2.31.0")
        call_count = self.r._http.get.call_count

        result_lower = self.r.resolve("requests", "2.31.0")

        # Served from cache — no additional HTTP traffic
        assert self.r._http.get.call_count == call_count
        assert result_mixed is result_lower

    def test_different_versions_are_different_cache_keys(self):
        """
        resolve("pkg", "1.0") and resolve("pkg", "2.0") are independent entries;
        both must trigger HTTP calls.
        """
        self.r._http = _make_http_mock(
            search_json=_search_response([_REQUESTS_REPO]),
            tags_json=_tags("v1.0.0", "v2.31.0"),
            license_json=_MIT_PAYLOAD,
        )
        result_v1 = self.r.resolve("requests", "1.0.0")
        count_after_v1 = self.r._http.get.call_count

        result_v2 = self.r.resolve("requests", "2.31.0")

        # Second version must have triggered additional HTTP calls
        assert self.r._http.get.call_count > count_after_v1
        assert result_v1 is not None
        assert result_v2 is not None
        # They are distinct objects in the cache
        assert result_v1 is not result_v2

    def test_different_packages_are_different_cache_keys(self):
        """
        resolve("numpy", "1.0") and resolve("requests", "1.0") are independent.
        """
        numpy_repo = _repo("numpy", owner="numpy", stars=30_000)
        numpy_payload = _license_payload(
            "BSD-3-Clause",
            "BSD 3-Clause",
            "https://github.com/numpy/numpy/blob/v1.0/LICENSE",
        )

        call_log: list[str] = []

        def _get(url: str, **kwargs: object) -> MagicMock:
            if "/search/repositories" in url:
                q = kwargs.get("params", {}).get("q", "")  # type: ignore[union-attr]
                if "numpy" in str(q):
                    call_log.append("numpy-search")
                    return _mock_response(200, _search_response([numpy_repo]))
                call_log.append("requests-search")
                return _mock_response(200, _search_response([_REQUESTS_REPO]))
            if "/tags" in url:
                return _mock_response(200, _tags("v1.0.0"))
            if "/license" in url:
                if "numpy" in url:
                    return _mock_response(200, numpy_payload)
                return _mock_response(200, _MIT_PAYLOAD)
            return _mock_response(200, {})

        mock_http = MagicMock()
        mock_http.get.side_effect = _get
        self.r._http = mock_http

        r_numpy = self.r.resolve("numpy", "1.0.0")
        r_requests = self.r.resolve("requests", "1.0.0")

        assert r_numpy is not None
        assert r_requests is not None
        assert r_numpy is not r_requests


# ===========================================================================
# TestContextManager
# ===========================================================================


class TestContextManager:
    """Verify that GitHubLicenseResolver honours the context-manager protocol."""

    def test_enter_returns_self(self):
        """__enter__ must return the resolver itself."""
        with patch("vigil_core.github_resolver.httpx.Client"):
            r = GitHubLicenseResolver(token="x")
        r._http = MagicMock()
        with r as ctx:
            assert ctx is r

    def test_close_called_on_exit(self):
        """_http.close() must be called when the ``with`` block exits normally."""
        with patch("vigil_core.github_resolver.httpx.Client"):
            r = GitHubLicenseResolver(token="x")
        mock_http = MagicMock()
        r._http = mock_http

        with r:
            pass

        mock_http.close.assert_called_once()

    def test_close_called_on_exception(self):
        """_http.close() must be called even when the ``with`` block raises."""
        with patch("vigil_core.github_resolver.httpx.Client"):
            r = GitHubLicenseResolver(token="x")
        mock_http = MagicMock()
        r._http = mock_http

        with pytest.raises(ValueError):
            with r:
                raise ValueError("boom inside context")

        mock_http.close.assert_called_once()

    def test_explicit_close_releases_http(self):
        """Calling close() directly must delegate to _http.close()."""
        with patch("vigil_core.github_resolver.httpx.Client"):
            r = GitHubLicenseResolver(token="x")
        mock_http = MagicMock()
        r._http = mock_http

        r.close()

        mock_http.close.assert_called_once()


# ===========================================================================
# TestPackageResolverIntegration
# ===========================================================================


class _FakeMeta:
    """
    Minimal stand-in for ``importlib.metadata.PackageMetadata``.

    Supports:
    * ``meta["Name"]`` / ``meta["Version"]``
    * ``meta.get("License")``
    * ``meta.get_all("Classifier")``
    """

    def __init__(
        self,
        name: str,
        version: str,
        license_field: str | None = None,
        classifiers: list[str] | None = None,
    ) -> None:
        self._data: dict[str, str] = {"Name": name, "Version": version}
        if license_field:
            self._data["License"] = license_field
        self._classifiers: list[str] = classifiers or []

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def get_all(self, key: str) -> list[str]:
        if key == "Classifier":
            return self._classifiers
        return []


def _make_dist(
    name: str,
    version: str,
    license_field: str | None = None,
    classifiers: list[str] | None = None,
) -> MagicMock:
    """Build a fake ``importlib.metadata.Distribution`` backed by ``_FakeMeta``."""
    dist = MagicMock()
    dist.metadata = _FakeMeta(name, version, license_field, classifiers)
    return dist


class TestPackageResolverIntegration:
    """
    Integration tests verifying the interaction between PackageResolver and a
    GitHubLicenseResolver stub.
    """

    def _github_mock(self, return_value: GitHubLicenseResult | None = None) -> MagicMock:
        gh = MagicMock()
        gh.resolve.return_value = return_value
        return gh

    # ------------------------------------------------------------------ #
    # Conditional invocation
    # ------------------------------------------------------------------ #

    def test_github_not_called_when_pypi_resolves(self):
        """PackageResolver must skip GitHub when PyPI metadata provides a license."""
        github = self._github_mock()
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("requests", "2.31.0", license_field="MIT")

        result = resolver._from_distribution(dist)

        assert result is not None
        github.resolve.assert_not_called()

    def test_github_not_called_when_classifier_resolves(self):
        """GitHub must also be skipped when a classifier yields a license."""
        github = self._github_mock()
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist(
            "requests",
            "2.31.0",
            classifiers=["License :: OSI Approved :: MIT License"],
        )

        result = resolver._from_distribution(dist)

        assert result is not None
        github.resolve.assert_not_called()

    def test_github_called_when_pypi_fails(self):
        """When PyPI metadata provides no license, GitHub resolver must be invoked."""
        github = self._github_mock(return_value=None)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("requests", "2.31.0")  # no license_field, no classifiers

        resolver._from_distribution(dist)

        github.resolve.assert_called_once_with("requests", "2.31.0")

    def test_github_not_invoked_when_resolver_is_none(self):
        """Default (no github_resolver) must not raise AttributeError."""
        resolver = PackageResolver(github_resolver=None)
        dist = _make_dist("requests", "2.31.0")
        dep = resolver._from_distribution(dist)
        # Must not raise; dep may be None or a DependencyInfo with no license
        assert dep is None or dep.license_spdx is None or isinstance(dep.license_spdx, str)

    # ------------------------------------------------------------------ #
    # Result propagation
    # ------------------------------------------------------------------ #

    def test_github_result_stored_in_dep_info(self):
        """A successful GitHub result must populate license fields correctly."""
        source_url = "https://github.com/psf/requests/blob/v2.31.0/LICENSE"
        gh_result = GitHubLicenseResult(
            spdx_id="MIT",
            license_name="MIT License",
            source_url=source_url,
            repo_url="https://github.com/psf/requests",
            ref="v2.31.0",
            ref_is_version_tag=True,
            confidence=0.97,
        )
        github = self._github_mock(return_value=gh_result)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("requests", "2.31.0")

        dep = resolver._from_distribution(dist)

        assert dep is not None
        assert dep.license_spdx == "MIT"
        assert dep.license_resolved_by == "github"
        assert dep.license_source_url == source_url

    def test_github_result_license_info_populated(self):
        """license_info must be populated when the SPDX ID is known to LicenseDatabase."""
        gh_result = GitHubLicenseResult(
            spdx_id="Apache-2.0",
            license_name="Apache License 2.0",
            source_url="https://github.com/psf/requests/blob/v2.31.0/LICENSE",
            repo_url="https://github.com/psf/requests",
            ref="v2.31.0",
            ref_is_version_tag=True,
            confidence=0.95,
        )
        github = self._github_mock(return_value=gh_result)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("requests", "2.31.0")

        dep = resolver._from_distribution(dist)

        assert dep is not None
        assert dep.license_info is not None
        assert dep.license_info.spdx_id == "Apache-2.0"

    def test_github_none_result_leaves_unknown(self):
        """When GitHub returns None the dependency must have no license_info."""
        github = self._github_mock(return_value=None)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("obscure-pkg-xyz", "0.1.0")

        dep = resolver._from_distribution(dist)

        assert dep is not None
        assert dep.license_info is None

    def test_github_none_result_license_resolved_by_is_none(self):
        """When GitHub returns None, license_resolved_by must not be set to 'github'."""
        github = self._github_mock(return_value=None)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("obscure-pkg-xyz", "0.1.0")

        dep = resolver._from_distribution(dist)

        assert dep is not None
        assert dep.license_resolved_by != "github"

    # ------------------------------------------------------------------ #
    # Branch fallback annotation
    # ------------------------------------------------------------------ #

    def test_github_result_with_branch_fallback_annotates_url(self):
        """
        When ref_is_version_tag=False (fell back to default branch), PackageResolver
        must annotate the source URL with ``[branch: <ref>, no version tag found]``.
        """
        source_url = "https://github.com/psf/requests/blob/main/LICENSE"
        gh_result = GitHubLicenseResult(
            spdx_id="MIT",
            license_name="MIT License",
            source_url=source_url,
            repo_url="https://github.com/psf/requests",
            ref="main",
            ref_is_version_tag=False,
            confidence=0.95,
        )
        github = self._github_mock(return_value=gh_result)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("requests", "2.31.0")

        dep = resolver._from_distribution(dist)

        assert dep is not None
        assert dep.license_resolved_by == "github"
        assert dep.license_source_url is not None
        assert "main" in dep.license_source_url
        assert "no version tag found" in dep.license_source_url

    def test_github_result_with_version_tag_url_not_annotated(self):
        """
        When ref_is_version_tag=True the source_url must be stored verbatim
        (no annotation appended).
        """
        source_url = "https://github.com/psf/requests/blob/v2.31.0/LICENSE"
        gh_result = GitHubLicenseResult(
            spdx_id="MIT",
            license_name="MIT License",
            source_url=source_url,
            repo_url="https://github.com/psf/requests",
            ref="v2.31.0",
            ref_is_version_tag=True,
            confidence=0.97,
        )
        github = self._github_mock(return_value=gh_result)
        resolver = PackageResolver(github_resolver=github)
        dist = _make_dist("requests", "2.31.0")

        dep = resolver._from_distribution(dist)

        assert dep is not None
        assert dep.license_source_url == source_url
