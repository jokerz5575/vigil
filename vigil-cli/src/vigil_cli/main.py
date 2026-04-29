"""
Vigil CLI — Open source compliance, automated.
"""

# ruff: noqa: B008
from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="vigil",
    help="🛡️  Vigil — Open source compliance, automated.",
    add_completion=True,
    rich_markup_mode="rich",
)
licenses_app = typer.Typer(help="License compliance commands.")
app.add_typer(licenses_app, name="licenses")

console = Console()


class OutputFormat(str, Enum):
    terminal = "terminal"
    json = "json"
    html = "html"


@app.command()
def scan(
    requirements: Path | None = typer.Option(
        None,
        "--requirements",
        "-r",
        help="Path to requirements.txt. Defaults to scanning the current environment.",
    ),
    policy: Path | None = typer.Option(
        None,
        "--policy",
        "-p",
        help="Path to vigil.yaml policy file.",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.terminal,
        "--format",
        "-f",
        help="Output format.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write report to this file.",
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        help="Project name to include in the report.",
    ),
    fail_on_warning: bool = typer.Option(
        False,
        "--fail-on-warning",
        help="Exit with code 1 on warnings as well as errors.",
    ),
    github_token: str | None = typer.Option(
        None,
        "--github-token",
        envvar="GITHUB_TOKEN",
        help=(
            "GitHub personal-access token used to look up licenses for packages "
            "that have no license metadata on PyPI. Falls back to the GITHUB_TOKEN "
            "environment variable. Unauthenticated requests are rate-limited to "
            "60/hour; authenticated requests to 5,000/hour."
        ),
    ),
) -> None:
    """
    Scan project dependencies for license compliance issues.

    Examples:

        vigil scan

        vigil scan --requirements requirements.txt --policy vigil.yaml

        vigil scan --format html --output report.html

        vigil scan --github-token ghp_... --policy vigil.yaml
    """
    from vigil_licenses.reporter import ReportFormat, generate_report
    from vigil_licenses.scanner import LicensePolicy, LicenseScanner

    # Load policy
    lic_policy = None
    if policy:
        if not policy.exists():
            console.print(f"[red]Policy file not found: {policy}[/red]")
            raise typer.Exit(1)
        lic_policy = LicensePolicy.from_yaml(policy)

    scanner = LicenseScanner(policy=lic_policy, github_token=github_token)

    with console.status("[bold cyan]Scanning dependencies...[/bold cyan]"):
        report = scanner.scan(
            requirements_file=str(requirements) if requirements else None,
            project_name=project,
        )

    fmt_map = {
        OutputFormat.terminal: ReportFormat.TERMINAL,
        OutputFormat.json: ReportFormat.JSON,
        OutputFormat.html: ReportFormat.HTML,
    }

    generate_report(report, fmt=fmt_map[format], output_path=output)

    if output:
        console.print(f"\n[green]Report written to {output}[/green]")

    # Exit codes for CI integration
    if report.has_errors:
        raise typer.Exit(1)
    if fail_on_warning and report.has_warnings:
        raise typer.Exit(1)


@licenses_app.command("check")
def licenses_check(
    requirements: Path | None = typer.Option(None, "--requirements", "-r"),
    policy: Path | None = typer.Option(None, "--policy", "-p"),
) -> None:
    """Check for license conflicts (alias for `vigil scan`)."""
    # Delegate to scan
    from vigil_licenses.reporter import ReportFormat, generate_report
    from vigil_licenses.scanner import LicensePolicy, LicenseScanner

    lic_policy = None
    if policy and policy.exists():
        lic_policy = LicensePolicy.from_yaml(policy)

    scanner = LicenseScanner(policy=lic_policy)
    report = scanner.scan(requirements_file=str(requirements) if requirements else None)
    generate_report(report, fmt=ReportFormat.TERMINAL)

    if report.has_errors:
        raise typer.Exit(1)


@licenses_app.command("report")
def licenses_report(
    requirements: Path | None = typer.Option(None, "--requirements", "-r"),
    format: OutputFormat = typer.Option(OutputFormat.html, "--format", "-f"),
    output: Path = typer.Option(Path("vigil-report.html"), "--output", "-o"),
    project: str | None = typer.Option(None, "--project"),
) -> None:
    """Generate a standalone compliance report file."""
    from vigil_licenses.reporter import ReportFormat, generate_report
    from vigil_licenses.scanner import LicenseScanner

    scanner = LicenseScanner()
    with console.status("[bold cyan]Scanning...[/bold cyan]"):
        report = scanner.scan(
            requirements_file=str(requirements) if requirements else None,
            project_name=project,
        )

    fmt_map = {
        OutputFormat.terminal: ReportFormat.TERMINAL,
        OutputFormat.json: ReportFormat.JSON,
        OutputFormat.html: ReportFormat.HTML,
    }
    generate_report(report, fmt=fmt_map[format], output_path=output)
    console.print(f"[green]✓ Report saved to {output}[/green]")


@app.command()
def version() -> None:
    """Show the Vigil version."""
    from vigil_cli import __version__

    console.print(f"vigil [cyan]{__version__}[/cyan]")


if __name__ == "__main__":
    app()
