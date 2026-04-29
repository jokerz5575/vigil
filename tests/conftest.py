"""
Shared pytest fixtures for the Vigil test suite.

Automatically discovered by pytest — no explicit imports needed in test modules.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pytest

# ---------------------------------------------------------------------------
# Make the monorepo packages importable without pip-installing them.
# (conftest.py is loaded before any test file, so this runs first.)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "vigil-core" / "src"))
sys.path.insert(0, str(_ROOT / "vigil-licenses" / "src"))
sys.path.insert(0, str(_ROOT / "vigil-cli" / "src"))

from vigil_core.license_db import LicenseDatabase
from vigil_core.models import (
    ComplianceReport,
    ConflictSeverity,
    DependencyInfo,
    LicenseConflict,
    LicenseFamily,
    LicenseInfo,
)
from vigil_core.package_resolver import PackageResolver
from vigil_licenses.scanner import LicensePolicy, LicenseScanner

# ---------------------------------------------------------------------------
# Core infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> LicenseDatabase:
    """A fresh LicenseDatabase instance."""
    return LicenseDatabase()


@pytest.fixture
def vigil_yaml_path() -> Path:
    """Absolute path to the root vigil.yaml policy file."""
    return _ROOT / "vigil.yaml"


# ---------------------------------------------------------------------------
# Policy fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def strict_policy() -> LicensePolicy:
    """
    Policy that only allows permissive licenses and blocks all copyleft.
    Mirrors the kind of policy a commercial closed-source project would use.
    """
    return LicensePolicy(
        allow=["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "CC0-1.0"],
        block=["GPL-2.0", "GPL-3.0", "AGPL-3.0", "SSPL-1.0"],
        warn=["LGPL-2.1", "LGPL-3.0", "MPL-2.0"],
        fail_on_unknown=False,
    )


@pytest.fixture
def permissive_policy() -> LicensePolicy:
    """
    Policy with no allow-list — only blocks the worst offenders.
    Mirrors the kind of policy an open-source project would use.
    """
    return LicensePolicy(
        block=["GPL-3.0", "AGPL-3.0", "SSPL-1.0"],
        warn=["LGPL-3.0", "MPL-2.0"],
    )


# ---------------------------------------------------------------------------
# Dependency / report builder helpers
# ---------------------------------------------------------------------------


def _build_dep(
    name: str,
    version: str = "1.0.0",
    spdx: str | None = None,
    family: LicenseFamily = LicenseFamily.PERMISSIVE,
    is_direct: bool = True,
    osi_approved: bool = True,
) -> DependencyInfo:
    """Build a DependencyInfo with optional inline LicenseInfo."""
    license_info: LicenseInfo | None = None
    if spdx:
        license_info = LicenseInfo(
            spdx_id=spdx,
            name=f"{spdx} License",
            family=family,
            osi_approved=osi_approved,
        )
    return DependencyInfo(
        name=name,
        version=version,
        license_spdx=spdx,
        license_info=license_info,
        is_direct=is_direct,
    )


@pytest.fixture
def dep_factory() -> Callable[..., DependencyInfo]:
    """Factory fixture for building DependencyInfo test instances."""
    return _build_dep


def _build_report(
    deps: list[DependencyInfo] | None = None,
    conflicts: list[LicenseConflict] | None = None,
    project_name: str | None = "test-project",
) -> ComplianceReport:
    """Build a ComplianceReport with auto-computed license_summary."""
    deps = deps or []
    conflicts = conflicts or []
    license_summary: dict[str, int] = {}
    for d in deps:
        if d.license_info:
            sid = d.license_info.spdx_id
            license_summary[sid] = license_summary.get(sid, 0) + 1
    return ComplianceReport(
        project_name=project_name,
        total_dependencies=len(deps),
        direct_dependencies=sum(1 for d in deps if d.is_direct),
        dependencies=deps,
        conflicts=conflicts,
        license_summary=license_summary,
    )


@pytest.fixture
def report_factory() -> Callable[..., ComplianceReport]:
    """Factory fixture for building ComplianceReport test instances."""
    return _build_report


# ---------------------------------------------------------------------------
# Scanner helpers
# ---------------------------------------------------------------------------


def _make_scanner(
    deps: list[DependencyInfo],
    policy: LicensePolicy | None = None,
) -> LicenseScanner:
    """Return a LicenseScanner whose resolver is replaced by one that yields *deps*."""
    _db = LicenseDatabase()
    _policy = policy or LicensePolicy()
    scanner = LicenseScanner(policy=_policy, license_db=_db)

    class _MockResolver(PackageResolver):
        def resolve_installed(self) -> list[DependencyInfo]:
            return deps

    scanner._resolver = _MockResolver(license_db=_db)
    return scanner


@pytest.fixture
def scanner_factory() -> Callable[..., LicenseScanner]:
    """Factory fixture for building LicenseScanner instances with injected deps."""
    return _make_scanner


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_requirements(tmp_path: Path) -> Path:
    """Write a minimal requirements.txt with well-known packages."""
    req = tmp_path / "requirements.txt"
    req.write_text("pytest\npydantic\n")
    return req


@pytest.fixture
def tmp_yaml_policy(tmp_path: Path) -> Path:
    """Write a minimal vigil.yaml and return its path."""
    content = """\
policy:
  allow:
    - MIT
    - Apache-2.0
    - BSD-3-Clause
  block:
    - GPL-3.0
    - AGPL-3.0
  warn:
    - LGPL-2.1
    - MPL-2.0
  fail_on_unknown: false
"""
    p = tmp_path / "vigil.yaml"
    p.write_text(content)
    return p
