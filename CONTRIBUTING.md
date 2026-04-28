# Contributing to Vigil

Thank you for considering a contribution to Vigil! 🎉

## Getting Started

1. **Fork** the repository and clone it locally.

2. **Install development dependencies:**

```bash
pip install -e ./vigil-core[dev]
pip install -e ./vigil-licenses[dev]
pip install -e ./vigil-cli[dev]
pip install pytest ruff mypy
```

3. **Run the tests:**

```bash
pytest tests/ -v
```

4. **Run the linter:**

```bash
ruff check vigil-core/src vigil-licenses/src vigil-cli/src
```

## Project Structure

```
vigil/
├── vigil-core/         # Shared models, license DB, package resolver
├── vigil-licenses/     # License scanner and reporter
├── vigil-cli/          # Typer CLI (vigil command)
├── tests/              # Test suite
├── vigil.yaml          # Example policy file
└── .github/workflows/  # CI/CD
```

## How to Contribute

- **Bug reports** → Open an Issue with steps to reproduce.
- **Feature requests** → Open an Issue describing the use case first.
- **Pull requests** → Please open an issue before large PRs so we can align on direction.

## Adding a New License

Edit `vigil-core/src/vigil_core/license_db.py` and add an entry to `_LICENSE_DATA`.
Add the SPDX ID, full name, and license family. Add any common aliases to `_LICENSE_ALIASES`.

## Adding a New Conflict Rule

In `LicenseDatabase.check_conflict()`, add your logic following the existing pattern.
Make sure to add a corresponding test in `tests/test_vigil.py`.

## Code Style

- Python 3.9+ compatible
- Type hints everywhere
- `ruff` for linting and formatting
- `mypy --strict` for type checking

## License

By contributing, you agree that your contributions will be licensed under Apache-2.0.
