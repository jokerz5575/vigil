"""
Shared Pydantic models for the Vigil compliance toolkit.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LicenseFamily(str, Enum):
    """High-level license family classification."""

    PERMISSIVE = "permissive"  # MIT, Apache-2.0, BSD
    WEAK_COPYLEFT = "weak_copyleft"  # LGPL, MPL
    STRONG_COPYLEFT = "strong_copyleft"  # GPL
    NETWORK_COPYLEFT = "network_copyleft"  # AGPL, SSPL
    PROPRIETARY = "proprietary"
    PUBLIC_DOMAIN = "public_domain"
    UNKNOWN = "unknown"


class LicenseInfo(BaseModel):
    """Represents a resolved software license."""

    spdx_id: str = Field(..., description="SPDX license identifier, e.g. 'MIT'")
    name: str = Field(..., description="Full license name")
    family: LicenseFamily
    osi_approved: bool = False
    fsf_libre: bool = False
    allows_commercial_use: bool = True
    requires_attribution: bool = False
    requires_share_alike: bool = False
    network_clause: bool = False  # True for AGPL, SSPL
    url: str | None = None

    def is_permissive(self) -> bool:
        return self.family == LicenseFamily.PERMISSIVE

    def is_copyleft(self) -> bool:
        return self.family in (
            LicenseFamily.WEAK_COPYLEFT,
            LicenseFamily.STRONG_COPYLEFT,
            LicenseFamily.NETWORK_COPYLEFT,
        )


class DependencyInfo(BaseModel):
    """Represents a resolved package dependency."""

    name: str
    version: str
    license_spdx: str | None = None
    license_info: LicenseInfo | None = None
    is_direct: bool = True
    homepage: str | None = None
    repository: str | None = None
    author: str | None = None
    description: str | None = None
    pypi_url: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.name}=={self.version}"


class ConflictSeverity(str, Enum):
    ERROR = "error"  # Must fix — e.g. GPL in a proprietary project
    WARNING = "warning"  # Should review — e.g. LGPL
    INFO = "info"  # Informational


class LicenseConflict(BaseModel):
    """Represents a detected license conflict between dependencies."""

    package: str
    license_spdx: str
    severity: ConflictSeverity
    reason: str
    recommendation: str | None = None


class ComplianceReport(BaseModel):
    """Full compliance scan report."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    project_name: str | None = None
    total_dependencies: int = 0
    direct_dependencies: int = 0
    dependencies: list[DependencyInfo] = Field(default_factory=list)
    conflicts: list[LicenseConflict] = Field(default_factory=list)
    unknown_licenses: list[str] = Field(default_factory=list)
    license_summary: dict[str, int] = Field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(c.severity == ConflictSeverity.ERROR for c in self.conflicts)

    @property
    def has_warnings(self) -> bool:
        return any(c.severity == ConflictSeverity.WARNING for c in self.conflicts)

    def license_families(self) -> dict[str, list[str]]:
        """Group packages by license family."""
        result: dict[str, list[str]] = {}
        for dep in self.dependencies:
            if dep.license_info:
                family = dep.license_info.family.value
                result.setdefault(family, []).append(dep.name)
        return result
