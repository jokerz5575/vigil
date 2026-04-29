"""
Comprehensive tests for LicensePolicy and LicenseScanner.

Covers:
- Policy construction (defaults, from_dict, from_yaml)
- Mocked scanner: conflict detection, warn/allow/block precedence,
  unknown licenses, license_summary, direct/transitive counts, project_name
- Real-install scanner: smoke tests against the live Python environment
"""

from __future__ import annotations

from pathlib import Path

import pytest
from vigil_core.models import ConflictSeverity, LicenseFamily
from vigil_licenses.scanner import LicensePolicy, LicenseScanner

# ---------------------------------------------------------------------------
# TestLicensePolicy
# ---------------------------------------------------------------------------


class TestLicensePolicy:
    """Unit tests for LicensePolicy construction and loading."""

    # --- defaults -----------------------------------------------------------

    def test_defaults_allow_is_none(self):
        policy = LicensePolicy()
        assert policy.allow is None

    def test_defaults_block_is_empty_list(self):
        policy = LicensePolicy()
        assert policy.block == []

    def test_defaults_warn_is_empty_list(self):
        policy = LicensePolicy()
        assert policy.warn == []

    def test_defaults_fail_on_unknown_is_false(self):
        policy = LicensePolicy()
        assert policy.fail_on_unknown is False

    # --- from_dict (full) ---------------------------------------------------

    def test_from_dict_full_allow(self):
        data = {
            "policy": {
                "allow": ["MIT", "Apache-2.0"],
                "block": ["GPL-3.0"],
                "warn": ["LGPL-2.1"],
                "fail_on_unknown": True,
            }
        }
        policy = LicensePolicy.from_dict(data)
        assert policy.allow == ["MIT", "Apache-2.0"]

    def test_from_dict_full_block(self):
        data = {
            "policy": {
                "allow": ["MIT"],
                "block": ["GPL-3.0", "AGPL-3.0"],
                "warn": [],
                "fail_on_unknown": False,
            }
        }
        policy = LicensePolicy.from_dict(data)
        assert policy.block == ["GPL-3.0", "AGPL-3.0"]

    def test_from_dict_full_warn(self):
        data = {
            "policy": {
                "allow": ["MIT"],
                "block": [],
                "warn": ["LGPL-2.1", "MPL-2.0"],
                "fail_on_unknown": False,
            }
        }
        policy = LicensePolicy.from_dict(data)
        assert policy.warn == ["LGPL-2.1", "MPL-2.0"]

    def test_from_dict_full_fail_on_unknown_true(self):
        data = {"policy": {"allow": ["MIT"], "fail_on_unknown": True}}
        policy = LicensePolicy.from_dict(data)
        assert policy.fail_on_unknown is True

    # --- from_dict (minimal) ------------------------------------------------

    def test_from_dict_minimal_block_only(self):
        data = {"policy": {"block": ["GPL-3.0"]}}
        policy = LicensePolicy.from_dict(data)
        assert policy.allow is None
        assert policy.block == ["GPL-3.0"]
        assert policy.warn == []
        assert policy.fail_on_unknown is False

    def test_from_dict_minimal_empty_policy(self):
        data = {"policy": {}}
        policy = LicensePolicy.from_dict(data)
        assert policy.allow is None
        assert policy.block == []
        assert policy.warn == []

    # --- from_dict (flat — no "policy" wrapper) -----------------------------

    def test_from_dict_flat_allow(self):
        data = {"allow": ["MIT", "BSD-3-Clause"], "block": ["GPL-3.0"], "warn": ["MPL-2.0"]}
        policy = LicensePolicy.from_dict(data)
        assert policy.allow == ["MIT", "BSD-3-Clause"]

    def test_from_dict_flat_block(self):
        data = {"allow": ["MIT"], "block": ["AGPL-3.0"]}
        policy = LicensePolicy.from_dict(data)
        assert policy.block == ["AGPL-3.0"]

    def test_from_dict_flat_warn(self):
        data = {"warn": ["LGPL-2.1"]}
        policy = LicensePolicy.from_dict(data)
        assert policy.warn == ["LGPL-2.1"]

    def test_from_dict_missing_policy_key_uses_flat_fallback(self):
        data = {"allow": ["MIT"]}
        policy = LicensePolicy.from_dict(data)
        assert policy.allow == ["MIT"]

    # --- from_yaml ----------------------------------------------------------

    def test_from_yaml_loads_allow(self, tmp_yaml_policy):
        policy = LicensePolicy.from_yaml(tmp_yaml_policy)
        assert "MIT" in policy.allow
        assert "Apache-2.0" in policy.allow
        assert "BSD-3-Clause" in policy.allow

    def test_from_yaml_loads_block(self, tmp_yaml_policy):
        policy = LicensePolicy.from_yaml(tmp_yaml_policy)
        assert "GPL-3.0" in policy.block
        assert "AGPL-3.0" in policy.block

    def test_from_yaml_loads_warn(self, tmp_yaml_policy):
        policy = LicensePolicy.from_yaml(tmp_yaml_policy)
        assert "LGPL-2.1" in policy.warn
        assert "MPL-2.0" in policy.warn

    def test_from_yaml_loads_fail_on_unknown(self, tmp_yaml_policy):
        policy = LicensePolicy.from_yaml(tmp_yaml_policy)
        assert policy.fail_on_unknown is False

    def test_from_yaml_missing_file_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "does_not_exist.yaml"
        with pytest.raises(FileNotFoundError):
            LicensePolicy.from_yaml(missing)


# ---------------------------------------------------------------------------
# TestLicenseScannerMocked
# ---------------------------------------------------------------------------


class TestLicenseScannerMocked:
    """Tests for LicenseScanner using an injected mock resolver."""

    # --- clean scans --------------------------------------------------------

    def test_clean_scan_all_mit_no_conflicts(self, scanner_factory, dep_factory):
        deps = [
            dep_factory("lib-a", spdx="MIT"),
            dep_factory("lib-b", spdx="MIT"),
            dep_factory("lib-c", spdx="Apache-2.0"),
        ]
        scanner = scanner_factory(deps)
        report = scanner.scan()
        assert len(report.conflicts) == 0

    def test_empty_dep_list_zero_conflicts(self, scanner_factory):
        scanner = scanner_factory([])
        report = scanner.scan()
        assert report.total_dependencies == 0
        assert len(report.conflicts) == 0

    # --- blocked license ----------------------------------------------------

    def test_blocked_license_yields_error_conflict(
        self, scanner_factory, dep_factory, strict_policy
    ):
        dep = dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert len(report.conflicts) == 1
        assert report.conflicts[0].severity == ConflictSeverity.ERROR

    def test_blocked_license_conflict_has_correct_package(
        self, scanner_factory, dep_factory, strict_policy
    ):
        dep = dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert report.conflicts[0].package == "gpl-lib"

    def test_blocked_license_conflict_has_correct_spdx_id(
        self, scanner_factory, dep_factory, strict_policy
    ):
        dep = dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert report.conflicts[0].license_spdx == "GPL-3.0"

    # --- warn list ----------------------------------------------------------

    def test_warn_list_yields_warning_not_error(self, scanner_factory, dep_factory, strict_policy):
        # LGPL-2.1 is in strict_policy.warn
        dep = dep_factory("lgpl-lib", spdx="LGPL-2.1", family=LicenseFamily.WEAK_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert len(report.conflicts) == 1
        assert report.conflicts[0].severity == ConflictSeverity.WARNING

    def test_warn_list_conflict_has_correct_package(
        self, scanner_factory, dep_factory, strict_policy
    ):
        dep = dep_factory("lgpl-lib", spdx="LGPL-2.1", family=LicenseFamily.WEAK_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert report.conflicts[0].package == "lgpl-lib"

    # --- warn overrides allow check -----------------------------------------

    def test_warn_overrides_allow_missing_gives_warning_not_error(
        self, scanner_factory, dep_factory, strict_policy
    ):
        # strict_policy.warn includes LGPL-2.1 but LGPL-2.1 is NOT in strict_policy.allow.
        # The warn check in scan() fires BEFORE the allow-list check in check_conflict(),
        # so the result must be WARNING, not ERROR.
        dep = dep_factory("lgpl-lib", spdx="LGPL-2.1", family=LicenseFamily.WEAK_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert report.conflicts[0].severity == ConflictSeverity.WARNING

    def test_warn_check_runs_before_allow_check_no_error_produced(
        self, scanner_factory, dep_factory, strict_policy
    ):
        dep = dep_factory("mpl-lib", spdx="MPL-2.0", family=LicenseFamily.WEAK_COPYLEFT)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        # MPL-2.0 is in strict_policy.warn (not in allow); must be WARNING, not ERROR
        assert all(c.severity != ConflictSeverity.ERROR for c in report.conflicts)

    # --- allow list ---------------------------------------------------------

    def test_allow_list_permits_exact_match_no_conflict(
        self, scanner_factory, dep_factory, strict_policy
    ):
        dep = dep_factory("safe-lib", spdx="MIT")
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert len(report.conflicts) == 0

    def test_allow_list_blocks_unlisted_license_error(
        self, scanner_factory, dep_factory, strict_policy
    ):
        # PSF-2.0 is NOT in strict_policy.allow and NOT in strict_policy.warn or block.
        # check_conflict sees an allow list that doesn't include PSF-2.0 → ERROR.
        dep = dep_factory("psf-lib", spdx="PSF-2.0", family=LicenseFamily.PERMISSIVE)
        scanner = scanner_factory([dep], strict_policy)
        report = scanner.scan()
        assert len(report.conflicts) == 1
        assert report.conflicts[0].severity == ConflictSeverity.ERROR

    # --- unknown licenses ---------------------------------------------------

    def test_unknown_license_fail_on_unknown_false_no_conflict(self, scanner_factory, dep_factory):
        dep = dep_factory("mystery-lib")  # no spdx → license_info is None
        policy = LicensePolicy(fail_on_unknown=False)
        scanner = scanner_factory([dep], policy)
        report = scanner.scan()
        assert len(report.conflicts) == 0

    def test_unknown_license_fail_on_unknown_false_added_to_unknown_list(
        self, scanner_factory, dep_factory
    ):
        dep = dep_factory("mystery-lib")
        policy = LicensePolicy(fail_on_unknown=False)
        scanner = scanner_factory([dep], policy)
        report = scanner.scan()
        assert len(report.unknown_licenses) == 1
        assert "mystery-lib" in report.unknown_licenses[0]

    def test_unknown_license_fail_on_unknown_true_yields_error(self, scanner_factory, dep_factory):
        dep = dep_factory("mystery-lib")
        policy = LicensePolicy(fail_on_unknown=True)
        scanner = scanner_factory([dep], policy)
        report = scanner.scan()
        assert len(report.conflicts) == 1
        assert report.conflicts[0].severity == ConflictSeverity.ERROR

    def test_unknown_license_fail_on_unknown_true_conflict_has_package_name(
        self, scanner_factory, dep_factory
    ):
        dep = dep_factory("mystery-lib")
        policy = LicensePolicy(fail_on_unknown=True)
        scanner = scanner_factory([dep], policy)
        report = scanner.scan()
        assert report.conflicts[0].package == "mystery-lib"

    # --- AGPL without explicit policy ---------------------------------------

    def test_agpl_no_explicit_policy_yields_network_copyleft_warning(
        self, scanner_factory, dep_factory
    ):
        # Default LicensePolicy(): block=[], warn=[], allow=None.
        # AGPL-3.0 is not in any list; check_conflict sees NETWORK_COPYLEFT → WARNING.
        dep = dep_factory("agpl-lib", spdx="AGPL-3.0", family=LicenseFamily.NETWORK_COPYLEFT)
        scanner = scanner_factory([dep])  # no policy → LicensePolicy() defaults
        report = scanner.scan()
        assert len(report.conflicts) == 1
        assert report.conflicts[0].severity == ConflictSeverity.WARNING

    def test_agpl_no_explicit_policy_conflict_mentions_network(self, scanner_factory, dep_factory):
        dep = dep_factory("agpl-lib", spdx="AGPL-3.0", family=LicenseFamily.NETWORK_COPYLEFT)
        scanner = scanner_factory([dep])
        report = scanner.scan()
        assert "network" in report.conflicts[0].reason.lower()

    # --- license_summary ----------------------------------------------------

    def test_license_summary_counts_mit_correctly(self, scanner_factory, dep_factory):
        deps = [
            dep_factory("a", spdx="MIT"),
            dep_factory("b", spdx="MIT"),
            dep_factory("c", spdx="Apache-2.0"),
        ]
        scanner = scanner_factory(deps)
        report = scanner.scan()
        assert report.license_summary["MIT"] == 2

    def test_license_summary_counts_apache_correctly(self, scanner_factory, dep_factory):
        deps = [
            dep_factory("a", spdx="MIT"),
            dep_factory("b", spdx="MIT"),
            dep_factory("c", spdx="Apache-2.0"),
        ]
        scanner = scanner_factory(deps)
        report = scanner.scan()
        assert report.license_summary["Apache-2.0"] == 1

    def test_license_summary_does_not_count_unknown_deps(self, scanner_factory, dep_factory):
        dep_known = dep_factory("a", spdx="MIT")
        dep_unknown = dep_factory("b")  # no license_info
        scanner = scanner_factory([dep_known, dep_unknown])
        report = scanner.scan()
        # Only "MIT" should appear in the summary
        assert "MIT" in report.license_summary
        assert len(report.license_summary) == 1

    # --- multiple deps / multiple conflicts ---------------------------------

    def test_multiple_conflicts_correct_count(
        self, scanner_factory, dep_factory, permissive_policy
    ):
        # GPL-3.0 → blocked → ERROR; LGPL-3.0 → in warn → WARNING; MIT → clean
        deps = [
            dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT),
            dep_factory("lgpl-lib", spdx="LGPL-3.0", family=LicenseFamily.WEAK_COPYLEFT),
            dep_factory("safe-lib", spdx="MIT"),
        ]
        scanner = scanner_factory(deps, permissive_policy)
        report = scanner.scan()
        assert len(report.conflicts) == 2

    def test_multiple_conflicts_contains_error_severity(
        self, scanner_factory, dep_factory, permissive_policy
    ):
        deps = [
            dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT),
            dep_factory("lgpl-lib", spdx="LGPL-3.0", family=LicenseFamily.WEAK_COPYLEFT),
            dep_factory("safe-lib", spdx="MIT"),
        ]
        scanner = scanner_factory(deps, permissive_policy)
        report = scanner.scan()
        severities = {c.severity for c in report.conflicts}
        assert ConflictSeverity.ERROR in severities

    def test_multiple_conflicts_contains_warning_severity(
        self, scanner_factory, dep_factory, permissive_policy
    ):
        deps = [
            dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT),
            dep_factory("lgpl-lib", spdx="LGPL-3.0", family=LicenseFamily.WEAK_COPYLEFT),
            dep_factory("safe-lib", spdx="MIT"),
        ]
        scanner = scanner_factory(deps, permissive_policy)
        report = scanner.scan()
        severities = {c.severity for c in report.conflicts}
        assert ConflictSeverity.WARNING in severities

    # --- direct vs transitive counts ----------------------------------------

    def test_direct_vs_transitive_total_count(self, scanner_factory, dep_factory):
        deps = [
            dep_factory("direct-a", spdx="MIT", is_direct=True),
            dep_factory("direct-b", spdx="MIT", is_direct=True),
            dep_factory("transitive-a", spdx="MIT", is_direct=False),
        ]
        scanner = scanner_factory(deps)
        report = scanner.scan()
        assert report.total_dependencies == 3

    def test_direct_vs_transitive_direct_count(self, scanner_factory, dep_factory):
        deps = [
            dep_factory("direct-a", spdx="MIT", is_direct=True),
            dep_factory("direct-b", spdx="MIT", is_direct=True),
            dep_factory("transitive-a", spdx="MIT", is_direct=False),
        ]
        scanner = scanner_factory(deps)
        report = scanner.scan()
        assert report.direct_dependencies == 2

    # --- project_name -------------------------------------------------------

    def test_project_name_passes_through_to_report(self, scanner_factory, dep_factory):
        scanner = scanner_factory([dep_factory("lib", spdx="MIT")])
        report = scanner.scan(project_name="my-awesome-project")
        assert report.project_name == "my-awesome-project"

    def test_project_name_none_when_not_provided(self, scanner_factory, dep_factory):
        scanner = scanner_factory([dep_factory("lib", spdx="MIT")])
        report = scanner.scan()
        assert report.project_name is None


# ---------------------------------------------------------------------------
# TestLicenseScannerRealInstall
# ---------------------------------------------------------------------------


class TestLicenseScannerRealInstall:
    """Smoke tests that exercise the real PackageResolver against the live environment."""

    def test_scan_installed_returns_compliance_report(self):
        from vigil_core.license_db import LicenseDatabase
        from vigil_core.models import ComplianceReport

        scanner = LicenseScanner(policy=LicensePolicy(), license_db=LicenseDatabase())
        report = scanner.scan()
        assert isinstance(report, ComplianceReport)

    def test_scan_installed_total_dependencies_non_negative(self):
        from vigil_core.license_db import LicenseDatabase

        scanner = LicenseScanner(policy=LicensePolicy(), license_db=LicenseDatabase())
        report = scanner.scan()
        assert report.total_dependencies >= 0

    def test_scan_installed_finds_pytest(self):
        from vigil_core.license_db import LicenseDatabase

        scanner = LicenseScanner(policy=LicensePolicy(), license_db=LicenseDatabase())
        report = scanner.scan()
        names = [d.name.lower() for d in report.dependencies]
        assert any("pytest" in n for n in names)

    def test_scan_from_requirements_returns_at_least_one_dep(self, tmp_requirements):
        from vigil_core.license_db import LicenseDatabase

        scanner = LicenseScanner(policy=LicensePolicy(), license_db=LicenseDatabase())
        report = scanner.scan(requirements_file=str(tmp_requirements))
        assert report.total_dependencies >= 1

    def test_scan_from_requirements_finds_pytest(self, tmp_requirements):
        from vigil_core.license_db import LicenseDatabase

        scanner = LicenseScanner(policy=LicensePolicy(), license_db=LicenseDatabase())
        report = scanner.scan(requirements_file=str(tmp_requirements))
        names = [d.name.lower() for d in report.dependencies]
        assert any("pytest" in n for n in names)
