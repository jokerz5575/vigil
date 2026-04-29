"""
Comprehensive tests for PackageResolver.

Covers:
- resolve_installed(): returns DependencyInfo list, non-empty name/version,
  pytest present, pypi_url format
- resolve_from_requirements(): installed packages found, is_direct=True,
  missing packages → version="unknown", comments/blank lines ignored,
  version specifiers stripped
- _from_distribution(): builds correct DependencyInfo from real metadata,
  custom LicenseDatabase is stored
"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest
from vigil_core.license_db import LicenseDatabase
from vigil_core.models import DependencyInfo
from vigil_core.package_resolver import PackageResolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pytest_is_installed() -> bool:
    try:
        importlib.metadata.distribution("pytest")
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def _pydantic_is_installed() -> bool:
    try:
        importlib.metadata.distribution("pydantic")
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


# ---------------------------------------------------------------------------
# TestResolveInstalled
# ---------------------------------------------------------------------------


class TestResolveInstalled:
    """Tests for PackageResolver.resolve_installed()."""

    @pytest.fixture(autouse=True)
    def resolver(self):
        self._resolver = PackageResolver(license_db=LicenseDatabase())

    def test_returns_a_list(self):
        result = self._resolver.resolve_installed()
        assert isinstance(result, list)

    def test_all_items_are_dependency_info(self):
        result = self._resolver.resolve_installed()
        for item in result:
            assert isinstance(item, DependencyInfo)

    def test_all_items_have_non_empty_name(self):
        result = self._resolver.resolve_installed()
        for item in result:
            assert isinstance(item.name, str)
            assert len(item.name) > 0

    def test_all_items_have_non_empty_version(self):
        result = self._resolver.resolve_installed()
        for item in result:
            assert isinstance(item.version, str)
            assert len(item.version) > 0

    def test_result_is_non_empty(self):
        # At minimum pytest itself must be installed to run these tests.
        result = self._resolver.resolve_installed()
        assert len(result) > 0

    def test_pytest_present_in_results(self):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed (should never happen)")
        result = self._resolver.resolve_installed()
        names = [d.name.lower() for d in result]
        assert any("pytest" in n for n in names)

    def test_pypi_url_format_when_set(self):
        result = self._resolver.resolve_installed()
        for item in result:
            if item.pypi_url is not None:
                assert "pypi.org/project" in item.pypi_url

    def test_pypi_url_references_package_name(self):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        result = self._resolver.resolve_installed()
        pytest_dep = next((d for d in result if d.name.lower() == "pytest"), None)
        if pytest_dep and pytest_dep.pypi_url:
            assert "pytest" in pytest_dep.pypi_url.lower()


# ---------------------------------------------------------------------------
# TestResolveFromRequirements
# ---------------------------------------------------------------------------


class TestResolveFromRequirements:
    """Tests for PackageResolver.resolve_from_requirements()."""

    @pytest.fixture(autouse=True)
    def resolver(self):
        self._resolver = PackageResolver(license_db=LicenseDatabase())

    def test_resolves_pytest_from_requirements(self, tmp_requirements):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        result = self._resolver.resolve_from_requirements(str(tmp_requirements))
        names = [d.name.lower() for d in result]
        assert any("pytest" in n for n in names)

    def test_resolves_pydantic_from_requirements(self, tmp_requirements):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        result = self._resolver.resolve_from_requirements(str(tmp_requirements))
        names = [d.name.lower() for d in result]
        assert any("pydantic" in n for n in names)

    def test_all_returned_items_are_direct(self, tmp_requirements):
        result = self._resolver.resolve_from_requirements(str(tmp_requirements))
        for dep in result:
            assert dep.is_direct is True

    def test_missing_package_returns_version_unknown(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("this-package-definitely-does-not-exist-xyz-abc\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert len(result) == 1
        assert result[0].version == "unknown"

    def test_missing_package_preserves_name(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("this-package-definitely-does-not-exist-xyz-abc\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert result[0].name == "this-package-definitely-does-not-exist-xyz-abc"

    def test_comment_lines_are_ignored(self, tmp_path):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        req = tmp_path / "requirements.txt"
        req.write_text("# this is a comment\npytest\n")
        result = self._resolver.resolve_from_requirements(str(req))
        names = [d.name.lower() for d in result]
        assert "# this is a comment" not in names
        assert not any("#" in n for n in names)

    def test_blank_lines_are_ignored(self, tmp_path):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        req = tmp_path / "requirements.txt"
        req.write_text("\n\npytest\n\n")
        result = self._resolver.resolve_from_requirements(str(req))
        # Only 'pytest' should appear — no blank-line entries
        assert len(result) == 1
        assert result[0].name.lower() == "pytest"

    def test_comment_does_not_appear_as_package(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("# only a comment\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert len(result) == 0

    def test_version_pinned_with_eq_eq_is_stripped(self, tmp_path):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        req = tmp_path / "requirements.txt"
        req.write_text("pytest==8.0.0\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert len(result) == 1
        # The resolved name should be the real package name, not "pytest==8.0.0"
        assert "==" not in result[0].name

    def test_version_pinned_with_eq_eq_resolves_correct_package(self, tmp_path):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        req = tmp_path / "requirements.txt"
        req.write_text("pytest==8.0.0\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert result[0].name.lower() == "pytest"

    def test_version_pinned_with_gte_is_stripped(self, tmp_path):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        req = tmp_path / "requirements.txt"
        req.write_text("pydantic>=2.0\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert len(result) == 1
        assert ">=" not in result[0].name

    def test_version_pinned_with_gte_resolves_correct_package(self, tmp_path):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        req = tmp_path / "requirements.txt"
        req.write_text("pydantic>=2.0\n")
        result = self._resolver.resolve_from_requirements(str(req))
        assert result[0].name.lower() == "pydantic"

    def test_returns_list_of_dependency_info(self, tmp_requirements):
        result = self._resolver.resolve_from_requirements(str(tmp_requirements))
        for item in result:
            assert isinstance(item, DependencyInfo)


# ---------------------------------------------------------------------------
# TestFromDistribution
# ---------------------------------------------------------------------------


class TestFromDistribution:
    """Tests for PackageResolver._from_distribution()."""

    def test_from_distribution_pydantic_returns_dependency_info(self):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        dist = importlib.metadata.distribution("pydantic")
        resolver = PackageResolver(license_db=LicenseDatabase())
        result = resolver._from_distribution(dist)
        assert isinstance(result, DependencyInfo)

    def test_from_distribution_pydantic_name_is_pydantic(self):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        dist = importlib.metadata.distribution("pydantic")
        resolver = PackageResolver(license_db=LicenseDatabase())
        result = resolver._from_distribution(dist)
        assert result is not None
        assert result.name.lower() == "pydantic"

    def test_from_distribution_pydantic_version_non_empty(self):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        dist = importlib.metadata.distribution("pydantic")
        resolver = PackageResolver(license_db=LicenseDatabase())
        result = resolver._from_distribution(dist)
        assert result is not None
        assert len(result.version) > 0

    def test_from_distribution_pytest_returns_something(self):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        dist = importlib.metadata.distribution("pytest")
        resolver = PackageResolver(license_db=LicenseDatabase())
        result = resolver._from_distribution(dist)
        # We only assert that _from_distribution does not raise and returns
        # either a DependencyInfo or None (it may return None for malformed metadata).
        assert result is None or isinstance(result, DependencyInfo)

    def test_from_distribution_pytest_name_when_returned(self):
        if not _pytest_is_installed():
            pytest.skip("pytest not installed")
        dist = importlib.metadata.distribution("pytest")
        resolver = PackageResolver(license_db=LicenseDatabase())
        result = resolver._from_distribution(dist)
        if result is not None:
            assert "pytest" in result.name.lower()

    def test_custom_license_database_stored_on_resolver(self):
        custom_db = LicenseDatabase()
        resolver = PackageResolver(license_db=custom_db)
        assert resolver._db is custom_db

    def test_default_license_database_created_when_none_passed(self):
        resolver = PackageResolver()
        assert isinstance(resolver._db, LicenseDatabase)

    def test_from_distribution_pypi_url_set_for_known_package(self):
        if not _pydantic_is_installed():
            pytest.skip("pydantic not installed")
        dist = importlib.metadata.distribution("pydantic")
        resolver = PackageResolver(license_db=LicenseDatabase())
        result = resolver._from_distribution(dist)
        assert result is not None
        assert result.pypi_url is not None
        assert "pypi.org/project" in result.pypi_url
