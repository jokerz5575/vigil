"""
Tests that validate the actual vigil/vigil.yaml policy file.

Covers:
- File existence and structure (valid YAML, required keys, correct types)
- Content correctness (required licenses present, no duplicates, disjoint sets)
- LicensePolicy.from_yaml integration (loads cleanly, correct allow/block/warn,
  conflict checks work correctly with the loaded policy)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from vigil_core.models import ConflictSeverity
from vigil_licenses.scanner import LicensePolicy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def policy_data(vigil_yaml_path: Path) -> dict:
    """Load vigil.yaml and return the full parsed dict."""
    with open(vigil_yaml_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# TestVigilYamlStructure
# ---------------------------------------------------------------------------


class TestVigilYamlStructure:
    """Validates the structural integrity of vigil.yaml."""

    def test_file_exists(self, vigil_yaml_path):
        assert vigil_yaml_path.exists(), f"vigil.yaml not found at {vigil_yaml_path}"

    def test_file_is_a_regular_file(self, vigil_yaml_path):
        assert vigil_yaml_path.is_file()

    def test_loads_as_non_none_dict(self, policy_data):
        assert policy_data is not None
        assert isinstance(policy_data, dict)

    def test_has_top_level_policy_key(self, policy_data):
        assert "policy" in policy_data, "Missing top-level 'policy' key in vigil.yaml"

    def test_policy_has_allow_key(self, policy_data):
        assert "allow" in policy_data["policy"]

    def test_policy_has_block_key(self, policy_data):
        assert "block" in policy_data["policy"]

    def test_policy_has_warn_key(self, policy_data):
        assert "warn" in policy_data["policy"]

    def test_allow_is_a_list(self, policy_data):
        assert isinstance(policy_data["policy"]["allow"], list)

    def test_block_is_a_list(self, policy_data):
        assert isinstance(policy_data["policy"]["block"], list)

    def test_warn_is_a_list(self, policy_data):
        assert isinstance(policy_data["policy"]["warn"], list)

    def test_allow_contains_only_strings(self, policy_data):
        for item in policy_data["policy"]["allow"]:
            assert isinstance(item, str), f"Non-string in allow list: {item!r}"

    def test_block_contains_only_strings(self, policy_data):
        for item in policy_data["policy"]["block"]:
            assert isinstance(item, str), f"Non-string in block list: {item!r}"

    def test_warn_contains_only_strings(self, policy_data):
        for item in policy_data["policy"]["warn"]:
            assert isinstance(item, str), f"Non-string in warn list: {item!r}"

    def test_fail_on_unknown_is_bool_when_present(self, policy_data):
        pol = policy_data["policy"]
        if "fail_on_unknown" in pol:
            assert isinstance(pol["fail_on_unknown"], bool), (
                f"fail_on_unknown must be a bool, got {type(pol['fail_on_unknown'])}"
            )

    def test_allow_list_is_non_empty(self, policy_data):
        assert len(policy_data["policy"]["allow"]) > 0

    def test_block_list_is_non_empty(self, policy_data):
        assert len(policy_data["policy"]["block"]) > 0

    def test_warn_list_is_non_empty(self, policy_data):
        assert len(policy_data["policy"]["warn"]) > 0


# ---------------------------------------------------------------------------
# TestVigilYamlContent
# ---------------------------------------------------------------------------


class TestVigilYamlContent:
    """Validates the specific license content of vigil.yaml."""

    # --- allow list: core permissive licenses --------------------------------

    def test_allow_contains_mit(self, policy_data):
        assert "MIT" in policy_data["policy"]["allow"]

    def test_allow_contains_apache_2_0(self, policy_data):
        assert "Apache-2.0" in policy_data["policy"]["allow"]

    def test_allow_contains_bsd_3_clause(self, policy_data):
        assert "BSD-3-Clause" in policy_data["policy"]["allow"]

    def test_allow_contains_isc(self, policy_data):
        assert "ISC" in policy_data["policy"]["allow"]

    def test_allow_contains_unlicense(self, policy_data):
        assert "Unlicense" in policy_data["policy"]["allow"]

    def test_allow_contains_cc0_1_0(self, policy_data):
        assert "CC0-1.0" in policy_data["policy"]["allow"]

    def test_allow_has_at_least_30_entries(self, policy_data):
        count = len(policy_data["policy"]["allow"])
        assert count >= 30, f"Expected ≥30 allow entries, got {count}"

    # --- block list: strong copyleft ----------------------------------------

    def test_block_contains_gpl_2_0(self, policy_data):
        assert "GPL-2.0" in policy_data["policy"]["block"]

    def test_block_contains_gpl_3_0(self, policy_data):
        assert "GPL-3.0" in policy_data["policy"]["block"]

    def test_block_contains_agpl_3_0(self, policy_data):
        assert "AGPL-3.0" in policy_data["policy"]["block"]

    def test_block_contains_sspl_1_0(self, policy_data):
        assert "SSPL-1.0" in policy_data["policy"]["block"]

    def test_block_contains_gpl_2_0_only(self, policy_data):
        assert "GPL-2.0-only" in policy_data["policy"]["block"]

    def test_block_contains_gpl_3_0_only(self, policy_data):
        assert "GPL-3.0-only" in policy_data["policy"]["block"]

    def test_block_contains_agpl_3_0_only(self, policy_data):
        assert "AGPL-3.0-only" in policy_data["policy"]["block"]

    # --- warn list: weak copyleft -------------------------------------------

    def test_warn_contains_lgpl_2_1(self, policy_data):
        assert "LGPL-2.1" in policy_data["policy"]["warn"]

    def test_warn_contains_lgpl_3_0(self, policy_data):
        assert "LGPL-3.0" in policy_data["policy"]["warn"]

    def test_warn_contains_mpl_2_0(self, policy_data):
        assert "MPL-2.0" in policy_data["policy"]["warn"]

    def test_warn_contains_epl(self, policy_data):
        warn = policy_data["policy"]["warn"]
        assert "EPL-1.0" in warn or "EPL-2.0" in warn, (
            "Expected at least EPL-1.0 or EPL-2.0 in warn list"
        )

    # --- no duplicates ------------------------------------------------------

    def test_allow_has_no_duplicates(self, policy_data):
        allow = policy_data["policy"]["allow"]
        assert len(allow) == len(set(allow)), (
            f"Duplicate entries in allow: {[x for x in allow if allow.count(x) > 1]}"
        )

    def test_block_has_no_duplicates(self, policy_data):
        block = policy_data["policy"]["block"]
        assert len(block) == len(set(block)), (
            f"Duplicate entries in block: {[x for x in block if block.count(x) > 1]}"
        )

    def test_warn_has_no_duplicates(self, policy_data):
        warn = policy_data["policy"]["warn"]
        assert len(warn) == len(set(warn)), (
            f"Duplicate entries in warn: {[x for x in warn if warn.count(x) > 1]}"
        )

    # --- disjoint sets ------------------------------------------------------

    def test_allow_and_block_are_disjoint(self, policy_data):
        allow = set(policy_data["policy"]["allow"])
        block = set(policy_data["policy"]["block"])
        overlap = allow & block
        assert not overlap, f"Licenses appear in both allow and block: {overlap}"

    def test_warn_and_block_are_disjoint(self, policy_data):
        warn = set(policy_data["policy"]["warn"])
        block = set(policy_data["policy"]["block"])
        overlap = warn & block
        assert not overlap, f"Licenses appear in both warn and block: {overlap}"

    def test_allow_and_warn_are_disjoint(self, policy_data):
        # A license cannot be simultaneously "allowed without comment" and "flagged for review".
        allow = set(policy_data["policy"]["allow"])
        warn = set(policy_data["policy"]["warn"])
        overlap = allow & warn
        assert not overlap, f"Licenses appear in both allow and warn: {overlap}"


# ---------------------------------------------------------------------------
# TestVigilYamlLoadedAsPolicy
# ---------------------------------------------------------------------------


class TestVigilYamlLoadedAsPolicy:
    """Tests that validate vigil.yaml loads correctly as a LicensePolicy."""

    def test_from_yaml_loads_without_error(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert policy is not None

    def test_loaded_policy_allow_has_at_least_30_items(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert policy.allow is not None
        assert len(policy.allow) >= 30

    def test_loaded_policy_allow_contains_mit(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert "MIT" in policy.allow

    def test_loaded_policy_allow_contains_apache(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert "Apache-2.0" in policy.allow

    def test_loaded_policy_block_contains_gpl_3_0(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert "GPL-3.0" in policy.block

    def test_loaded_policy_block_contains_agpl_3_0(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert "AGPL-3.0" in policy.block

    def test_loaded_policy_warn_contains_lgpl_2_1(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert "LGPL-2.1" in policy.warn

    def test_loaded_policy_warn_contains_mpl_2_0(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert "MPL-2.0" in policy.warn

    def test_loaded_policy_fail_on_unknown_is_false(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert policy.fail_on_unknown is False

    def test_check_conflict_gpl_blocked_returns_error(self, vigil_yaml_path, db):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        conflict = db.check_conflict(
            package_name="gpl-lib",
            license_spdx="GPL-3.0",
            policy_block=policy.block,
        )
        assert conflict is not None
        assert conflict.severity == ConflictSeverity.ERROR

    def test_check_conflict_gpl_blocked_package_name_preserved(self, vigil_yaml_path, db):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        conflict = db.check_conflict(
            package_name="gpl-lib",
            license_spdx="GPL-3.0",
            policy_block=policy.block,
        )
        assert conflict is not None
        assert conflict.package == "gpl-lib"

    def test_check_conflict_mit_allowed_returns_none(self, vigil_yaml_path, db):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        conflict = db.check_conflict(
            package_name="safe-lib",
            license_spdx="MIT",
            policy_allow=policy.allow,
        )
        assert conflict is None

    def test_check_conflict_apache_allowed_returns_none(self, vigil_yaml_path, db):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        conflict = db.check_conflict(
            package_name="apache-lib",
            license_spdx="Apache-2.0",
            policy_allow=policy.allow,
        )
        assert conflict is None

    def test_check_conflict_agpl_blocked_returns_error(self, vigil_yaml_path, db):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        conflict = db.check_conflict(
            package_name="agpl-lib",
            license_spdx="AGPL-3.0",
            policy_block=policy.block,
        )
        assert conflict is not None
        assert conflict.severity == ConflictSeverity.ERROR

    def test_loaded_policy_block_non_empty(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert len(policy.block) > 0

    def test_loaded_policy_warn_non_empty(self, vigil_yaml_path):
        policy = LicensePolicy.from_yaml(vigil_yaml_path)
        assert len(policy.warn) > 0
