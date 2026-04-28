"""
Report generator for Vigil compliance reports.
Supports terminal (rich), JSON, and HTML output.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from vigil_core.models import ComplianceReport, ConflictSeverity


class ReportFormat(str, Enum):
    TERMINAL = "terminal"
    JSON = "json"
    HTML = "html"


def generate_report(
    report: ComplianceReport,
    fmt: ReportFormat = ReportFormat.TERMINAL,
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Generate a compliance report in the specified format.

    Args:
        report: The ComplianceReport to render.
        fmt: Output format (terminal, json, html).
        output_path: If provided, write the report to this file path.

    Returns:
        The rendered report as a string.
    """
    if fmt == ReportFormat.JSON:
        content = _render_json(report)
    elif fmt == ReportFormat.HTML:
        content = _render_html(report)
    else:
        _render_terminal(report)
        return ""  # Terminal rendering is done via rich directly

    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")

    return content


def _render_terminal(report: ComplianceReport) -> None:
    """Render a rich terminal report."""
    from rich.console import Console
    from rich.table import Table
    from rich import box
    from rich.panel import Panel
    from rich.text import Text

    console = Console()

    # Header
    title = f"Vigil Compliance Report"
    if report.project_name:
        title += f" — {report.project_name}"
    console.print()
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))

    # Summary
    console.print(f"\n[bold]Dependencies scanned:[/bold] {report.total_dependencies}")
    console.print(f"[bold]Unique licenses found:[/bold] {len(report.license_summary)}")

    if report.unknown_licenses:
        console.print(
            f"[bold yellow]⚠ Unknown licenses:[/bold yellow] {len(report.unknown_licenses)}"
        )

    # License breakdown
    if report.license_summary:
        console.print()
        table = Table(title="License Breakdown", box=box.ROUNDED, show_lines=True)
        table.add_column("SPDX License", style="cyan")
        table.add_column("Packages", justify="right")

        for spdx, count in sorted(
            report.license_summary.items(), key=lambda x: -x[1]
        ):
            table.add_row(spdx, str(count))
        console.print(table)

    # Conflicts
    if not report.conflicts:
        console.print("\n[bold green]✓ No license conflicts detected.[/bold green]\n")
        return

    console.print()
    conflict_table = Table(
        title="License Issues", box=box.ROUNDED, show_lines=True
    )
    conflict_table.add_column("Severity", width=10)
    conflict_table.add_column("Package", style="cyan")
    conflict_table.add_column("License")
    conflict_table.add_column("Reason")
    conflict_table.add_column("Recommendation")

    for conflict in report.conflicts:
        if conflict.severity == ConflictSeverity.ERROR:
            sev = Text("ERROR", style="bold red")
        elif conflict.severity == ConflictSeverity.WARNING:
            sev = Text("WARN", style="bold yellow")
        else:
            sev = Text("INFO", style="bold blue")

        conflict_table.add_row(
            sev,
            conflict.package,
            conflict.license_spdx,
            conflict.reason,
            conflict.recommendation or "—",
        )

    console.print(conflict_table)

    if report.has_errors:
        console.print(
            "\n[bold red]✗ Compliance check FAILED — errors must be resolved.[/bold red]\n"
        )
    elif report.has_warnings:
        console.print(
            "\n[bold yellow]⚠ Compliance check passed with warnings.[/bold yellow]\n"
        )


def _render_json(report: ComplianceReport) -> str:
    return report.model_dump_json(indent=2)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vigil Compliance Report</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #1a1a2e; }
  h1 { color: #0a3d62; } h2 { color: #1e3799; border-bottom: 2px solid #e0e0e0; padding-bottom: 0.4rem; }
  table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
  th { background: #1e3799; color: white; padding: 0.6rem 1rem; text-align: left; }
  td { padding: 0.5rem 1rem; border-bottom: 1px solid #e0e0e0; }
  tr:hover { background: #f5f6fa; }
  .badge { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
  .error { background: #ff4757; color: white; }
  .warning { background: #ffa502; color: white; }
  .info { background: #1e90ff; color: white; }
  .ok { color: #2ed573; font-weight: bold; }
  .summary { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }
  .stat { background: #f5f6fa; border-radius: 8px; padding: 1rem 1.5rem; text-align: center; }
  .stat-num { font-size: 2rem; font-weight: bold; color: #1e3799; }
  .stat-label { font-size: 0.85rem; color: #636e72; }
  footer { margin-top: 2rem; font-size: 0.8rem; color: #b2bec3; text-align: center; }
</style>
</head>
<body>
<h1>🛡️ Vigil Compliance Report{{ title_suffix }}</h1>
<p>Generated: {{ generated_at }}</p>
<div class="summary">
  <div class="stat"><div class="stat-num">{{ total }}</div><div class="stat-label">Dependencies</div></div>
  <div class="stat"><div class="stat-num">{{ license_count }}</div><div class="stat-label">Unique Licenses</div></div>
  <div class="stat"><div class="stat-num">{{ error_count }}</div><div class="stat-label">Errors</div></div>
  <div class="stat"><div class="stat-num">{{ warn_count }}</div><div class="stat-label">Warnings</div></div>
</div>
{% if conflicts %}
<h2>License Issues</h2>
<table>
  <tr><th>Severity</th><th>Package</th><th>License</th><th>Reason</th><th>Recommendation</th></tr>
  {% for c in conflicts %}
  <tr>
    <td><span class="badge {{ c.severity }}">{{ c.severity.upper() }}</span></td>
    <td><strong>{{ c.package }}</strong></td>
    <td>{{ c.license_spdx }}</td>
    <td>{{ c.reason }}</td>
    <td>{{ c.recommendation or '—' }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p class="ok">✓ No license conflicts detected.</p>
{% endif %}
<h2>License Breakdown</h2>
<table>
  <tr><th>SPDX License</th><th>Packages</th></tr>
  {% for spdx, count in license_summary %}
  <tr><td>{{ spdx }}</td><td>{{ count }}</td></tr>
  {% endfor %}
</table>
{% if unknown %}
<h2>Unknown Licenses ({{ unknown|length }})</h2>
<ul>{% for u in unknown %}<li>{{ u }}</li>{% endfor %}</ul>
{% endif %}
<footer>Generated by <strong>Vigil</strong> — Open source compliance, automated.</footer>
</body>
</html>"""


def _render_html(report: ComplianceReport) -> str:
    from jinja2 import Template

    tpl = Template(_HTML_TEMPLATE)
    return tpl.render(
        title_suffix=f" — {report.project_name}" if report.project_name else "",
        generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        total=report.total_dependencies,
        license_count=len(report.license_summary),
        error_count=sum(
            1 for c in report.conflicts if c.severity == ConflictSeverity.ERROR
        ),
        warn_count=sum(
            1 for c in report.conflicts if c.severity == ConflictSeverity.WARNING
        ),
        conflicts=report.conflicts,
        license_summary=sorted(
            report.license_summary.items(), key=lambda x: -x[1]
        ),
        unknown=report.unknown_licenses,
    )
