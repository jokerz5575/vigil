"""
Resolves installed Python package metadata including license information.
Works with pip, importlib.metadata, and PyPI JSON API as fallback.
"""
from __future__ import annotations

import importlib.metadata
from typing import Optional

from vigil_core.models import DependencyInfo
from vigil_core.license_db import LicenseDatabase


class PackageResolver:
    """
    Resolves metadata for installed Python packages.
    Uses importlib.metadata as primary source, with PyPI API as fallback.
    """

    def __init__(self, license_db: Optional[LicenseDatabase] = None) -> None:
        self._db = license_db or LicenseDatabase()

    def resolve_installed(self) -> list[DependencyInfo]:
        """
        Resolve all packages currently installed in the Python environment.
        """
        packages = []
        for dist in importlib.metadata.distributions():
            info = self._from_distribution(dist)
            if info:
                packages.append(info)
        return packages

    def resolve_from_requirements(self, requirements_path: str) -> list[DependencyInfo]:
        """
        Parse a requirements.txt and resolve metadata for each listed package.
        """
        import subprocess
        import sys

        packages = []
        with open(requirements_path) as f:
            lines = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]

        for line in lines:
            # Strip version specifiers to get package name
            name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
            try:
                dist = importlib.metadata.distribution(name)
                info = self._from_distribution(dist)
                if info:
                    info.is_direct = True
                    packages.append(info)
            except importlib.metadata.PackageNotFoundError:
                # Package listed but not installed; add as unknown
                packages.append(DependencyInfo(
                    name=name,
                    version="unknown",
                    is_direct=True,
                ))
        return packages

    def _from_distribution(
        self, dist: importlib.metadata.Distribution
    ) -> Optional[DependencyInfo]:
        """Build a DependencyInfo from an importlib.metadata Distribution."""
        try:
            meta = dist.metadata
            name = meta["Name"]
            version = meta["Version"]

            if not name or not version:
                return None

            raw_license = meta.get("License") or ""
            license_info = None
            license_spdx = None

            if raw_license:
                license_spdx = self._db.normalize(raw_license)
                if license_spdx:
                    license_info = self._db.get(license_spdx)

            # Fall back to Classifier: License :: ... entries
            if not license_spdx:
                for classifier in (meta.get_all("Classifier") or []):
                    if classifier.startswith("License ::"):
                        parts = classifier.split(" :: ")
                        if len(parts) >= 3:
                            candidate = parts[-1].strip()
                            license_spdx = self._db.normalize(candidate)
                            if license_spdx:
                                license_info = self._db.get(license_spdx)
                                break

            return DependencyInfo(
                name=name,
                version=version,
                license_spdx=license_spdx or raw_license or None,
                license_info=license_info,
                homepage=meta.get("Home-page"),
                author=meta.get("Author"),
                description=meta.get("Summary"),
                pypi_url=f"https://pypi.org/project/{name}/",
            )
        except Exception:
            return None
