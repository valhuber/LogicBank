# LogicBank Testing Guide

## Overview

The LogicBank project contains multiple example projects, each with their own LogicBank activation. When running tests, there are conflicts between different example activations, so tests must be run separately by example directory.

## Quick Test Setup (Fixed)

The VS Code test configuration has been updated to focus on the `nw` tests by default. The test directory is now correctly configured in `.vscode/settings.json`.

### Running Tests in VS Code

1. **VS Code Test Discovery**: The Test Explorer should now discover tests in `examples/nw/tests/`
2. **Running specific tests**: Use the VS Code Test Explorer UI to run individual tests or all tests in the nw example

### Running Tests via Command Line

For running tests in different example projects, use the provided test runner script:

```bash
# List all available test directories
python run_tests.py --list

# Run tests for a specific example (e.g., nw)
python run_tests.py --dir examples/nw/tests

# Run tests for banking example
python run_tests.py --dir examples/banking/tests

# Run all test directories (will run each separately to avoid conflicts)
python run_tests.py
```

## Available Test Directories

- `examples/banking/tests` - Banking transfer scenarios
- `examples/copy_children/tests` - Copy children relationships
- `examples/custom_exceptions/tests` - Custom exception handling
- `examples/insert_parent/tests` - Parent insertion scenarios  
- `examples/nw/tests` - Northwind database examples (main test suite)
- `examples/payment_allocation/tests` - Payment allocation logic
- `examples/referential_integrity/tests` - Referential integrity examples
- `examples/tutorial/tests` - Tutorial examples

## Why Separate Test Runs?

Each example project:
1. Has its own database models
2. Activates LogicBank with specific rules for those models
3. Creates conflicts when multiple activations happen simultaneously

Running tests separately avoids these conflicts and ensures reliable test execution.

## Test Environment

- Python virtual environment: `venv/`
- Main dependencies: SQLAlchemy 1.4.29, LogicBankUtils
- Database: SQLite (copied from gold database before each test)

## Original Problem

The original test configuration was trying to discover tests across all example directories simultaneously (`./examples` instead of `./examples/nw/tests`), causing LogicBank activation conflicts and missing attribute errors.

## Solution

1. **Fixed VS Code settings**: Updated `.vscode/settings.json` to target `examples/nw/tests` 
2. **Created test runner script**: `run_tests.py` for running other example tests individually
3. **Documented the approach**: This README explains why and how to run tests properly

## Running Individual Test Files

You can also run individual test files directly:

```bash
# Run a specific test file
python examples/nw/tests/test_add_order.py

# Run with unittest module
python -m unittest examples.nw.tests.test_add_order -v
```
