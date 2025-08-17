# LogicBank Testing Guide

## Usage Overview

The LogicBank testing strategy follows a **comprehensive-first, debug-specific** approach:

1. **Start with `run_tests_all`** - Run the complete test suite to get an overall health check
2. **On failure, debug specific tests** - Use individual run configurations for detailed debugging

This approach ensures you quickly identify issues across the entire framework, then focus debugging efforts on specific failing components.

### Quick Start
- **VS Code:** Press `F5` → Select `run_tests_all` 
- **Command Line:** `python3 run_tests.py`
- **Results:** Check `test_summary.txt` for detailed results

## Running Tests

### Option 1: VS Code Launch Configurations (Recommended)

**Comprehensive Testing:**
- Press `F5` → Select `run_tests_all` to run all test suites
- Creates `test_summary.txt` with detailed results including individual test file listings

**Debug Specific Failures:**
- Use `run_tests_<example>` configurations for specific test suites:
  - `run_tests_nw` - Northwind example (16 business logic tests)
  - `run_tests_copy_children` - Copy children functionality
  - `run_tests_banking` - Banking transfer tests
  - `run_tests_payment_allocation` - Payment allocation logic
  - `run_tests_referential_integrity` - Referential integrity cascade tests
- Use individual test configurations for single file debugging:
  - `copy_children_test`, `banking_test`, `payment_allocation_test`, etc.

**List Available Tests:**
- Use `run_tests_list` to see all available test directories

### Option 2: Command Line

```bash
# Run all tests (creates test_summary.txt)
python3 run_tests.py

# Run specific test directory
python3 run_tests.py --dir examples/nw/tests
python3 run_tests.py --dir examples/copy_children/tests

# List available test directories  
python3 run_tests.py --list
```

### Option 3: Individual Test Files

```bash
# Run individual test files directly
python3 examples/copy_children/tests/test_clone_project.py
python3 examples/banking/tests/test_transfer_funds.py
```

## Test Results

### Test Summary Report
- **File:** `test_summary.txt` (overwrites each run)
- **Contains:** 
  - Overall results (pass/fail rates)
  - Detailed test file listings for each example
  - Individual NW test descriptions
  - Key accomplishments and notes

### Example Test Summary Output
```
OVERALL RESULTS:
Total Test Suites: 8
Total Test Files: 23  
Passed Suites: 8
Failed Suites: 0
Success Rate: 100.0%

DETAILED TEST RESULTS:
examples/nw/tests                        PASSED
  Unittest files:
    - test_add_order.py
    - test_upd_order_shipped.py
    [... 14 more NW tests]

examples/copy_children/tests             PASSED
  Standalone scripts:
    - test_clone_project.py
```

## Available Test Directories

- `examples/banking/tests` - Banking transfer scenarios  
- `examples/copy_children/tests` - Copy children relationships
- `examples/custom_exceptions/tests` - Custom exception handling
- `examples/insert_parent/tests` - Parent insertion scenarios  
- `examples/nw/tests` - Northwind database examples (16 business logic tests)
- `examples/payment_allocation/tests` - Payment allocation logic
- `examples/referential_integrity/tests` - Referential integrity examples
- `examples/tutorial/tests` - Tutorial examples

## Test Architecture

### Test Organization
- **8 Example Directories:** Each with focused test scenarios
- **23 Individual Test Files:** Mix of unittest and standalone scripts
- **Test Types:**
  - **Unittest files** (NW): Uses Python unittest framework
  - **Standalone scripts**: Direct execution with custom test logic

### Key Test Suites
1. **NW (Northwind):** 16 comprehensive business logic tests
2. **Copy Children:** Project cloning with child entity replication
3. **Banking:** Financial transfer validation
4. **Payment Allocation:** Payment distribution logic
5. **Referential Integrity:** Parent-child cascade operations
6. **Custom Exceptions:** Constraint violation handling
7. **Insert Parent:** Parent entity creation workflows
8. **Tutorial:** Basic LogicBank functionality

## Debugging Workflow

### When Tests Pass ✅
- Review `test_summary.txt` for confirmation
- All 8 test suites should show `PASSED`
- Success rate should be 100.0%

### When Tests Fail ❌
1. **Check `test_summary.txt`** for overview of which suites failed
2. **Run specific failing suite** using `run_tests_<example>` configuration
3. **Debug individual test** using `<example>_test` configuration with breakpoints
4. **Set breakpoints** in LogicBank code or test logic as needed
5. **Use `justMyCode: false`** configurations for framework-level debugging

### Common Debugging Scenarios
- **SQLAlchemy compatibility issues:** Check version-specific logic paths
- **Session management:** Verify proper session handling in LogicBank framework
- **Rule execution:** Trace business logic rule firing sequences
- **Data persistence:** Validate database state changes

## Why Separate Test Runs?

Each example project:
1. Has its own database models
2. Activates LogicBank with specific rules for those models
3. Creates conflicts when multiple activations happen simultaneously

The `run_tests.py` script handles this by running each test directory separately, avoiding conflicts and ensuring reliable test execution.

## Framework Compatibility

### SQLAlchemy 2.0 Validation
All tests validate LogicBank compatibility with SQLAlchemy 2.0, including:
- Session management patterns
- Relationship handling (`back_populates` vs `backref`)
- Query syntax and execution
- Transaction management

## Test Environment

- **Python:** 3.13.5
- **SQLAlchemy:** 2.0.39
- **LogicBank:** 1.20.26
- **Virtual Environment:** `venv/bin/python`
- **Database:** SQLite (copied from gold database before each test)

## Legacy Notes

### Original Problem
The original test configuration was trying to discover tests across all example directories simultaneously, causing LogicBank activation conflicts and missing attribute errors.

### Solution Evolution
1. **Fixed VS Code settings**: Updated to target specific test directories
2. **Created comprehensive test runner**: `run_tests.py` for organized test execution
3. **Enhanced debugging workflow**: VS Code launch configurations for efficient debugging
4. **Automated reporting**: `test_summary.txt` with detailed results

This testing approach ensures comprehensive validation while enabling efficient debugging of specific issues.
