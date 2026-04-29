"""
Resolves installed Python package metadata including license information.

Resolution order for each package
----------------------------------
1. ``License:`` metadata field → normalised to an SPDX ID.
2. ``License ::`` PyPI classifiers → normalised to an SPDX ID.
3. (Optional) GitHub API via :class:`~vigil_core.github_resolver.GitHubLicenseResolver`
   when a resolver is supplied and steps 1–2 yield nothing.
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

from vigil_core.license_db import LicenseDatabase
from vigil_core.models import DependencyInfo

if TYPE_CHECKING:
    from vigil_core.github_resolver import GitHubLicenseResolver


class PackageResolver:
    """
    Resolves metadata for installed Python packages.

    Pass a :class:`~vigil_core.github_resolver.GitHubLicenseResolver` instance
    as *github_resolver* to automatically fall back to GitHub when a package's
    license cannot be determined from its PyPI metadata alone.
    """

    def __init__(
        self,
        license_db: LicenseDatabase | None = None,
        github_resolver: GitHubLicenseResolver | None = None,
    ) -> None:
        self._db = license_db or LicenseDatabase()
        self._github = github_resolver  # None disables GitHub fallback

    def resolve_installed(self) -> list[DependencyInfo]:
        """Resolve all packages currently installed in the Python environment."""
        packages = []
        for dist in importlib.metadata.distributions():
            info = self._from_distribution(dist)
            if info:
                packages.append(info)
        return packages

    def resolve_from_requirements(self, requirements_path: str) -> list[DependencyInfo]:
        """Parse a requirements.txt and resolve metadata for each listed package."""
        packages = []
        with open(requirements_path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        for line in lines:
            # Strip version specifiers to get the bare package name
            name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
            try:
                dist = importlib.metadata.distribution(name)
                info = self._from_distribution(dist)
                if info:
                    info.is_direct = True
                    packages.append(info)
            except importlib.metadata.PackageNotFoundError:
                packages.append(DependencyInfo(name=name, version="unknown", is_direct=True))
        return packages

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _from_distribution(
        self,
        dist: importlib.metadata.Distribution,
    ) -> DependencyInfo | None:
        """Build a :class:`DependencyInfo` from an importlib.metadata Distribution."""
        try:
            meta = dist.metadata
            name: str = meta["Name"]
            version: str = meta["Version"]

            if not name or not version:
                return None

            license_info = None
            license_spdx: str | None = None
            license_source_url: str | None = None
            license_resolved_by: str | None = None

            # ----------------------------------------------------------------
            # 1. License: metadata field
            # ----------------------------------------------------------------
            raw_license: str = meta.get("License") or ""
            if raw_license:
                license_spdx = self._db.normalize(raw_license)
                if license_spdx:
                    license_info = self._db.get(license_spdx)

            # ----------------------------------------------------------------
            # 2. License :: ... classifier entries
            # ----------------------------------------------------------------
            if not license_spdx:
                for classifier in meta.get_all("Classifier") or []:
                    if classifier.startswith("License ::"):
                        parts = classifier.split(" :: ")
                        if len(parts) >= 3:
                            candidate = parts[-1].strip()
                            license_spdx = self._db.normalize(candidate)
                            if license_spdx:
                                license_info = self._db.get(license_spdx)
                                break

            # ----------------------------------------------------------------
            # 3. GitHub fallback (only when steps 1–2 failed and we have
            #    a version string that is worth searching for)
            # ----------------------------------------------------------------
            if not license_spdx and self._github is not None and version != "unknown":
                result = self._github.resolve(name, version)
                if result is not None:
                    license_spdx = result.spdx_id
                    license_info = self._db.get(license_spdx)
                    license_source_url = result.source_url
                    license_resolved_by = "github"
                    if not result.ref_is_version_tag:
                        # Annotate when we had to fall back to the default branch
                        license_source_url = (
                            f"{result.source_url}  [branch: {result.ref}, no version tag found]"
                        )

            if license_spdx and license_resolved_by is None:
                license_resolved_by = "pypi"

            return DependencyInfo(
                name=name,
                version=version,
                license_spdx=license_spdx or raw_license or None,
                license_info=license_info,
                homepage=meta.get("Home-page"),
                author=meta.get("Author"),
                description=meta.get("Summary"),
                pypi_url=f"https://pypi.org/project/{name}/",
                license_source_url=license_source_url,
                license_resolved_by=license_resolved_by,
            )
        except Exception:  # noqa: BLE001
            return None
