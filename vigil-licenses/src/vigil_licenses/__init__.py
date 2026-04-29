"""
vigil-licenses: License conflict detection and compliance reporting.
"""
from vigil_licenses.reporter import ReportFormat, generate_report
from vigil_licenses.scanner import LicenseScanner

__version__ = "1.0.0"
__all__ = ["LicenseScanner", "ReportFormat", "generate_report"]
