"""
vigil-licenses: License conflict detection and compliance reporting.
"""
from vigil_licenses.scanner import LicenseScanner
from vigil_licenses.reporter import ReportFormat, generate_report

__version__ = "0.1.0"
__all__ = ["LicenseScanner", "ReportFormat", "generate_report"]
