# `generate_report` & `ReportFormat`

**Module:** `vigil_licenses.reporter`  
**Source:** `vigil-licenses/src/vigil_licenses/reporter.py`

The reporter module converts a `ComplianceReport` into one of three output formats:
a rich terminal table, a JSON string, or a self-contained HTML page.

---

## `ReportFormat`

```python
class ReportFormat(str, Enum):
    TERMINAL = "terminal"
    JSON     = "json"
    HTML     = "html"
```

| Value | String | Description |
|---|---|---|
| `ReportFormat.TERMINAL` | `"terminal"` | Renders a rich table directly to stdout using the `rich` library |
| `ReportFormat.JSON` | `"json"` | Returns a pretty-printed JSON string (Pydantic `model_dump_json`) |
| `ReportFormat.HTML` | `"html"` | Returns a self-contained HTML page rendered from a Jinja2 template |

Because `ReportFormat` extends `str`, the values can be compared to plain strings:

```python
assert ReportFormat.JSON == "json"
assert ReportFormat.TERMINAL == "terminal"
assert ReportFormat.HTML == "html"
```

---

## `generate_report(report, fmt, output_path)`

```python
def generate_report(
    report: ComplianceReport,
    fmt: ReportFormat = ReportFormat.TERMINAL,
    output_path: str | Path | None = None,
) -> str
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `report` | `ComplianceReport` | — | The report object to render |
| `fmt` | `ReportFormat` | `TERMINAL` | Output format |
| `output_path` | `str \| Path \| None` | `None` | If provided, the rendered content is written to this file path (not applicable for `TERMINAL`) |

**Return value:**

- `TERMINAL` — renders directly to stdout and returns `""`.
- `JSON` — returns the JSON string.
- `HTML` — returns the HTML string.

When `output_path` is given for `JSON` or `HTML`, the content is **both** returned
*and* written to disk.

---

## Usage Examples

### Terminal output

```python
from vigil_licenses.reporter import generate_report, ReportFormat

# Prints a rich table to the terminal, returns ""
result = generate_report(report, ReportFormat.TERMINAL)
assert result == ""
```

The terminal renderer produces:

- A summary panel showing the project name.
- A "License Breakdown" table listing each unique SPDX ID and the number of packages using it.
- A "License Issues" table showing every conflict with severity badge, package name,
  SPDX ID, reason, and recommendation.
- A final pass/fail line in green (no conflicts) or red/yellow (errors/warnings).

### JSON output

=== "String only"

    ```python
    import json
    from vigil_licenses.reporter import generate_report, ReportFormat

    json_str = generate_report(report, ReportFormat.JSON)
    data = json.loads(json_str)

    print(data["total_dependencies"])
    print(data["conflicts"][0]["severity"])   # "error" or "warning"
    ```

=== "Write to file"

    ```python
    from pathlib import Path
    from vigil_licenses.reporter import generate_report, ReportFormat

    json_str = generate_report(
        report, ReportFormat.JSON, output_path="report.json"
    )
    # report.json is written; json_str contains the same content
    ```

The JSON schema mirrors the Pydantic model structure.  Enum values are serialised as
their lowercase string equivalents (`"error"`, `"warning"`, `"permissive"`, etc.).

### HTML output

=== "String only"

    ```python
    from vigil_licenses.reporter import generate_report, ReportFormat

    html = generate_report(report, ReportFormat.HTML)
    assert "<!DOCTYPE html>" in html
    assert report.project_name in html
    ```

=== "Write to file"

    ```python
    from pathlib import Path
    from vigil_licenses.reporter import generate_report, ReportFormat

    generate_report(report, ReportFormat.HTML, output_path="report.html")
    # Open report.html in a browser — no server required
    ```

!!! note "Self-contained HTML"
    The HTML report uses **no external CDN dependencies**.  All CSS is inlined in a
    `<style>` block and the layout is achieved with a small Bootstrap-inspired
    stylesheet embedded directly in the `<head>`.  The file can be opened from the
    filesystem (`file://…`) or attached to a CI artifact without any network access.

---

## Private Helpers

These functions are not part of the public API but are documented here for contributors.

### `_render_terminal(report)`

```python
def _render_terminal(report: ComplianceReport) -> None
```

Uses `rich.console.Console` and `rich.table.Table` to render the compliance report
to stdout.  The function writes directly to the console and returns `None`.  It is
called by `generate_report()` when `fmt == ReportFormat.TERMINAL`.

### `_render_json(report)`

```python
def _render_json(report: ComplianceReport) -> str
```

Delegates to Pydantic:

```python
return report.model_dump_json(indent=2)
```

### `_render_html(report)`

```python
def _render_html(report: ComplianceReport) -> str
```

Renders the module-level `_HTML_TEMPLATE` string using `jinja2.Template`.  The
template receives the following context variables:

| Variable | Type | Description |
|---|---|---|
| `title_suffix` | `str` | `" — <project_name>"` or `""` |
| `generated_at` | `str` | Formatted as `YYYY-MM-DD HH:MM UTC` |
| `total` | `int` | `report.total_dependencies` |
| `license_count` | `int` | Number of unique SPDX IDs in `license_summary` |
| `error_count` | `int` | Number of `ERROR`-severity conflicts |
| `warn_count` | `int` | Number of `WARNING`-severity conflicts |
| `conflicts` | `list[LicenseConflict]` | Full list of conflicts |
| `license_summary` | `list[tuple[str, int]]` | License counts sorted descending |
| `unknown` | `list[str]` | `report.unknown_licenses` |
