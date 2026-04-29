# vigil-licenses

License conflict detection and compliance reporting for Python projects.

Part of the [Vigil](https://github.com/schmidtpeterdaniel/vigil) compliance toolkit.

## Install

```bash
pip install vigil-licenses
```

## Quick Start

```python
from vigil_licenses.scanner import LicenseScanner, LicensePolicy

policy = LicensePolicy(
    allow=["MIT", "Apache-2.0", "BSD-3-Clause"],
    block=["GPL-3.0", "AGPL-3.0"],
)
scanner = LicenseScanner(policy=policy)
report = scanner.scan()
print(f"Conflicts: {len(report.conflicts)}")
```

## License

Apache-2.0
