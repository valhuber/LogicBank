---
title: LogicBank Release Management
Description: Version bump, build (pyproject.toml), and PyPI release process for LogicBank
Usage: Read before cutting a release. See run_tests_readme.md (repo root) for testing; dev-architecture.md for how releases couple to GenAI-Logic's pinned version.
version: 1.0
changelog:
  - 1.0 (Jun 2026) - Split out of readme_dev.md (renamed to run_tests_readme.md) into system/LogicBank-Internal-Dev/, per request to separate testing docs (human-facing, repo root) from release-management docs (moved alongside the other AI-context/internal-dev docs)
---

# LogicBank Release Management

This guide covers building and releasing LogicBank using the modern pyproject.toml build system.

**Before releasing:** run the full test suite — see [run_tests_readme.md](../../run_tests_readme.md) (repo root). All tests must pass (100% success rate) before cutting a release.

**After releasing:** GenAI-Logic pins an exact LogicBank version (not floating) — see [dev-architecture.md](dev-architecture.md) → "Relationship to ApiLogicServer Dev Workspace" for the release-coupling workflow (bump here → release to PyPI → bump GL's pin → re-run BLT).

## Modern Build System (pyproject.toml)

LogicBank uses a modern Python packaging approach with `pyproject.toml` instead of the legacy `setup.py`.

### Build System Configuration

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "logicbank"
dynamic = ["version"]
dependencies = [
    "python-dateutil>=2.3,<3",
    "sqlalchemy==2.0.39",
]
```

### Version Management

- **Version Source:** `logic_bank/rule_bank/rule_bank_setup.py`
- **Current Version:** `1.30.00`
- **Format:** Semantic versioning (MAJOR.MINOR.PATCH)
- **Note:** Build system normalizes versions (e.g., `1.30.00` → `1.30.0` in filenames)

## Release Process

### 1. Pre-Release Testing

```bash
# Run comprehensive test suite
python3 run_tests.py

# Verify all tests pass (check test_summary.txt)
# Success rate should be 100.0%
```

### 2. Version Update

Update version in `logic_bank/rule_bank/rule_bank_setup.py`:

```python
__version__ = "1.31.00"  # Update as needed
```

### 3. Build Package

```bash
# Install build dependencies (choose one approach)

# Option A: Using pipx (recommended for tools)
pipx install build
pipx install twine

# Option B: Global installation (also acceptable)
pip install build twine

# Option C: In virtual environment (project-specific), with venv active:
pip install build twine

# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build package using pyproject.toml
python -m build

# Verify build outputs
ls dist/
# Should show: logicbank-1.30.0.tar.gz and logicbank-1.30.0-py3-none-any.whl
# Note: Version normalized from 1.30.00 to 1.30.0
```

### 4. Test Installation

```bash
# Test installation from wheel (use actual normalized filename)
pip install dist/logicbank-1.30.0-py3-none-any.whl

# for ApiLogicServer
cd ~/dev/ApiLogicServer/ApiLogicServer-dev/build_and_test/ApiLogicServer
. venv/bin/activate
pip install ~/dev/ApiLogicServer/ApiLogicServer-dev/org_git/LogicBank/dist/logicbank-1.30.0-py3-none-any.whl

# Or test with editable install
pip install -e .
```

### 5. Upload to PyPI

```bash
# Upload to PyPI (requires credentials)
python -m twine upload dist/*

# Or upload with skip existing (for re-runs)
python -m twine upload --skip-existing dist/*
```

## Development Installation

### For Development

```bash
# Clone repository
git clone https://github.com/valhuber/logicbank.git
cd logicbank

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests to verify installation
python3 run_tests.py
```

### Dependencies

**Core Dependencies:**
- `python-dateutil>=2.3,<3`
- `sqlalchemy==2.0.39`

**Development Dependencies:**
- `pytest>=6.0`
- `pytest-cov`
- `black` (code formatting)
- `flake8` (linting)
- `mypy` (type checking)

## Release Checklist

- [ ] All tests pass (100% success rate)
- [ ] Version updated in `rule_bank_setup.py`
- [ ] Dependencies verified in `pyproject.toml`
- [ ] Build completes successfully
- [ ] Package installs correctly
- [ ] Documentation updated if needed
- [ ] Git tag created for release
- [ ] PyPI upload successful

## Legacy Build System Notes

**Previous Approach (deprecated):**
```bash
# Old setup.py approach (no longer used)
python setup.py sdist bdist_wheel
```

**Current Approach:**
```bash
# Modern pyproject.toml approach
python -m build
```

The modern approach provides:
- Better dependency resolution
- Standardized build interface
- Improved metadata handling
- Enhanced compatibility with Python packaging tools
