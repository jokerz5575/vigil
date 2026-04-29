# 🛡️ Vigil — Open source compliance, automated.

**Vigil** is a Python-native license compliance toolkit that scans your entire dependency tree,
enforces a tiered SPDX policy, and produces machine-readable reports — all in a single command.
As regulations like the **EU Cyber Resilience Act (CRA)** and **US Executive Order 14028** raise
the bar for software supply-chain transparency, Vigil gives every team — from solo developers to
regulated enterprises — a repeatable, auditable compliance workflow without the manual spreadsheet
grind.

---

## Features

| | |
|---|---|
| 🔍 **License Scanning** | Detects every license in your dependency tree, including transitive dependencies |
| 📋 **Policy Enforcement** | `allow` / `warn` / `block` tiers using SPDX identifiers — ship your policy as code |
| 📄 **SBOM Generation** | SPDX + CycloneDX export *(coming soon)* |
| 🛡️ **Supply Chain Security** | Provenance verification + typosquat detection *(coming soon)* |
| 📊 **Compliance Reports** | Rich terminal output, structured JSON, and standalone HTML reports |
| ⚡ **CI Ready** | Official GitHub Action + non-zero exit codes for pipeline gating |

---

## Quick Start

```bash vigil/docs/index.md
# 1. Install
pip install vigil-licenses vigil-cli

# 2. Scan your current environment (no policy — informational only)
vigil scan

# 3. Scan with a policy file and gate on violations
vigil scan --policy vigil.yaml
```

---

## Packages

| Package | Description | Status |
|---|---|---|
| `vigil-core` | Shared license DB, Pydantic models, package resolver | ✅ Available |
| `vigil-licenses` | License scanning + policy enforcement + reporters | ✅ Available |
| `vigil-cli` | Typer-based command-line interface | ✅ Available |
| `vigil-sbom` | SBOM generation (SPDX + CycloneDX) | 🚧 Coming soon |
| `vigil-policy` | Policy-as-code helpers for CI | 🚧 Coming soon |
| `vigil-supply` | Provenance + typosquat detection | 🚧 Coming soon |

---

## Next Steps

- [**Getting Started**](getting-started.md) — install, run your first scan, and wire up CI in minutes.
- [**Policy Reference**](policy.md) — full `vigil.yaml` format, all ~110 SPDX identifiers, and custom policy examples.
- [**Changelog**](changelog.md) — release history and what's new.
- [**GitHub →**](https://github.com/jokerz5575/vigil) — source code, issues, and contributions welcome.
