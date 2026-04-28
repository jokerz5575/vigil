"""
LicenseScanner: scans a project's dependencies and detects license conflicts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from vigil_core.license_db import LicenseDatabase
from vigil_core.models import ComplianceReport, LicenseConflict, ConflictSeverity
from vigil_core.package_resolver import PackageResolver


class LicensePolicy:
    """
    Defines which licenses are allowed, blocked, or warned about.

    Example:
        policy = LicensePolicy(
            allow=["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"],
            block=["GPL-3.0", "AGPL-3.0", "SSPL-1.0"],
        )
    """

    def __init__(
        self,
        allow: Optional[list[str]] = None,
        block: Optional[list[str]] = None,
        warn: Optional[list[str]] = None,
        fail_on_unknown: bool = False,
    ) -> None:
        self.allow = allow
        self.block = block or []
        self.warn = warn or []
        self.fail_on_unknown = fail_on_unknown

    @classmethod
    def from_dict(cls, data: dict) -> "LicensePolicy":
        policy = data.get("policy", data)
        return cls(
            allow=policy.get("allow"),
            block=policy.get("block", []),
            warn=policy.get("warn", []),
            fail_on_unknown=policy.get("fail_on_unknown", False),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "LicensePolicy":
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required to load policy from YAML. "
                "Install it with: pip install pyyaml"
            )
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


class LicenseScanner:
    """
    Scans Python project dependencies for license compliance issues.

    Usage:
        scanner = LicenseScanner(policy=LicensePolicy(block=["GPL-3.0"]))
        report = scanner.scan()
        print(f"Found {len(report.conflicts)} conflicts")
    """

    def __init__(
        self,
        policy: Optional[LicensePolicy] = None,
        license_db: Optional[LicenseDatabase] = None,
    ) -> None:
        self._policy = policy or LicensePolicy()
        self._db = license_db or LicenseDatabase()
        self._resolver = PackageResolver(license_db=self._db)

    def scan(
        self,
        requirements_file: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> ComplianceReport:
        """
        Scan dependencies and return a full ComplianceReport.

        Args:
            requirements_file: Path to requirements.txt. If None, scans
                               all packages installed in the current environment.
            project_name: Optional name to embed in the report.
        """
        if requirements_file:
            deps = self._resolver.resolve_from_requirements(requirements_file)
        else:
            deps = self._resolver.resolve_installed()

        conflicts: list[LicenseConflict] = []
        unknown_licenses: list[str] = []
        license_summary: dict[str, int] = {}

        for dep in deps:
            # Track unknown licenses
            if not dep.license_info:
                raw = dep.license_spdx or "UNKNOWN"
                unknown_licenses.append(f"{dep.name} ({raw})")
                if self._policy.fail_on_unknown:
                    conflicts.append(LicenseConflict(
                        package=dep.name,
                        license_spdx=raw,
                        severity=ConflictSeverity.ERROR,
                        reason=f"License '{raw}' could not be identified.",
                        recommendation="Manually verify the license for this package.",
                    ))
                continue

            spdx = dep.license_info.spdx_id

            # License summary count
            license_summary[spdx] = license_summary.get(spdx, 0) + 1

            # Check warn list
            if spdx in self._policy.warn:
                conflicts.append(LicenseConflict(
                    package=dep.name,
                    license_spdx=spdx,
                    severity=ConflictSeverity.WARNING,
                    reason=f"{spdx} is flagged for review in your policy.",
                ))
                continue

            # Full conflict check
            conflict = self._db.check_conflict(
                package_name=dep.name,
                license_spdx=spdx,
                policy_allow=self._policy.allow,
                policy_block=self._policy.block,
            )
            if conflict:
                conflicts.append(conflict)

        return ComplianceReport(
            project_name=project_name,
            total_dependencies=len(deps),
            direct_dependencies=sum(1 for d in deps if d.is_direct),
            dependencies=deps,
            conflicts=conflicts,
            unknown_licenses=unknown_licenses,
            license_summary=license_summary,
        )
