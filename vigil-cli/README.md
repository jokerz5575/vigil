# vigil-cli

Command-line interface for the Vigil compliance toolkit.

Part of the [Vigil](https://github.com/schmidtpeterdaniel/vigil) compliance toolkit.

## Install

```bash
pip install vigil-cli
```

## Usage

```bash
# Scan current environment
vigil scan

# Scan with a policy file
vigil scan --policy vigil.yaml

# Generate an HTML report
vigil scan --format html --output report.html

# Check for license conflicts
vigil licenses check --policy vigil.yaml
```

## License

Apache-2.0
