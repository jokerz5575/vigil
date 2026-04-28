"""
Tests for vigil-core: models, license DB, and package resolver.
"""
import sys
import os

# Add packages to path for testing without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../vigil-core/src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../vigil-licenses/src"))

import pytest
from vigil_core.license_db import LicenseDatabase
from vigil_core.models import LicenseFamily, ConflictSeverity


@pytest.fixture
def db():
    return LicenseDatabase()


class TestLicenseDatabase:
    def test_get_known_license(self, db):
        lic = db.get("MIT")
        assert lic is not None
        assert lic.spdx_id == "MIT"
        assert lic.family == LicenseFamily.PERMISSIVE
        assert lic.osi_approved is True

    def test_get_unknown_license(self, db):
        assert db.get("FOOBAR-1.0") is None

    def test_normalize_exact(self, db):
        assert db.normalize("MIT") == "MIT"
        assert db.normalize("Apache-2.0") == "Apache-2.0"

    def test_normalize_alias(self, db):
        assert db.normalize("apache 2.0") == "Apache-2.0"
        assert db.normalize("MIT") == "MIT"
        assert db.normalize("gplv3") == "GPL-3.0"

    def test_normalize_unknown(self, db):
        assert db.normalize("Some Random License 5.0") is None

    def test_no_conflict_for_permissive(self, db):
        conflict = db.check_conflict("requests", "MIT")
        assert conflict is None

    def test_conflict_blocked_license(self, db):
        conflict = db.check_conflict(
            "somelib", "GPL-3.0", policy_block=["GPL-3.0"]
        )
        assert conflict is not None
        assert conflict.severity == ConflictSeverity.ERROR

    def test_conflict_not_in_allowlist(self, db):
        conflict = db.check_conflict(
            "somelib", "LGPL-3.0",
            policy_allow=["MIT", "Apache-2.0"]
        )
        assert conflict is not None
        assert conflict.severity == ConflictSeverity.ERROR

    def test_allowed_license_passes(self, db):
        conflict = db.check_conflict(
            "requests", "MIT",
            policy_allow=["MIT", "Apache-2.0"]
        )
        assert conflict is None

    def test_agpl_warns_by_default(self, db):
        conflict = db.check_conflict("somelib", "AGPL-3.0")
        assert conflict is not None
        assert conflict.severity == ConflictSeverity.WARNING

    def test_all_spdx_ids(self, db):
        ids = db.all_spdx_ids()
        assert "MIT" in ids
        assert "Apache-2.0" in ids
        assert "GPL-3.0" in ids
        assert len(ids) > 10


class TestLicenseInfo:
    def test_is_permissive(self, db):
        assert db.get("MIT").is_permissive() is True
        assert db.get("GPL-3.0").is_permissive() is False

    def test_is_copyleft(self, db):
        assert db.get("GPL-3.0").is_copyleft() is True
        assert db.get("AGPL-3.0").is_copyleft() is True
        assert db.get("MIT").is_copyleft() is False


class TestLicenseScanner:
    def test_scanner_runs(self):
        from vigil_licenses.scanner import LicenseScanner
        scanner = LicenseScanner()
        report = scanner.scan()
        # Should complete without error; at minimum finds Python itself
        assert report.total_dependencies >= 0

    def test_policy_blocks_trigger_errors(self):
        from vigil_licenses.scanner import LicenseScanner, LicensePolicy
        from vigil_core.models import DependencyInfo, LicenseInfo, LicenseFamily
        from vigil_core.package_resolver import PackageResolver

        # Mock resolver
        class MockResolver(PackageResolver):
            def resolve_installed(self):
                return [
                    DependencyInfo(
                        name="evil-gpl-lib",
                        version="1.0.0",
                        license_spdx="GPL-3.0",
                        license_info=LicenseInfo(
                            spdx_id="GPL-3.0",
                            name="GNU General Public License v3.0",
                            family=LicenseFamily.STRONG_COPYLEFT,
                        ),
                    )
                ]

        from vigil_core.license_db import LicenseDatabase
        db = LicenseDatabase()
        policy = LicensePolicy(block=["GPL-3.0"])
        scanner = LicenseScanner(policy=policy, license_db=db)
        scanner._resolver = MockResolver(license_db=db)

        report = scanner.scan()
        assert report.has_errors is True
        assert len(report.conflicts) == 1
        assert report.conflicts[0].package == "evil-gpl-lib"
