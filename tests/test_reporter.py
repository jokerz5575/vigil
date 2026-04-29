"""
Comprehensive tests for the Vigil report generator.

Covers:
- JSON rendering: valid JSON, expected keys, field values, file output
- HTML rendering: DOCTYPE, project name, conflict details, empty-report text, file output
- Terminal rendering: returns empty string, does not raise
- ReportFormat enum string values
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from vigil_core.models import ConflictSeverity, LicenseConflict, LicenseFamily
from vigil_licenses.reporter import (
    ReportFormat,
    _render_html,
    _render_json,
    generate_report,
)

# ---------------------------------------------------------------------------
# Module-level report fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_report(report_factory):
    """A report with no dependencies and no conflicts."""
    return report_factory(deps=[], conflicts=[], project_name="empty-project")


@pytest.fixture
def report_with_errors(report_factory, dep_factory):
    """A report containing a single ERROR-level conflict."""
    dep = dep_factory("bad-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT)
    conflict = LicenseConflict(
        package="bad-lib",
        license_spdx="GPL-3.0",
        severity=ConflictSeverity.ERROR,
        reason="GPL-3.0 is explicitly blocked by your policy.",
        recommendation="Replace bad-lib with a permissively licensed alternative.",
    )
    return report_factory(deps=[dep], conflicts=[conflict], project_name="error-project")


@pytest.fixture
def report_with_warnings(report_factory, dep_factory):
    """A report containing a single WARNING-level conflict."""
    dep = dep_factory("lgpl-lib", spdx="LGPL-2.1", family=LicenseFamily.WEAK_COPYLEFT)
    conflict = LicenseConflict(
        package="lgpl-lib",
        license_spdx="LGPL-2.1",
        severity=ConflictSeverity.WARNING,
        reason="LGPL-2.1 is flagged for review in your policy.",
        recommendation=None,
    )
    return report_factory(deps=[dep], conflicts=[conflict], project_name="warn-project")


@pytest.fixture
def report_multi(report_factory, dep_factory):
    """A report with multiple dependencies and mixed conflict severities."""
    deps = [
        dep_factory("gpl-lib", spdx="GPL-3.0", family=LicenseFamily.STRONG_COPYLEFT),
        dep_factory("lgpl-lib", spdx="LGPL-2.1", family=LicenseFamily.WEAK_COPYLEFT),
        dep_factory("safe-lib", spdx="MIT"),
    ]
    conflicts = [
        LicenseConflict(
            package="gpl-lib",
            license_spdx="GPL-3.0",
            severity=ConflictSeverity.ERROR,
            reason="GPL-3.0 is blocked.",
        ),
        LicenseConflict(
            package="lgpl-lib",
            license_spdx="LGPL-2.1",
            severity=ConflictSeverity.WARNING,
            reason="LGPL-2.1 needs review.",
        ),
    ]
    return report_factory(deps=deps, conflicts=conflicts, project_name="multi-project")


# ---------------------------------------------------------------------------
# TestJSONReport
# ---------------------------------------------------------------------------


class TestJSONReport:
    """Tests for JSON report rendering."""

    def test_render_json_returns_valid_json_string(self, report_with_errors):
        result = _render_json(report_with_errors)
        parsed = json.loads(result)  # must not raise
        assert isinstance(parsed, dict)

    def test_render_json_has_total_dependencies_key(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert "total_dependencies" in parsed

    def test_render_json_has_conflicts_key(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert "conflicts" in parsed

    def test_render_json_has_license_summary_key(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert "license_summary" in parsed

    def test_render_json_has_project_name_key(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert "project_name" in parsed

    def test_render_json_project_name_value_preserved(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert parsed["project_name"] == "error-project"

    def test_render_json_project_name_none_for_unnamed_report(self, report_factory):
        report = report_factory(project_name=None)
        parsed = json.loads(_render_json(report))
        assert parsed["project_name"] is None

    def test_render_json_conflicts_array_correct_length(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert len(parsed["conflicts"]) == 1

    def test_render_json_conflict_has_package_field(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        conflict = parsed["conflicts"][0]
        assert "package" in conflict
        assert conflict["package"] == "bad-lib"

    def test_render_json_conflict_has_license_spdx_field(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        conflict = parsed["conflicts"][0]
        assert "license_spdx" in conflict
        assert conflict["license_spdx"] == "GPL-3.0"

    def test_render_json_conflict_severity_is_string_error(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        conflict = parsed["conflicts"][0]
        assert "severity" in conflict
        assert conflict["severity"] == "error"

    def test_render_json_conflict_severity_is_string_warning(self, report_with_warnings):
        parsed = json.loads(_render_json(report_with_warnings))
        conflict = parsed["conflicts"][0]
        assert conflict["severity"] == "warning"

    def test_render_json_total_dependencies_correct(self, report_with_errors):
        parsed = json.loads(_render_json(report_with_errors))
        assert parsed["total_dependencies"] == 1

    def test_generate_report_json_returns_same_as_render_json(self, report_with_errors):
        direct = _render_json(report_with_errors)
        via_generate = generate_report(report_with_errors, fmt=ReportFormat.JSON)
        assert json.loads(direct) == json.loads(via_generate)

    def test_generate_report_json_writes_file(self, report_with_errors, tmp_path):
        out = tmp_path / "report.json"
        generate_report(report_with_errors, fmt=ReportFormat.JSON, output_path=out)
        assert out.exists()

    def test_generate_report_json_file_contains_valid_json(self, report_with_errors, tmp_path):
        out = tmp_path / "report.json"
        generate_report(report_with_errors, fmt=ReportFormat.JSON, output_path=out)
        parsed = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)

    def test_generate_report_json_file_has_project_name(self, report_with_errors, tmp_path):
        out = tmp_path / "report.json"
        generate_report(report_with_errors, fmt=ReportFormat.JSON, output_path=out)
        parsed = json.loads(out.read_text(encoding="utf-8"))
        assert parsed["project_name"] == "error-project"

    def test_generate_report_json_empty_report(self, empty_report):
        result = generate_report(empty_report, fmt=ReportFormat.JSON)
        parsed = json.loads(result)
        assert parsed["total_dependencies"] == 0
        assert parsed["conflicts"] == []

    def test_render_json_multi_conflicts_length(self, report_multi):
        parsed = json.loads(_render_json(report_multi))
        assert len(parsed["conflicts"]) == 2


# ---------------------------------------------------------------------------
# TestHTMLReport
# ---------------------------------------------------------------------------


class TestHTMLReport:
    """Tests for HTML report rendering."""

    def test_render_html_returns_non_empty_string(self, report_with_errors):
        result = _render_html(report_with_errors)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_html_contains_doctype(self, report_with_errors):
        result = _render_html(report_with_errors)
        assert "<!DOCTYPE html>" in result

    def test_render_html_contains_project_name_when_present(self, report_with_errors):
        result = _render_html(report_with_errors)
        assert "error-project" in result

    def test_render_html_project_name_absent_when_none(self, report_factory, dep_factory):
        dep = dep_factory("lib", spdx="MIT")
        report = report_factory(deps=[dep], project_name=None)
        result = _render_html(report)
        assert "<!DOCTYPE html>" in result  # still valid HTML

    def test_render_html_contains_package_name_when_conflicts(self, report_with_errors):
        result = _render_html(report_with_errors)
        assert "bad-lib" in result

    def test_render_html_contains_spdx_id_when_conflicts(self, report_with_errors):
        result = _render_html(report_with_errors)
        assert "GPL-3.0" in result

    def test_render_html_empty_report_has_no_conflicts_text(self, empty_report):
        result = _render_html(empty_report)
        assert "No license conflicts" in result

    def test_render_html_with_warnings_contains_package_name(self, report_with_warnings):
        result = _render_html(report_with_warnings)
        assert "lgpl-lib" in result

    def test_render_html_with_warnings_contains_spdx_id(self, report_with_warnings):
        result = _render_html(report_with_warnings)
        assert "LGPL-2.1" in result

    def test_render_html_multi_conflicts_contains_all_packages(self, report_multi):
        result = _render_html(report_multi)
        assert "gpl-lib" in result
        assert "lgpl-lib" in result

    def test_generate_report_html_returns_same_html(self, report_with_errors):
        direct = _render_html(report_with_errors)
        via_generate = generate_report(report_with_errors, fmt=ReportFormat.HTML)
        assert direct == via_generate

    def test_generate_report_html_writes_file(self, report_with_errors, tmp_path):
        out = tmp_path / "report.html"
        generate_report(report_with_errors, fmt=ReportFormat.HTML, output_path=out)
        assert out.exists()

    def test_generate_report_html_file_contains_doctype(self, report_with_errors, tmp_path):
        out = tmp_path / "report.html"
        generate_report(report_with_errors, fmt=ReportFormat.HTML, output_path=out)
        assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")

    def test_generate_report_html_file_contains_project_name(self, report_with_errors, tmp_path):
        out = tmp_path / "report.html"
        generate_report(report_with_errors, fmt=ReportFormat.HTML, output_path=out)
        assert "error-project" in out.read_text(encoding="utf-8")

    def test_render_html_contains_html_tags(self, empty_report):
        result = _render_html(empty_report)
        assert "<html" in result
        assert "</html>" in result


# ---------------------------------------------------------------------------
# TestTerminalReport
# ---------------------------------------------------------------------------


class TestTerminalReport:
    """Tests for terminal (rich) report rendering."""

    def test_generate_report_terminal_returns_empty_string(self, empty_report):
        result = generate_report(empty_report, fmt=ReportFormat.TERMINAL)
        assert result == ""

    def test_generate_report_terminal_does_not_raise_for_empty_report(self, empty_report):
        # Must not raise
        generate_report(empty_report, fmt=ReportFormat.TERMINAL)

    def test_generate_report_terminal_does_not_raise_for_errors(self, report_with_errors):
        generate_report(report_with_errors, fmt=ReportFormat.TERMINAL)

    def test_generate_report_terminal_does_not_raise_for_warnings(self, report_with_warnings):
        generate_report(report_with_warnings, fmt=ReportFormat.TERMINAL)

    def test_generate_report_terminal_does_not_raise_for_multi(self, report_multi):
        generate_report(report_multi, fmt=ReportFormat.TERMINAL)

    def test_generate_report_terminal_returns_string_type(self, empty_report):
        result = generate_report(empty_report, fmt=ReportFormat.TERMINAL)
        assert isinstance(result, str)

    def test_generate_report_terminal_does_not_write_file(self, empty_report, tmp_path):
        # Terminal format should NOT write output_path even if provided.
        out = tmp_path / "terminal.txt"
        generate_report(empty_report, fmt=ReportFormat.TERMINAL, output_path=out)
        assert not out.exists()


# ---------------------------------------------------------------------------
# TestReportFormat
# ---------------------------------------------------------------------------


class TestReportFormat:
    """Tests for the ReportFormat enum values."""

    def test_terminal_value_is_string_terminal(self):
        assert ReportFormat.TERMINAL == "terminal"

    def test_json_value_is_string_json(self):
        assert ReportFormat.JSON == "json"

    def test_html_value_is_string_html(self):
        assert ReportFormat.HTML == "html"

    def test_terminal_is_str_subclass(self):
        assert isinstance(ReportFormat.TERMINAL, str)

    def test_json_is_str_subclass(self):
        assert isinstance(ReportFormat.JSON, str)

    def test_html_is_str_subclass(self):
        assert isinstance(ReportFormat.HTML, str)

    def test_all_three_formats_distinct(self):
        formats = {ReportFormat.TERMINAL, ReportFormat.JSON, ReportFormat.HTML}
        assert len(formats) == 3
