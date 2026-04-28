# 🛡️ Vigil

> **Open source compliance, automated.**

Vigil is a modular Python toolkit for software supply chain compliance — license conflict detection, SBOM generation, policy enforcement, and dependency health scoring. Built for developers, trusted by OSPOs.

---

## Why Vigil?

- 🇪🇺 **EU Cyber Resilience Act** mandates SBOMs for software sold in Europe
- 🔒 **US EO 14028** requires supply chain transparency for federal software
- 🧩 Existing tools are fragmented, hard to configure, and don't talk to each other

Vigil brings it all under one roof — installable piece by piece, or all at once.

---

## Packages

| Package | Description | PyPI |
|---|---|---|
| `vigil-core` | Shared license DB, SBOM parsing, CVE feeds | [![PyPI](https://img.shields.io/pypi/v/vigil-core)](https://pypi.org/project/vigil-core) |
| `vigil-licenses` | License resolution, conflict detection & drift monitoring | [![PyPI](https://img.shields.io/pypi/v/vigil-licenses)](https://pypi.org/project/vigil-licenses) |
| `vigil-sbom` | SBOM generation & validation (SPDX + CycloneDX) | 🚧 Coming soon |
| `vigil-policy` | Policy-as-code enforcement for CI pipelines | 🚧 Coming soon |
| `vigil-supply` | Provenance verification & typosquat detection | 🚧 Coming soon |
| `vigil` | Full suite meta-package | 🚧 Coming soon |

---

## Quick Start

```bash
pip install vigil-licenses
```

```bash
# Scan your current project
vigil scan

# Check for license conflicts
vigil licenses check

# Generate a compliance report
vigil licenses report --format html --output report.html
```

---

## Roadmap

- [x] `vigil-core` — shared foundation
- [x] `vigil-licenses` — license compliance
- [ ] `vigil-sbom` — SBOM generation (SPDX + CycloneDX)
- [ ] `vigil-policy` — CI policy enforcement
- [ ] `vigil-supply` — supply chain security
- [ ] `vigil-dashboard` — local web UI for OSPOs
- [ ] Vigil Cloud — hosted SaaS

---

## Contributing

Vigil is Apache 2.0 licensed and welcomes contributions. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Apache-2.0 © Vigil Contributors
