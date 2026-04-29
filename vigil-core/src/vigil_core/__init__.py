"""
vigil-core: Shared foundation for the Vigil compliance toolkit.
"""

from vigil_core.github_resolver import GitHubLicenseResolver, GitHubLicenseResult
from vigil_core.license_db import LicenseDatabase
from vigil_core.models import ComplianceReport, DependencyInfo, LicenseInfo
from vigil_core.package_resolver import PackageResolver

__version__ = "0.1.0"
__all__ = [
    "LicenseInfo",
    "DependencyInfo",
    "ComplianceReport",
    "LicenseDatabase",
    "PackageResolver",
    "GitHubLicenseResolver",
    "GitHubLicenseResult",
]
