# =============================================================================
# Vigil — Developer Makefile
# =============================================================================
# Usage:
#   make install      Install all packages in editable mode + dev dependencies
#   make test         Run the full test suite
#   make test-cov     Run tests with an HTML + terminal coverage report
#   make test-fast    Run tests, stop on first failure (-x)
#   make lint         Lint all source trees with ruff
#   make format       Auto-format all source trees with ruff
#   make typecheck    Static type-check with mypy
#   make build        Build distributable wheels for all packages
#   make clean        Remove all build/cache artifacts
#   make help         Show this help message
#
# Prerequisites:
#   Python 3.9+ must be on PATH.  Create and activate a virtualenv first:
#
#       python3 -m venv .venv
#       source .venv/bin/activate   # Linux / macOS
#       .venv\Scripts\activate      # Windows
#
#   Then run:  make install
# =============================================================================

PYTHON  ?= python3
PIP     ?= pip
PYTEST  ?= pytest
RUFF    ?= ruff
MYPY    ?= mypy
HATCH   ?= hatch

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
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
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

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run the full test suite
	$(PYTEST) $(TEST_DIR) -v --tb=short

.PHONY: test-fast
test-fast: ## Run tests and stop on the first failure
	$(PYTEST) $(TEST_DIR) -v --tb=short -x

.PHONY: test-cov
test-cov: ## Run tests with terminal + HTML coverage report
	$(PYTEST) $(TEST_DIR) -v --tb=short \
		$(COV_PKGS) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov
	@echo ""
	@echo "  ✓  HTML coverage report written to htmlcov/index.html"
	@echo ""

.PHONY: test-xml
test-xml: ## Run tests and emit JUnit XML (useful in CI)
	$(PYTEST) $(TEST_DIR) -v --tb=short \
		$(COV_PKGS) \
		--cov-report=xml:coverage.xml \
		--junitxml=test-results.xml

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------

.PHONY: lint
lint: ## Check all source trees with ruff (no modifications)
	$(RUFF) check $(SRC_TREES)

.PHONY: format
format: ## Auto-format all source trees with ruff
	$(RUFF) format $(SRC_TREES)

.PHONY: typecheck
typecheck: ## Run mypy static type checker over all source trees
	$(MYPY) $(SRC_TREES)

.PHONY: check
check: lint typecheck ## Run all static analysis (lint + typecheck)

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

.PHONY: build
build: ## Build distributable wheels for all three packages
	$(PIP) install --quiet hatch
	cd vigil-core    && $(HATCH) build
	cd vigil-licenses && $(HATCH) build
	cd vigil-cli     && $(HATCH) build
	@echo ""
	@echo "  ✓  Wheels written to vigil-core/dist, vigil-licenses/dist, vigil-cli/dist"
	@echo ""

# ---------------------------------------------------------------------------
# Dogfood — scan Vigil's own dependencies
# ---------------------------------------------------------------------------

.PHONY: scan
scan: ## Run a license compliance scan against Vigil's own environment
	vigil scan --policy vigil.yaml

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove all build / cache artifacts
	find . -type d -name __pycache__   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov       -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist          -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc"               -delete                        2>/dev/null || true
	find . -name ".coverage"           -delete                        2>/dev/null || true
	find . -name "coverage.xml"        -delete                        2>/dev/null || true
	find . -name "test-results.xml"    -delete                        2>/dev/null || true
	@echo "  ✓  Clean."
