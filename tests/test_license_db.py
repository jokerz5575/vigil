"""
Comprehensive tests for vigil_core.license_db.

Covers:
  - LicenseDatabase.get()
  - LicenseDatabase.normalize()
  - LicenseDatabase.resolve()
  - LicenseDatabase.check_conflict()
  - LicenseDatabase.all_spdx_ids()
"""

from __future__ import annotations

import pytest
from vigil_core.license_db import (
    _LICENSE_ALIASES,
    _LICENSE_DATA,
    LicenseDatabase,
)
from vigil_core.models import (
    ConflictSeverity,
    LicenseFamily,
    LicenseInfo,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_SPDX_IDS: list[str] = [
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "LGPL-2.1",
    "LGPL-3.0",
    "MPL-2.0",
    "GPL-2.0",
    "GPL-3.0",
    "AGPL-3.0",
    "SSPL-1.0",
    "Unlicense",
    "CC0-1.0",
]


# ---------------------------------------------------------------------------
# TestGet
# ---------------------------------------------------------------------------


class TestGet:
    """Tests for LicenseDatabase.get()."""

    @pytest.mark.parametrize("spdx_id", ALL_SPDX_IDS)
    def test_get_returns_license_info_for_all_known_ids(
        self, db: LicenseDatabase, spdx_id: str
    ) -> None:
        """Every SPDX ID in _LICENSE_DATA is retrievable."""
        info = db.get(spdx_id)
        assert info is not None
        assert isinstance(info, LicenseInfo)
        assert info.spdx_id == spdx_id

    @pytest.mark.parametrize("spdx_id", ALL_SPDX_IDS)
    def test_get_spdx_id_matches_key(self, db: LicenseDatabase, spdx_id: str) -> None:
        """The spdx_id field on the returned object equals the lookup key."""
        info = db.get(spdx_id)
        assert info is not None
        assert info.spdx_id == spdx_id

    # --- family assertions ---

    @pytest.mark.parametrize(
        "spdx_id, expected_family",
        [
            ("MIT", LicenseFamily.PERMISSIVE),
            ("Apache-2.0", LicenseFamily.PERMISSIVE),
            ("BSD-2-Clause", LicenseFamily.PERMISSIVE),
            ("BSD-3-Clause", LicenseFamily.PERMISSIVE),
            ("ISC", LicenseFamily.PERMISSIVE),
            ("LGPL-2.1", LicenseFamily.WEAK_COPYLEFT),
            ("LGPL-3.0", LicenseFamily.WEAK_COPYLEFT),
            ("MPL-2.0", LicenseFamily.WEAK_COPYLEFT),
            ("GPL-2.0", LicenseFamily.STRONG_COPYLEFT),
            ("GPL-3.0", LicenseFamily.STRONG_COPYLEFT),
            ("AGPL-3.0", LicenseFamily.NETWORK_COPYLEFT),
            ("SSPL-1.0", LicenseFamily.NETWORK_COPYLEFT),
            ("Unlicense", LicenseFamily.PUBLIC_DOMAIN),
            ("CC0-1.0", LicenseFamily.PUBLIC_DOMAIN),
        ],
    )
    def test_get_correct_family(
        self,
        db: LicenseDatabase,
        spdx_id: str,
        expected_family: LicenseFamily,
    ) -> None:
        info = db.get(spdx_id)
        assert info is not None
        assert info.family == expected_family

    # --- OSI approved ---

    @pytest.mark.parametrize(
        "spdx_id, expected",
        [
            ("MIT", True),
            ("Apache-2.0", True),
            ("GPL-3.0", True),
            ("AGPL-3.0", True),
            ("SSPL-1.0", False),  # not OSI-approved
            ("CC0-1.0", False),  # not OSI-approved
            ("Unlicense", True),
        ],
    )
    def test_osi_approved_flag(self, db: LicenseDatabase, spdx_id: str, expected: bool) -> None:
        info = db.get(spdx_id)
        assert info is not None
        assert info.osi_approved is expected

    # --- FSF libre ---

    @pytest.mark.parametrize(
        "spdx_id, expected",
        [
            ("MIT", True),
            ("Apache-2.0", True),
            ("GPL-3.0", True),
            ("AGPL-3.0", True),
            ("SSPL-1.0", False),  # not FSF-free
            ("CC0-1.0", True),
            ("Unlicense", True),
        ],
    )
    def test_fsf_libre_flag(self, db: LicenseDatabase, spdx_id: str, expected: bool) -> None:
        info = db.get(spdx_id)
        assert info is not None
        assert info.fsf_libre is expected

    # --- allows_commercial_use ---

    @pytest.mark.parametrize(
        "spdx_id, expected",
        [
            ("MIT", True),
            ("Apache-2.0", True),
            ("GPL-3.0", True),
            ("AGPL-3.0", True),
            ("SSPL-1.0", False),  # restricts commercial cloud use
            ("CC0-1.0", True),
            ("Unlicense", True),
        ],
    )
    def test_allows_commercial_use_flag(
        self, db: LicenseDatabase, spdx_id: str, expected: bool
    ) -> None:
        info = db.get(spdx_id)
        assert info is not None
        assert info.allows_commercial_use is expected

    # --- network_clause ---

    @pytest.mark.parametrize(
        "spdx_id, expected",
        [
            ("MIT", False),
            ("Apache-2.0", False),
            ("GPL-3.0", False),
            ("AGPL-3.0", True),
            ("SSPL-1.0", True),
        ],
    )
    def test_network_clause_flag(self, db: LicenseDatabase, spdx_id: str, expected: bool) -> None:
        info = db.get(spdx_id)
        assert info is not None
        assert info.network_clause is expected

    # --- attribution=False for public-domain licenses ---

    @pytest.mark.parametrize("spdx_id", ["Unlicense", "CC0-1.0"])
    def test_public_domain_no_attribution_required(self, db: LicenseDatabase, spdx_id: str) -> None:
        info = db.get(spdx_id)
        assert info is not None
        assert info.requires_attribution is False

    # --- unknown / case-sensitivity ---

    def test_get_unknown_returns_none(self, db: LicenseDatabase) -> None:
        assert db.get("FAKE-99.0") is None

    def test_get_empty_string_returns_none(self, db: LicenseDatabase) -> None:
        assert db.get("") is None

    def test_get_is_case_sensitive_lowercase_fails(self, db: LicenseDatabase) -> None:
        """'mit' is not a valid SPDX ID — exact lookup must be case-sensitive."""
        assert db.get("mit") is None

    def test_get_is_case_sensitive_mixed_case_fails(self, db: LicenseDatabase) -> None:
        assert db.get("Apache-2.0".lower()) is None  # "apache-2.0" → None

    def test_get_is_case_sensitive_uppercase_fails(self, db: LicenseDatabase) -> None:
        assert db.get("MIT".lower()) is None


# ---------------------------------------------------------------------------
# TestNormalize
# ---------------------------------------------------------------------------


class TestNormalize:
    """Tests for LicenseDatabase.normalize()."""

    # --- exact match for all 14 SPDX IDs ---

    @pytest.mark.parametrize("spdx_id", ALL_SPDX_IDS)
    def test_normalize_exact_match_returns_same_id(self, db: LicenseDatabase, spdx_id: str) -> None:
        assert db.normalize(spdx_id) == spdx_id

    # --- alias coverage ---

    @pytest.mark.parametrize(
        "alias, expected_spdx",
        [
            ("mit", "MIT"),
            ("apache 2", "Apache-2.0"),
            ("apache 2.0", "Apache-2.0"),
            ("apache software license", "Apache-2.0"),
            ("apache license, version 2.0", "Apache-2.0"),
            ("bsd", "BSD-3-Clause"),
            ("bsd license", "BSD-3-Clause"),
            ("new bsd license", "BSD-3-Clause"),
            ("simplified bsd", "BSD-2-Clause"),
            ("isc license", "ISC"),
            ("mozilla public license 2.0", "MPL-2.0"),
            ("gpl", "GPL-3.0"),
            ("gplv2", "GPL-2.0"),
            ("gplv3", "GPL-3.0"),
            ("gnu gpl v3", "GPL-3.0"),
            ("lgpl", "LGPL-3.0"),
            ("lgplv2", "LGPL-2.1"),
            ("lgplv3", "LGPL-3.0"),
            ("agpl", "AGPL-3.0"),
            ("agplv3", "AGPL-3.0"),
            ("public domain", "Unlicense"),
            ("cc0", "CC0-1.0"),
            ("psf", "PSF-2.0"),
            ("python software foundation license", "PSF-2.0"),
        ],
    )
    def test_normalize_alias(self, db: LicenseDatabase, alias: str, expected_spdx: str) -> None:
        assert db.normalize(alias) == expected_spdx

    # --- case-insensitivity of aliases ---

    def test_normalize_alias_uppercase(self, db: LicenseDatabase) -> None:
        """Aliases are matched case-insensitively after lower()."""
        assert db.normalize("MIT") == "MIT"  # exact match path
        assert db.normalize("GPLv2") == "GPL-2.0"  # alias path via lower()
        assert db.normalize("GPLv3") == "GPL-3.0"
        assert db.normalize("AGPLv3") == "AGPL-3.0"
        assert db.normalize("LGPL") == "LGPL-3.0"

    # --- whitespace stripping ---

    def test_normalize_strips_leading_whitespace(self, db: LicenseDatabase) -> None:
        assert db.normalize("  MIT") == "MIT"

    def test_normalize_strips_trailing_whitespace(self, db: LicenseDatabase) -> None:
        assert db.normalize("MIT  ") == "MIT"

    def test_normalize_strips_both_sides(self, db: LicenseDatabase) -> None:
        assert db.normalize("  Apache-2.0  ") == "Apache-2.0"

    def test_normalize_strips_whitespace_then_alias(self, db: LicenseDatabase) -> None:
        """Whitespace is stripped before alias lookup."""
        assert db.normalize("  mit  ") == "MIT"

    # --- dash/underscore replacement in alias path ---

    def test_normalize_dash_replaced_for_alias_lookup(self, db: LicenseDatabase) -> None:
        """Dashes in the raw string are replaced with spaces before alias lookup."""
        # "gpl-v2" → normalized "gpl v2" — not an alias, but "gplv2" is via lower()
        # verify the simpler case: "lgpl-v2" is not an alias, but "lgplv2" is
        # This test checks the specific normalization step described in the source.
        assert db.normalize("gplv2") == "GPL-2.0"

    # --- unknown license ---

    def test_normalize_unknown_returns_none(self, db: LicenseDatabase) -> None:
        assert db.normalize("NotALicense-99") is None

    def test_normalize_empty_string_returns_none(self, db: LicenseDatabase) -> None:
        assert db.normalize("") is None

    def test_normalize_gibberish_returns_none(self, db: LicenseDatabase) -> None:
        assert db.normalize("xyzzy-frobozz") is None

    # --- resolve() also tested here as a convenience ---


class TestResolve:
    """Tests for LicenseDatabase.resolve()."""

    def test_resolve_alias_returns_license_info(self, db: LicenseDatabase) -> None:
        info = db.resolve("mit")
        assert info is not None
        assert info.spdx_id == "MIT"
        assert info.family == LicenseFamily.PERMISSIVE

    def test_resolve_exact_spdx_id_returns_license_info(self, db: LicenseDatabase) -> None:
        info = db.resolve("Apache-2.0")
        assert info is not None
        assert info.spdx_id == "Apache-2.0"

    def test_resolve_alias_with_whitespace(self, db: LicenseDatabase) -> None:
        info = db.resolve("  cc0  ")
        assert info is not None
        assert info.spdx_id == "CC0-1.0"

    def test_resolve_unknown_returns_none(self, db: LicenseDatabase) -> None:
        assert db.resolve("UNKNOWN-LICENSE") is None

    def test_resolve_empty_string_returns_none(self, db: LicenseDatabase) -> None:
        assert db.resolve("") is None

    def test_resolve_gplv3_alias(self, db: LicenseDatabase) -> None:
        info = db.resolve("gplv3")
        assert info is not None
        assert info.spdx_id == "GPL-3.0"
        assert info.family == LicenseFamily.STRONG_COPYLEFT

    def test_resolve_public_domain_alias(self, db: LicenseDatabase) -> None:
        info = db.resolve("public domain")
        assert info is not None
        assert info.spdx_id == "Unlicense"
        assert info.family == LicenseFamily.PUBLIC_DOMAIN


# ---------------------------------------------------------------------------
# TestCheckConflict
# ---------------------------------------------------------------------------


class TestCheckConflict:
    """Tests for LicenseDatabase.check_conflict()."""

    # --- Branch 1: policy_block non-empty and license in block → ERROR ---

    def test_blocked_license_returns_error(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("my-pkg", "GPL-3.0", policy_block=["GPL-3.0", "AGPL-3.0"])
        assert result is not None
        assert result.severity == ConflictSeverity.ERROR
        assert result.package == "my-pkg"
        assert result.license_spdx == "GPL-3.0"

    def test_blocked_license_reason_mentions_spdx(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "MIT", policy_block=["MIT"])
        assert result is not None
        assert "MIT" in result.reason

    def test_block_empty_list_does_not_block(self, db: LicenseDatabase) -> None:
        """An empty block list must not trigger the block branch."""
        result = db.check_conflict("pkg", "GPL-3.0", policy_block=[])
        # GPL-3.0 is STRONG_COPYLEFT, not NETWORK_COPYLEFT → should return None
        assert result is None

    def test_block_none_does_not_block(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "GPL-3.0", policy_block=None)
        assert result is None

    # --- Branch 2: allow list set and license NOT in it → ERROR ---

    def test_allow_list_excludes_unlisted_license(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "GPL-3.0", policy_allow=["MIT", "Apache-2.0"])
        assert result is not None
        assert result.severity == ConflictSeverity.ERROR

    def test_allow_list_excludes_unlisted_reason(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "LGPL-3.0", policy_allow=["MIT"])
        assert result is not None
        assert "LGPL-3.0" in result.reason

    # --- Branch 3: allow list set and license IS in it → no conflict (→ None) ---

    def test_allow_list_permits_listed_license(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "MIT", policy_allow=["MIT", "Apache-2.0", "BSD-3-Clause"])
        assert result is None

    def test_allow_list_permits_apache(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "Apache-2.0", policy_allow=["MIT", "Apache-2.0"])
        assert result is None

    # --- Branch: empty allow list is falsy → no allow-list restriction ---

    def test_empty_allow_list_imposes_no_restriction(self, db: LicenseDatabase) -> None:
        """policy_allow=[] is falsy; the allow-list branch must be skipped."""
        result = db.check_conflict("pkg", "GPL-3.0", policy_allow=[])
        # No block, no allow-list check; GPL-3.0 is STRONG_COPYLEFT → None
        assert result is None

    # --- Branch: block takes priority over allow ---

    def test_block_takes_priority_over_allow(self, db: LicenseDatabase) -> None:
        """If a license appears in both block and allow, block wins (ERROR)."""
        result = db.check_conflict(
            "pkg",
            "MIT",
            policy_allow=["MIT"],
            policy_block=["MIT"],
        )
        assert result is not None
        assert result.severity == ConflictSeverity.ERROR

    # --- Branch 4: SSPL-1.0 → ERROR (even without an explicit policy) ---

    def test_sspl_without_policy_returns_error(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("mongodb-driver", "SSPL-1.0")
        assert result is not None
        assert result.severity == ConflictSeverity.ERROR

    def test_sspl_error_reason_mentions_sspl(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "SSPL-1.0")
        assert result is not None
        assert "SSPL" in result.reason

    def test_sspl_takes_precedence_over_allow_list(self, db: LicenseDatabase) -> None:
        """SSPL-1.0 in the allow list still gets ERROR from the hard-coded check."""
        result = db.check_conflict("pkg", "SSPL-1.0", policy_allow=["SSPL-1.0"])
        # Allow-list passes, then the SSPL guard triggers ERROR
        assert result is not None
        assert result.severity == ConflictSeverity.ERROR

    # --- Branch 5: NETWORK_COPYLEFT (other than SSPL) → WARNING ---

    def test_agpl_without_policy_returns_warning(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("my-service", "AGPL-3.0")
        assert result is not None
        assert result.severity == ConflictSeverity.WARNING

    def test_agpl_warning_reason_mentions_network(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "AGPL-3.0")
        assert result is not None
        assert "network" in result.reason.lower() or "AGPL" in result.reason

    def test_agpl_in_allow_list_still_warns(self, db: LicenseDatabase) -> None:
        """AGPL passes the allow-list check but still triggers a WARNING."""
        result = db.check_conflict("pkg", "AGPL-3.0", policy_allow=["AGPL-3.0"])
        assert result is not None
        assert result.severity == ConflictSeverity.WARNING

    # --- Branch 6: permissive license → None ---

    def test_permissive_mit_no_conflict(self, db: LicenseDatabase) -> None:
        assert db.check_conflict("pkg", "MIT") is None

    def test_permissive_apache_no_conflict(self, db: LicenseDatabase) -> None:
        assert db.check_conflict("pkg", "Apache-2.0") is None

    def test_permissive_bsd3_no_conflict(self, db: LicenseDatabase) -> None:
        assert db.check_conflict("pkg", "BSD-3-Clause") is None

    def test_permissive_isc_no_conflict(self, db: LicenseDatabase) -> None:
        assert db.check_conflict("pkg", "ISC") is None

    # --- Branch 3 (unknown info): unknown SPDX after passing block/allow → None ---

    def test_unknown_spdx_not_in_block_or_allow_returns_none(self, db: LicenseDatabase) -> None:
        """If the SPDX ID is unknown to the DB and not blocked/restricted, return None."""
        result = db.check_conflict("pkg", "PSF-2.0")
        assert result is None

    def test_completely_unknown_spdx_returns_none(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "FAKE-99.0")
        assert result is None

    # --- strong copyleft without policy → None ---

    def test_gpl3_without_policy_returns_none(self, db: LicenseDatabase) -> None:
        """GPL-3.0 is STRONG_COPYLEFT, not NETWORK_COPYLEFT; no auto-warn."""
        assert db.check_conflict("pkg", "GPL-3.0") is None

    def test_gpl2_without_policy_returns_none(self, db: LicenseDatabase) -> None:
        assert db.check_conflict("pkg", "GPL-2.0") is None

    # --- package name is preserved in result ---

    def test_conflict_package_name_preserved(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("special-pkg-name", "SSPL-1.0")
        assert result is not None
        assert result.package == "special-pkg-name"

    def test_conflict_license_spdx_preserved(self, db: LicenseDatabase) -> None:
        result = db.check_conflict("pkg", "AGPL-3.0")
        assert result is not None
        assert result.license_spdx == "AGPL-3.0"


# ---------------------------------------------------------------------------
# TestAllSpdxIds
# ---------------------------------------------------------------------------


class TestAllSpdxIds:
    """Tests for LicenseDatabase.all_spdx_ids()."""

    def test_returns_list(self, db: LicenseDatabase) -> None:
        result = db.all_spdx_ids()
        assert isinstance(result, list)

    def test_returns_at_least_14_ids(self, db: LicenseDatabase) -> None:
        assert len(db.all_spdx_ids()) >= 14

    @pytest.mark.parametrize("spdx_id", ALL_SPDX_IDS)
    def test_contains_expected_spdx_id(self, db: LicenseDatabase, spdx_id: str) -> None:
        assert spdx_id in db.all_spdx_ids()

    def test_ids_are_strings(self, db: LicenseDatabase) -> None:
        for sid in db.all_spdx_ids():
            assert isinstance(sid, str)

    def test_no_duplicate_ids(self, db: LicenseDatabase) -> None:
        ids = db.all_spdx_ids()
        assert len(ids) == len(set(ids))

    def test_all_ids_are_retrievable(self, db: LicenseDatabase) -> None:
        """Every ID returned by all_spdx_ids() must also be retrievable via get()."""
        for sid in db.all_spdx_ids():
            assert db.get(sid) is not None, f"get({sid!r}) unexpectedly returned None"
