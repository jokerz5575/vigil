"""
Comprehensive tests for vigil_core.models.

Covers:
  - LicenseInfo  (is_permissive, is_copyleft, default fields)
  - DependencyInfo  (display_name, default fields)
  - ComplianceReport  (has_errors, has_warnings, license_families, empty defaults)
"""

from __future__ import annotations

from typing import Callable

import pytest
from vigil_core.models import (
    ComplianceReport,
    ConflictSeverity,
    DependencyInfo,
    LicenseConflict,
    LicenseFamily,
    LicenseInfo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_FAMILIES: list[LicenseFamily] = list(LicenseFamily)

# Families for which is_permissive() must return True
PERMISSIVE_FAMILIES: set[LicenseFamily] = {LicenseFamily.PERMISSIVE}

# Families for which is_copyleft() must return True
COPYLEFT_FAMILIES: set[LicenseFamily] = {
    LicenseFamily.WEAK_COPYLEFT,
    LicenseFamily.STRONG_COPYLEFT,
    LicenseFamily.NETWORK_COPYLEFT,
}


def _make_license_info(family: LicenseFamily) -> LicenseInfo:
    """Build a minimal LicenseInfo for the given family."""
    return LicenseInfo(
        spdx_id=f"TEST-{family.value}",
        name=f"Test {family.value} License",
        family=family,
    )


def _make_conflict(severity: ConflictSeverity, spdx: str = "GPL-3.0") -> LicenseConflict:
    return LicenseConflict(
        package="some-pkg",
        license_spdx=spdx,
        severity=severity,
        reason="Test conflict",
    )


# ---------------------------------------------------------------------------
# TestLicenseInfo
# ---------------------------------------------------------------------------


class TestLicenseInfo:
    """Tests for LicenseInfo model methods and default field values."""

    # --- is_permissive() parametrized over all 7 families ---

    @pytest.mark.parametrize("family", ALL_FAMILIES)
    def test_is_permissive_true_only_for_permissive(self, family: LicenseFamily) -> None:
        info = _make_license_info(family)
        expected = family in PERMISSIVE_FAMILIES
        assert info.is_permissive() is expected

    def test_is_permissive_mit_like(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.is_permissive() is True

    def test_is_permissive_gpl_false(self) -> None:
        info = _make_license_info(LicenseFamily.STRONG_COPYLEFT)
        assert info.is_permissive() is False

    def test_is_permissive_public_domain_false(self) -> None:
        info = _make_license_info(LicenseFamily.PUBLIC_DOMAIN)
        assert info.is_permissive() is False

    def test_is_permissive_unknown_false(self) -> None:
        info = _make_license_info(LicenseFamily.UNKNOWN)
        assert info.is_permissive() is False

    def test_is_permissive_proprietary_false(self) -> None:
        info = _make_license_info(LicenseFamily.PROPRIETARY)
        assert info.is_permissive() is False

    # --- is_copyleft() parametrized over all 7 families ---

    @pytest.mark.parametrize("family", ALL_FAMILIES)
    def test_is_copyleft_true_only_for_copyleft_families(self, family: LicenseFamily) -> None:
        info = _make_license_info(family)
        expected = family in COPYLEFT_FAMILIES
        assert info.is_copyleft() is expected

    def test_is_copyleft_weak_copyleft_true(self) -> None:
        info = _make_license_info(LicenseFamily.WEAK_COPYLEFT)
        assert info.is_copyleft() is True

    def test_is_copyleft_strong_copyleft_true(self) -> None:
        info = _make_license_info(LicenseFamily.STRONG_COPYLEFT)
        assert info.is_copyleft() is True

    def test_is_copyleft_network_copyleft_true(self) -> None:
        info = _make_license_info(LicenseFamily.NETWORK_COPYLEFT)
        assert info.is_copyleft() is True

    def test_is_copyleft_permissive_false(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.is_copyleft() is False

    def test_is_copyleft_public_domain_false(self) -> None:
        info = _make_license_info(LicenseFamily.PUBLIC_DOMAIN)
        assert info.is_copyleft() is False

    def test_is_copyleft_proprietary_false(self) -> None:
        info = _make_license_info(LicenseFamily.PROPRIETARY)
        assert info.is_copyleft() is False

    def test_is_copyleft_unknown_false(self) -> None:
        info = _make_license_info(LicenseFamily.UNKNOWN)
        assert info.is_copyleft() is False

    # --- default field values ---

    def test_default_osi_approved_is_false(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.osi_approved is False

    def test_default_fsf_libre_is_false(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.fsf_libre is False

    def test_default_allows_commercial_use_is_true(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.allows_commercial_use is True

    def test_default_requires_attribution_is_false(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.requires_attribution is False

    def test_default_requires_share_alike_is_false(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.requires_share_alike is False

    def test_default_network_clause_is_false(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.network_clause is False

    def test_default_url_is_none(self) -> None:
        info = _make_license_info(LicenseFamily.PERMISSIVE)
        assert info.url is None

    # --- explicit field assignment ---

    def test_explicit_fields_are_stored(self) -> None:
        info = LicenseInfo(
            spdx_id="MIT",
            name="MIT License",
            family=LicenseFamily.PERMISSIVE,
            osi_approved=True,
            fsf_libre=True,
            allows_commercial_use=True,
            requires_attribution=True,
            requires_share_alike=False,
            network_clause=False,
            url="https://spdx.org/licenses/MIT.html",
        )
        assert info.spdx_id == "MIT"
        assert info.name == "MIT License"
        assert info.family == LicenseFamily.PERMISSIVE
        assert info.osi_approved is True
        assert info.fsf_libre is True
        assert info.allows_commercial_use is True
        assert info.requires_attribution is True
        assert info.requires_share_alike is False
        assert info.network_clause is False
        assert info.url == "https://spdx.org/licenses/MIT.html"

    def test_network_clause_true_stored(self) -> None:
        info = LicenseInfo(
            spdx_id="AGPL-3.0",
            name="GNU Affero GPL v3",
            family=LicenseFamily.NETWORK_COPYLEFT,
            network_clause=True,
        )
        assert info.network_clause is True


# ---------------------------------------------------------------------------
# TestDependencyInfo
# ---------------------------------------------------------------------------


class TestDependencyInfo:
    """Tests for DependencyInfo model properties and default field values."""

    # --- display_name format ---

    def test_display_name_format(self, dep_factory: Callable[..., DependencyInfo]) -> None:
        dep = dep_factory("requests", "2.28.0")
        assert dep.display_name == "requests==2.28.0"

    def test_display_name_with_semver(self, dep_factory: Callable[..., DependencyInfo]) -> None:
        dep = dep_factory("pydantic", "1.10.4")
        assert dep.display_name == "pydantic==1.10.4"

    def test_display_name_with_pre_release(
        self, dep_factory: Callable[..., DependencyInfo]
    ) -> None:
        dep = dep_factory("pytest", "8.0.0rc1")
        assert dep.display_name == "pytest==8.0.0rc1"

    def test_display_name_name_component(self, dep_factory: Callable[..., DependencyInfo]) -> None:
        dep = dep_factory("my-package", "1.0.0")
        assert dep.display_name.startswith("my-package==")

    def test_display_name_version_component(
        self, dep_factory: Callable[..., DependencyInfo]
    ) -> None:
        dep = dep_factory("pkg", "3.14.159")
        assert dep.display_name.endswith("==3.14.159")

    # --- default field values ---

    def test_default_license_spdx_is_none(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.license_spdx is None

    def test_default_license_info_is_none(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.license_info is None

    def test_default_is_direct_is_true(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.is_direct is True

    def test_default_homepage_is_none(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.homepage is None

    def test_default_repository_is_none(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.repository is None

    def test_default_author_is_none(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.author is None

    def test_default_description_is_none(self) -> None:
        dep = DependencyInfo(name="pkg", version="1.0.0")
        assert dep.description is None

    # --- factory-built deps ---

    def test_dep_factory_with_spdx_sets_license_info(
        self, dep_factory: Callable[..., DependencyInfo]
    ) -> None:
        dep = dep_factory("pkg", "1.0", spdx="MIT")
        assert dep.license_spdx == "MIT"
        assert dep.license_info is not None
        assert dep.license_info.spdx_id == "MIT"

    def test_dep_factory_without_spdx_leaves_license_info_none(
        self, dep_factory: Callable[..., DependencyInfo]
    ) -> None:
        dep = dep_factory("pkg", "1.0")
        assert dep.license_spdx is None
        assert dep.license_info is None

    def test_dep_factory_is_direct_false(self, dep_factory: Callable[..., DependencyInfo]) -> None:
        dep = dep_factory("pkg", "1.0", is_direct=False)
        assert dep.is_direct is False

    def test_dep_factory_family_stored_on_license_info(
        self, dep_factory: Callable[..., DependencyInfo]
    ) -> None:
        dep = dep_factory("pkg", "1.0", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT)
        assert dep.license_info is not None
        assert dep.license_info.family == LicenseFamily.STRONG_COPYLEFT


# ---------------------------------------------------------------------------
# TestComplianceReport
# ---------------------------------------------------------------------------


class TestComplianceReport:
    """Tests for ComplianceReport model properties and methods."""

    # --- has_errors ---

    def test_has_errors_true_when_error_conflict_present(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflict = _make_conflict(ConflictSeverity.ERROR)
        report = report_factory(conflicts=[conflict])
        assert report.has_errors is True

    def test_has_errors_false_when_no_conflicts(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.has_errors is False

    def test_has_errors_false_when_only_warnings(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflict = _make_conflict(ConflictSeverity.WARNING)
        report = report_factory(conflicts=[conflict])
        assert report.has_errors is False

    def test_has_errors_false_when_only_info(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflict = _make_conflict(ConflictSeverity.INFO)
        report = report_factory(conflicts=[conflict])
        assert report.has_errors is False

    def test_has_errors_true_with_multiple_conflicts_including_error(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflicts = [
            _make_conflict(ConflictSeverity.WARNING, "LGPL-3.0"),
            _make_conflict(ConflictSeverity.ERROR, "GPL-3.0"),
        ]
        report = report_factory(conflicts=conflicts)
        assert report.has_errors is True

    # --- has_warnings ---

    def test_has_warnings_true_when_warning_conflict_present(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflict = _make_conflict(ConflictSeverity.WARNING)
        report = report_factory(conflicts=[conflict])
        assert report.has_warnings is True

    def test_has_warnings_false_when_no_conflicts(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.has_warnings is False

    def test_has_warnings_false_when_only_errors(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflict = _make_conflict(ConflictSeverity.ERROR)
        report = report_factory(conflicts=[conflict])
        assert report.has_warnings is False

    def test_has_warnings_false_when_only_info(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflict = _make_conflict(ConflictSeverity.INFO)
        report = report_factory(conflicts=[conflict])
        assert report.has_warnings is False

    # --- mixed severity: both has_errors and has_warnings simultaneously ---

    def test_has_errors_and_has_warnings_can_both_be_true(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflicts = [
            _make_conflict(ConflictSeverity.ERROR, "GPL-3.0"),
            _make_conflict(ConflictSeverity.WARNING, "LGPL-3.0"),
        ]
        report = report_factory(conflicts=conflicts)
        assert report.has_errors is True
        assert report.has_warnings is True

    def test_multiple_errors_has_errors_true(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        conflicts = [
            _make_conflict(ConflictSeverity.ERROR, "GPL-3.0"),
            _make_conflict(ConflictSeverity.ERROR, "AGPL-3.0"),
        ]
        report = report_factory(conflicts=conflicts)
        assert report.has_errors is True
        assert report.has_warnings is False

    # --- empty report defaults ---

    def test_empty_report_has_zero_total_dependencies(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.total_dependencies == 0

    def test_empty_report_has_zero_direct_dependencies(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.direct_dependencies == 0

    def test_empty_report_has_empty_dependencies_list(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.dependencies == []

    def test_empty_report_has_empty_conflicts_list(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.conflicts == []

    def test_empty_report_has_errors_false(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.has_errors is False

    def test_empty_report_has_warnings_false(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.has_warnings is False

    def test_empty_report_license_families_is_empty_dict(
        self, report_factory: Callable[..., ComplianceReport]
    ) -> None:
        report = report_factory()
        assert report.license_families() == {}

    # --- license_families() ---

    def test_license_families_groups_by_family_string(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [
            dep_factory("requests", "2.28.0", spdx="MIT", family=LicenseFamily.PERMISSIVE),
            dep_factory("flask", "2.3.0", spdx="Apache-2.0", family=LicenseFamily.PERMISSIVE),
            dep_factory(
                "some-gpl-lib", "1.0.0", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT
            ),
        ]
        report = report_factory(deps=deps)
        families = report.license_families()

        assert "permissive" in families
        assert sorted(families["permissive"]) == ["flask", "requests"]
        assert "strong_copyleft" in families
        assert families["strong_copyleft"] == ["some-gpl-lib"]

    def test_license_families_excludes_deps_without_license_info(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [
            dep_factory("known-pkg", "1.0.0", spdx="MIT", family=LicenseFamily.PERMISSIVE),
            dep_factory("unknown-pkg", "1.0.0"),  # no spdx → no license_info
        ]
        report = report_factory(deps=deps)
        families = report.license_families()

        # "unknown-pkg" must not appear anywhere in the result
        all_packages: list[str] = [pkg for names in families.values() for pkg in names]
        assert "unknown-pkg" not in all_packages
        assert "known-pkg" in all_packages

    def test_license_families_only_deps_without_license_info_returns_empty(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [
            dep_factory("pkg-a", "1.0.0"),  # no license_info
            dep_factory("pkg-b", "2.0.0"),  # no license_info
        ]
        report = report_factory(deps=deps)
        assert report.license_families() == {}

    def test_license_families_multiple_per_family(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [
            dep_factory("lib-a", "1.0", spdx="MIT", family=LicenseFamily.PERMISSIVE),
            dep_factory("lib-b", "1.0", spdx="Apache-2.0", family=LicenseFamily.PERMISSIVE),
            dep_factory("lib-c", "1.0", spdx="BSD-3-Clause", family=LicenseFamily.PERMISSIVE),
        ]
        report = report_factory(deps=deps)
        families = report.license_families()
        assert len(families["permissive"]) == 3
        assert sorted(families["permissive"]) == ["lib-a", "lib-b", "lib-c"]

    def test_license_families_returns_dict(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        dep = dep_factory("pkg", "1.0", spdx="MIT", family=LicenseFamily.PERMISSIVE)
        report = report_factory(deps=[dep])
        assert isinstance(report.license_families(), dict)

    def test_license_families_family_value_is_string(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        dep = dep_factory("pkg", "1.0", spdx="AGPL-3.0", family=LicenseFamily.NETWORK_COPYLEFT)
        report = report_factory(deps=[dep])
        families = report.license_families()
        # Keys must be the .value strings of LicenseFamily, not enum members
        for key in families:
            assert isinstance(key, str)
        assert "network_copyleft" in families

    def test_license_families_mixed_known_and_unknown_deps(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [
            dep_factory("mit-lib", "1.0", spdx="MIT", family=LicenseFamily.PERMISSIVE),
            dep_factory("no-license", "1.0"),  # excluded
            dep_factory("lgpl-lib", "1.0", spdx="LGPL-3.0", family=LicenseFamily.WEAK_COPYLEFT),
        ]
        report = report_factory(deps=deps)
        families = report.license_families()

        assert set(families.keys()) == {"permissive", "weak_copyleft"}
        assert "mit-lib" in families["permissive"]
        assert "lgpl-lib" in families["weak_copyleft"]

    # --- project_name propagated ---

    def test_project_name_stored(self, report_factory: Callable[..., ComplianceReport]) -> None:
        report = report_factory(project_name="my-cool-project")
        assert report.project_name == "my-cool-project"

    def test_project_name_none(self, report_factory: Callable[..., ComplianceReport]) -> None:
        report = report_factory(project_name=None)
        assert report.project_name is None

    # --- dependency counts ---

    def test_total_dependencies_count(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [dep_factory(f"pkg-{i}", "1.0") for i in range(5)]
        report = report_factory(deps=deps)
        assert report.total_dependencies == 5

    def test_direct_dependencies_count(
        self,
        dep_factory: Callable[..., DependencyInfo],
        report_factory: Callable[..., ComplianceReport],
    ) -> None:
        deps = [
            dep_factory("direct-a", "1.0", is_direct=True),
            dep_factory("direct-b", "1.0", is_direct=True),
            dep_factory("transitive", "1.0", is_direct=False),
        ]
        report = report_factory(deps=deps)
        assert report.direct_dependencies == 2
