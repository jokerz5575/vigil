# =============================================================================
# Vigil — Developer Makefile
# =============================================================================
#
# MAKEFILE RUNDOWN
# ----------------
# This Makefile automates the full development lifecycle of the Vigil monorepo.
# All three packages (vigil-core, vigil-licenses, vigil-cli) are installed in
# *editable* mode so local source changes take effect immediately without a
# reinstall step.
#
# RECOMMENDED FIRST-TIME SETUP
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   python3 -m venv .venv
#   source .venv/bin/activate     # Linux / macOS
#   .venv\Scripts\activate        # Windows
#   make install
#   make test
#
# DAILY DEVELOPMENT WORKFLOW
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   make test-fast       Fastest feedback — stops at the first failure (-x)
#   make lint            Catch style issues before committing (ruff)
#   make test-cov        Full picture with per-line coverage report
#
# BEFORE OPENING A PULL REQUEST
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   make check           Runs lint + typecheck in one step
#   make test-cov        Ensure overall coverage hasn't dropped below 90 %
#
# DOCUMENTATION
# ~~~~~~~~~~~~~
#   make docs-serve      Live-reload local preview at http://127.0.0.1:8000
#   make docs-build      Build the static site into site/
#   make docs-deploy     Push the built site to the gh-pages branch (CI does
#                        this automatically on every master push)
#
# RELEASING
# ~~~~~~~~~
#   make build           Build distributable wheels for all three packages
#                        (wheels land in vigil-*/dist/)
#
# CLEANING UP
# ~~~~~~~~~~~
#   make clean           Remove __pycache__, .pytest_cache, htmlcov, dist,
#                        .coverage, coverage.xml, test-results.xml and all
#                        *.pyc files
#
# =============================================================================
# TEST SCENARIOS
# =============================================================================
#
# The full test suite lives in tests/ and is split into six focused modules
# plus the original test_vigil.py.  Run the full suite with:
#
#   make test            (verbose, short traceback)
#   make test-cov        (same + coverage report)
#   make test-fast       (stop on first failure)
#
# To run a single module:
#   pytest tests/test_license_db.py -v
#
# To run a single class or test:
#   pytest tests/test_scanner.py::TestLicenseScannerMocked::test_blocked_license_raises_error -v
#
# ---------------------------------------------------------------------------
# tests/test_license_db.py  (173 tests)
# ---------------------------------------------------------------------------
#   TestGet
#     ✓ All 14 built-in SPDX IDs are retrievable from the database
#     ✓ spdx_id field on the returned object matches the lookup key
#     ✓ LicenseFamily is correct for every known license
#     ✓ osi_approved flag is correct (SSPL=False, CC0=False, MIT=True …)
#     ✓ fsf_libre flag is correct (SSPL=False, MIT=True …)
#     ✓ allows_commercial_use flag is correct (SSPL=False, all others=True)
#     ✓ network_clause flag is set only on AGPL-3.0 and SSPL-1.0
#     ✓ Public-domain licenses (Unlicense, CC0-1.0) require no attribution
#     ✓ get() returns None for unknown, empty, or wrong-case inputs
#   TestNormalize
#     ✓ Exact SPDX IDs pass through unchanged (all 14)
#     ✓ All 24 aliases in _LICENSE_ALIASES are resolved correctly
#     ✓ Normalization is case-insensitive for aliases
#     ✓ Leading / trailing whitespace is stripped before matching
#     ✓ Returns None for unknown strings and empty input
#   TestResolve
#     ✓ resolve() returns a LicenseInfo for known aliases
#     ✓ resolve() returns None for unknown strings
#   TestCheckConflict
#     ✓ Blocked license → ConflictSeverity.ERROR; reason mentions the SPDX ID
#     ✓ Empty / None block list does not block anything
#     ✓ License absent from allow list → ERROR
#     ✓ License present in allow list → None (no conflict)
#     ✓ Empty allow list [] is falsy → no allow-list restriction
#     ✓ Block takes priority when a license is in both allow and block
#     ✓ SSPL-1.0 without any policy → ERROR  (bug-fix: was previously WARNING)
#     ✓ SSPL-1.0 with explicit block → ERROR
#     ✓ SSPL-1.0 in allow list is still an ERROR (SSPL guard fires first)
#     ✓ AGPL-3.0 without any policy → WARNING (network-copyleft clause)
#     ✓ AGPL-3.0 warning reason mentions "network"
#     ✓ AGPL-3.0 in allow list still generates WARNING
#     ✓ Permissive licenses (MIT, Apache-2.0, BSD-3-Clause, ISC) → None
#     ✓ Strong copyleft (GPL-2.0, GPL-3.0) without policy → None
#     ✓ Completely unknown SPDX not in block or allow → None
#     ✓ Package name and license SPDX are preserved in conflict object
#   TestAllSpdxIds
#     ✓ Returns a plain list
#     ✓ Contains at least 14 entries
#     ✓ All 14 expected IDs are present
#     ✓ All values are strings
#     ✓ No duplicates
#     ✓ Every returned ID is retrievable via get()
#
# ---------------------------------------------------------------------------
# tests/test_models.py  (81 tests)
# ---------------------------------------------------------------------------
#   TestLicenseInfo
#     ✓ is_permissive() is True only for PERMISSIVE family
#     ✓ is_copyleft() is True for WEAK / STRONG / NETWORK copyleft families
#     ✓ All 7 LicenseFamily values covered by parametrized tests
#     ✓ Default field values match spec (osi_approved=False, url=None, …)
#   TestDependencyInfo
#     ✓ display_name property formats as "name==version"
#     ✓ Default fields are None / True as specified
#     ✓ Optional fields (homepage, author, description) accept values
#   TestComplianceReport
#     ✓ has_errors is True when any conflict has severity ERROR
#     ✓ has_errors is False when conflicts are only WARNINGs
#     ✓ has_warnings is True / False accordingly
#     ✓ Both flags can be True simultaneously (mixed-severity report)
#     ✓ Empty report has zero counts and False flags
#     ✓ license_families() groups packages by family string
#     ✓ Deps without license_info are excluded from license_families()
#
# ---------------------------------------------------------------------------
# tests/test_scanner.py  (68 tests)
# ---------------------------------------------------------------------------
#   TestLicensePolicy
#     ✓ Default policy has allow=None, block=[], warn=[], fail_on_unknown=False
#     ✓ from_dict() with full nested {"policy": {…}} structure
#     ✓ from_dict() with partial data (missing keys use defaults)
#     ✓ from_dict() with flat structure (no "policy" wrapper)
#     ✓ from_yaml() loads a real YAML file into a LicensePolicy object
#     ✓ from_yaml() raises FileNotFoundError for a missing path
#   TestLicenseScannerMocked
#     ✓ All-permissive deps → no conflicts at all
#     ✓ Blocked dep → ERROR with correct package name and SPDX ID
#     ✓ Dep in warn list → WARNING (not ERROR)
#     ✓ warn list overrides missing-from-allow: dep in warn but not allow → WARNING
#     ✓ Allow list: dep in list → no conflict
#     ✓ Allow list: dep not in list → ERROR
#     ✓ Unknown license with fail_on_unknown=False → no error, added to unknown_licenses
#     ✓ Unknown license with fail_on_unknown=True → ERROR conflict
#     ✓ AGPL-3.0 with no explicit policy → WARNING
#     ✓ license_summary counts are correct (MIT×2, Apache×1, etc.)
#     ✓ Multiple deps produce multiple conflicts with correct severities
#     ✓ is_direct / is_direct=False → correct direct_dependencies count
#     ✓ project_name is passed through to the report
#     ✓ Empty dep list → 0 conflicts, 0 dependencies
#   TestLicenseScannerRealInstall
#     ✓ scan() on real environment completes without raising
#     ✓ scan() with a requirements.txt file finds at least 1 package
#
# ---------------------------------------------------------------------------
# tests/test_reporter.py  (57 tests)
# ---------------------------------------------------------------------------
#   TestJSONReport
#     ✓ _render_json() returns valid JSON (parseable by json.loads)
#     ✓ JSON contains required top-level keys
#     ✓ project_name value is preserved
#     ✓ conflicts array has correct length and per-entry fields
#     ✓ severity is serialised as lowercase string ("error" / "warning")
#     ✓ generate_report() with JSON format returns the same string
#     ✓ generate_report() with output_path writes file; file contains valid JSON
#   TestHTMLReport
#     ✓ _render_html() returns a non-empty string
#     ✓ Output contains <!DOCTYPE html>
#     ✓ Project name appears in the rendered HTML
#     ✓ Package name and SPDX ID appear when there are conflicts
#     ✓ "No license conflicts" message appears for conflict-free reports
#     ✓ generate_report() with HTML format returns the HTML string
#     ✓ generate_report() with output_path writes the file
#   TestTerminalReport
#     ✓ generate_report() with TERMINAL format returns ""
#     ✓ Does not raise for empty / error / warning reports
#   TestReportFormat
#     ✓ Enum string values: TERMINAL=="terminal", JSON=="json", HTML=="html"
#
# ---------------------------------------------------------------------------
# tests/test_package_resolver.py  (35 tests)
# ---------------------------------------------------------------------------
#   TestResolveInstalled
#     ✓ Returns a list of DependencyInfo objects
#     ✓ Every item has a non-empty name and version
#     ✓ pytest itself is present in the results
#     ✓ pypi_url (when set) contains "pypi.org/project"
#   TestResolveFromRequirements
#     ✓ Known installed packages are resolved (pytest, pydantic)
#     ✓ All returned items have is_direct=True
#     ✓ Unknown packages get version="unknown"
#     ✓ Comment lines and blank lines are ignored
#     ✓ == version pins are stripped (pytest==8.0.0 → name="pytest")
#     ✓ >= version constraints are stripped (pydantic>=2.0 → name="pydantic")
#   TestFromDistribution
#     ✓ Real pydantic distribution → DependencyInfo with name="pydantic"
#     ✓ Custom LicenseDatabase is stored as resolver._db
#
# ---------------------------------------------------------------------------
# tests/test_policy_yaml.py  (47 tests)
# ---------------------------------------------------------------------------
#   TestVigilYamlStructure
#     ✓ vigil.yaml exists on disk
#     ✓ Loads as valid YAML (non-None dict)
#     ✓ Has top-level "policy" key
#     ✓ Has "allow", "block", "warn" sub-keys under "policy"
#     ✓ Every entry in each list is a plain string
#     ✓ fail_on_unknown (if present) is a bool
#   TestVigilYamlContent
#     ✓ allow contains MIT, Apache-2.0, BSD-3-Clause, ISC, Unlicense, CC0-1.0
#     ✓ block contains GPL-2.0, GPL-3.0, AGPL-3.0, SSPL-1.0
#     ✓ warn contains LGPL-2.1, LGPL-3.0, MPL-2.0
#     ✓ No duplicate entries in allow, block, or warn
#     ✓ allow ∩ block = ∅  (completely disjoint)
#     ✓ warn ∩ block = ∅   (completely disjoint)
#     ✓ allow ∩ warn = ∅   (completely disjoint)
#     ✓ allow has ≥ 30 entries (extended policy)
#     ✓ block contains the -only / -or-later GPL variants
#     ✓ warn contains at least one EPL variant and MPL-2.0
#   TestVigilYamlLoadedAsPolicy
#     ✓ LicensePolicy.from_yaml(vigil_yaml_path) loads without error
#     ✓ Loaded policy has ≥ 30 allow entries containing "MIT"
#     ✓ Loaded policy block contains "GPL-3.0"
#     ✓ db.check_conflict("gpl-lib", "GPL-3.0", policy_block=…) → ERROR
#     ✓ db.check_conflict("safe-lib", "MIT",    policy_allow=…) → None
#
# =============================================================================

PYTHON  ?= python3
PIP     ?= pip
PYTEST  ?= pytest
RUFF    ?= ruff
MYPY    ?= mypy
HATCH   ?= hatch
MKDOCS  ?= mkdocs

SRC_TREES  = vigil-core/src vigil-licenses/src vigil-cli/src
TEST_DIR   = tests
COV_PKGS   = --cov=vigil_core --cov=vigil_licenses

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "  Vigil Developer Makefile"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Run 'make install' first, then 'make test' to verify the setup."
	@echo ""

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

.PHONY: install
install: ## Install all packages in editable mode with all dev dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e "vigil-core[dev]"
	$(PIP) install -e "vigil-licenses[dev]"
	$(PIP) install -e "vigil-cli[dev]"
	$(PIP) install pytest pytest-cov pyyaml
	@echo ""
	@echo "  ✓  All packages installed.  Run 'make test' to verify."
	@echo ""

.PHONY: install-docs
install-docs: ## Install MkDocs Material and extensions for local doc preview
	$(PIP) install "mkdocs-material>=9.5" "pymdown-extensions>=10.0"

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run the full test suite (verbose, short traceback)
	$(PYTEST) $(TEST_DIR) -v --tb=short

.PHONY: test-fast
test-fast: ## Run tests and stop on the very first failure (-x flag)
	$(PYTEST) $(TEST_DIR) -v --tb=short -x

.PHONY: test-cov
test-cov: ## Run tests with terminal + HTML coverage report (htmlcov/index.html)
	$(PYTEST) $(TEST_DIR) -v --tb=short \
		$(COV_PKGS) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov
	@echo ""
	@echo "  ✓  HTML coverage report written to htmlcov/index.html"
	@echo ""

.PHONY: test-xml
test-xml: ## Run tests and emit JUnit XML + coverage XML (for CI artifact upload)
	$(PYTEST) $(TEST_DIR) -v --tb=short \
		$(COV_PKGS) \
		--cov-report=xml:coverage.xml \
		--junitxml=test-results.xml

.PHONY: test-module
test-module: ## Run a single test module: make test-module MOD=test_license_db
	$(PYTEST) $(TEST_DIR)/$(MOD).py -v --tb=short

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------

.PHONY: lint
lint: ## Check all source trees with ruff (read-only, no modifications)
	$(RUFF) check $(SRC_TREES)

.PHONY: format
format: ## Auto-format all source trees with ruff
	$(RUFF) format $(SRC_TREES)

.PHONY: typecheck
typecheck: ## Run mypy static type checker over all source trees
	$(MYPY) $(SRC_TREES)

.PHONY: check
check: lint typecheck ## Run all static analysis in one step (lint + typecheck)

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

.PHONY: docs-serve
docs-serve: ## Start a live-reload local preview at http://127.0.0.1:8000
	@echo "  → Open http://127.0.0.1:8000 in your browser (Ctrl-C to stop)"
	$(MKDOCS) serve

.PHONY: docs-build
docs-build: ## Build the static site into site/ (does not deploy)
	$(MKDOCS) build --clean
	@echo ""
	@echo "  ✓  Static site written to site/"
	@echo ""

.PHONY: docs-deploy
docs-deploy: ## Force-push the built site to the gh-pages branch
	$(MKDOCS) gh-deploy --force --clean
	@echo ""
	@echo "  ✓  Documentation deployed to https://jokerz5575.github.io/vigil/"
	@echo ""

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

.PHONY: build
build: ## Build distributable wheels for all three packages via hatch
	$(PIP) install --quiet hatch
	cd vigil-core     && $(HATCH) build
	cd vigil-licenses && $(HATCH) build
	cd vigil-cli      && $(HATCH) build
	@echo ""
	@echo "  ✓  Wheels written to vigil-core/dist, vigil-licenses/dist, vigil-cli/dist"
	@echo ""

# ---------------------------------------------------------------------------
# Dogfood — scan Vigil's own dependencies with Vigil
# ---------------------------------------------------------------------------

.PHONY: scan
scan: ## Run a license compliance scan against Vigil's own environment
	vigil scan --policy vigil.yaml

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove all build / cache / coverage artifacts
	find . -type d -name __pycache__   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov       -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name site          -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist          -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc"               -delete                        2>/dev/null || true
	find . -name ".coverage"           -delete                        2>/dev/null || true
	find . -name "coverage.xml"        -delete                        2>/dev/null || true
	find . -name "test-results.xml"    -delete                        2>/dev/null || true
	@echo "  ✓  Clean."
