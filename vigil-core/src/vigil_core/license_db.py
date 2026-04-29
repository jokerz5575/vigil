"""
Built-in license database with SPDX identifiers, metadata,
and a compatibility conflict matrix.
"""

from __future__ import annotations

from typing import Any

from vigil_core.models import ConflictSeverity, LicenseConflict, LicenseFamily, LicenseInfo

# Core SPDX license definitions
_LICENSE_DATA: dict[str, dict[str, Any]] = {
    "MIT": {
        "name": "MIT License",
        "family": LicenseFamily.PERMISSIVE,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "url": "https://spdx.org/licenses/MIT.html",
    },
    "Apache-2.0": {
        "name": "Apache License 2.0",
        "family": LicenseFamily.PERMISSIVE,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "url": "https://spdx.org/licenses/Apache-2.0.html",
    },
    "BSD-2-Clause": {
        "name": 'BSD 2-Clause "Simplified" License',
        "family": LicenseFamily.PERMISSIVE,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "url": "https://spdx.org/licenses/BSD-2-Clause.html",
    },
    "BSD-3-Clause": {
        "name": 'BSD 3-Clause "New" or "Revised" License',
        "family": LicenseFamily.PERMISSIVE,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "url": "https://spdx.org/licenses/BSD-3-Clause.html",
    },
    "ISC": {
        "name": "ISC License",
        "family": LicenseFamily.PERMISSIVE,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "url": "https://spdx.org/licenses/ISC.html",
    },
    "LGPL-2.1": {
        "name": "GNU Lesser General Public License v2.1",
        "family": LicenseFamily.WEAK_COPYLEFT,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "requires_share_alike": True,
        "url": "https://spdx.org/licenses/LGPL-2.1.html",
    },
    "LGPL-3.0": {
        "name": "GNU Lesser General Public License v3.0",
        "family": LicenseFamily.WEAK_COPYLEFT,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "requires_share_alike": True,
        "url": "https://spdx.org/licenses/LGPL-3.0.html",
    },
    "MPL-2.0": {
        "name": "Mozilla Public License 2.0",
        "family": LicenseFamily.WEAK_COPYLEFT,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "requires_share_alike": True,
        "url": "https://spdx.org/licenses/MPL-2.0.html",
    },
    "GPL-2.0": {
        "name": "GNU General Public License v2.0",
        "family": LicenseFamily.STRONG_COPYLEFT,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "requires_share_alike": True,
        "url": "https://spdx.org/licenses/GPL-2.0.html",
    },
    "GPL-3.0": {
        "name": "GNU General Public License v3.0",
        "family": LicenseFamily.STRONG_COPYLEFT,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "requires_share_alike": True,
        "url": "https://spdx.org/licenses/GPL-3.0.html",
    },
    "AGPL-3.0": {
        "name": "GNU Affero General Public License v3.0",
        "family": LicenseFamily.NETWORK_COPYLEFT,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": True,
        "requires_share_alike": True,
        "network_clause": True,
        "url": "https://spdx.org/licenses/AGPL-3.0.html",
    },
    "SSPL-1.0": {
        "name": "Server Side Public License v1",
        "family": LicenseFamily.NETWORK_COPYLEFT,
        "osi_approved": False,
        "fsf_libre": False,
        "allows_commercial_use": False,
        "requires_attribution": True,
        "requires_share_alike": True,
        "network_clause": True,
        "url": "https://spdx.org/licenses/SSPL-1.0.html",
    },
    "Unlicense": {
        "name": "The Unlicense",
        "family": LicenseFamily.PUBLIC_DOMAIN,
        "osi_approved": True,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": False,
        "url": "https://spdx.org/licenses/Unlicense.html",
    },
    "CC0-1.0": {
        "name": "Creative Commons Zero v1.0 Universal",
        "family": LicenseFamily.PUBLIC_DOMAIN,
        "osi_approved": False,
        "fsf_libre": True,
        "allows_commercial_use": True,
        "requires_attribution": False,
        "url": "https://spdx.org/licenses/CC0-1.0.html",
    },
}

# Common non-SPDX strings -> normalized SPDX mapping
_LICENSE_ALIASES: dict[str, str] = {
    "mit": "MIT",
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "simplified bsd": "BSD-2-Clause",
    "isc license": "ISC",
    "mozilla public license 2.0": "MPL-2.0",
    "gpl": "GPL-3.0",
    "gplv2": "GPL-2.0",
    "gplv3": "GPL-3.0",
    "gnu gpl v3": "GPL-3.0",
    "lgpl": "LGPL-3.0",
    "lgplv2": "LGPL-2.1",
    "lgplv3": "LGPL-3.0",
    "agpl": "AGPL-3.0",
    "agplv3": "AGPL-3.0",
    "public domain": "Unlicense",
    "cc0": "CC0-1.0",
    "psf": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    # Full classifier leaf strings used by popular PyPI packages
    "mit license": "MIT",
    "mit no attribution": "MIT-0",
    "bsd 2-clause license": "BSD-2-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "2-clause bsd license": "BSD-2-Clause",
    "3-clause bsd license": "BSD-3-Clause",
    "isc license (iscl)": "ISC",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "the unlicense (unlicense)": "Unlicense",
    "the unlicense": "Unlicense",
    "gnu general public license v2 (gplv2)": "GPL-2.0",
    "gnu general public license v3 (gplv3)": "GPL-3.0",
    "gnu general public license v2 or later (gplv2+)": "GPL-2.0",
    "gnu general public license v3 or later (gplv3+)": "GPL-3.0",
    "gnu lesser general public license v2 (lgplv2)": "LGPL-2.1",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0",
    "gnu lesser general public license v2 or later (lgplv2+)": "LGPL-2.1",
    "gnu lesser general public license v3 or later (lgplv3+)": "LGPL-3.0",
    "gnu affero general public license v3 (agplv3)": "AGPL-3.0",
    "gnu affero general public license v3 or later (agplv3+)": "AGPL-3.0",
    "historical permission notice and disclaimer (hpnd)": "HPND",
    "apache license, version 2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "eclipse public license 2.0 (epl-2.0)": "EPL-2.0",
    "european union public licence 1.2 (eupl 1.2)": "EUPL-1.2",
    "creativecommons zero v1.0 universal": "CC0-1.0",
    "creative commons cc0 1.0 universal": "CC0-1.0",
    "boost software license 1.0 (bsl-1.0)": "BSL-1.0",
    "zope public license": "ZPL-2.0",
    "python license (compat. mit)": "MIT",
    "lgpl with exceptions or zpl": "LGPL-2.1",
    "lgplv2 with exceptions": "LGPL-2.1",
    "new bsd": "BSD-3-Clause",
    "freebsd license": "BSD-2-Clause",
    "artistic license 2.0": "Artistic-2.0",
    "cddl 1.0": "CDDL-1.0",
}


class LicenseDatabase:
    """
    In-memory license database with SPDX data and conflict detection.
    """

    def __init__(self) -> None:
        self._licenses: dict[str, LicenseInfo] = {
            spdx_id: LicenseInfo(spdx_id=spdx_id, **data) for spdx_id, data in _LICENSE_DATA.items()
        }

    def get(self, spdx_id: str) -> LicenseInfo | None:
        """Look up a license by SPDX ID (exact match)."""
        return self._licenses.get(spdx_id)

    def normalize(self, raw_license: str) -> str | None:
        """
        Normalize a raw license string to its SPDX ID.
        Returns None if the license cannot be identified.
        """
        stripped = raw_license.strip()

        # Exact match first
        if stripped in self._licenses:
            return stripped

        # Alias lookup (case-insensitive)
        normalized = stripped.lower().replace("-", " ").replace("_", " ")
        spdx = _LICENSE_ALIASES.get(normalized) or _LICENSE_ALIASES.get(stripped.lower())
        return spdx

    def resolve(self, raw_license: str) -> LicenseInfo | None:
        """Normalize and look up full license info."""
        spdx_id = self.normalize(raw_license)
        if spdx_id:
            return self._licenses.get(spdx_id)
        return None

    def check_conflict(
        self,
        package_name: str,
        license_spdx: str,
        project_license: str | None = None,
        policy_allow: list[str] | None = None,
        policy_block: list[str] | None = None,
    ) -> LicenseConflict | None:
        """
        Check if a package license conflicts with a policy or project license.
        Returns a LicenseConflict if a problem is found, else None.
        """
        info = self.get(license_spdx)

        # Policy block list takes highest priority
        if policy_block and license_spdx in policy_block:
            return LicenseConflict(
                package=package_name,
                license_spdx=license_spdx,
                severity=ConflictSeverity.ERROR,
                reason=f"{license_spdx} is explicitly blocked by your policy.",
                recommendation="Find an alternative package with a compatible license.",
            )

        # If allow list is set, anything not in it is an error
        if policy_allow and license_spdx not in policy_allow:
            return LicenseConflict(
                package=package_name,
                license_spdx=license_spdx,
                severity=ConflictSeverity.ERROR,
                reason=f"{license_spdx} is not in your allowed license list.",
                recommendation=(
                    f"Add {license_spdx} to your policy allow list "
                    "or find an alternative."
                ),
            )

        if info is None:
            return None

        # SSPL must be checked BEFORE the generic network-copyleft path because
        # SSPL-1.0.family == NETWORK_COPYLEFT; without this guard it would only
        # produce a WARNING instead of the intended ERROR.
        if license_spdx == "SSPL-1.0":
            return LicenseConflict(
                package=package_name,
                license_spdx=license_spdx,
                severity=ConflictSeverity.ERROR,
                reason="SSPL-1.0 is not OSI-approved and restricts commercial cloud usage.",
                recommendation="Find an alternative package.",
            )

        # Warn on any other network-copyleft license (e.g. AGPL) even without
        # an explicit policy — the user should always review these.
        if info.family == LicenseFamily.NETWORK_COPYLEFT:
            return LicenseConflict(
                package=package_name,
                license_spdx=license_spdx,
                severity=ConflictSeverity.WARNING,
                reason=(
                    f"{license_spdx} has a network copyleft clause — "
                    "if you run this software as a service, you may be required "
                    "to release your source code."
                ),
                recommendation="Consult your legal team before using in a SaaS product.",
            )

        return None

    def all_spdx_ids(self) -> list[str]:
        return list(self._licenses.keys())
