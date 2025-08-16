#!/usr/bin/env python3
"""
Test runner script for LogicBank examples.
Each example project has its own LogicBank activation that conflicts with others,
so tests must be run separately by example directory.
"""

import os
import sys
import subprocess
import argparse

def find_test_directories():
    """Find all test directories in examples."""
    test_dirs = []
    examples_dir = "examples"
    for root, dirs, files in os.walk(examples_dir):
        if "tests" in dirs:
            test_path = os.path.join(root, "tests")
            test_dirs.append(test_path)
    return sorted(test_dirs)

def run_tests_for_directory(test_dir, python_executable):
    """Run tests for a specific directory."""
    print(f"\n{'='*60}")
    print(f"Running tests in: {test_dir}")
    print(f"{'='*60}")
    
    cmd = [
        python_executable, "-m", "unittest", "discover",
        "-s", test_dir,
        "-p", "test_*.py",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=".", capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests in {test_dir}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run LogicBank example tests")
    parser.add_argument("--dir", help="Specific test directory to run (e.g., examples/nw/tests)")
    parser.add_argument("--list", action="store_true", help="List available test directories")
    parser.add_argument("--python", default="python", help="Python executable to use")
    
    args = parser.parse_args()
    
    # Get Python executable from virtual environment if available
    venv_python = os.path.join("venv", "bin", "python")
    if os.path.exists(venv_python):
        python_executable = venv_python
    else:
        python_executable = args.python
    
    test_dirs = find_test_directories()
    
    if args.list:
        print("Available test directories:")
        for test_dir in test_dirs:
            print(f"  {test_dir}")
        return
    
    if args.dir:
        if args.dir in test_dirs:
            success = run_tests_for_directory(args.dir, python_executable)
            sys.exit(0 if success else 1)
        else:
            print(f"Test directory '{args.dir}' not found.")
            print("Available directories:")
            for test_dir in test_dirs:
                print(f"  {test_dir}")
            sys.exit(1)
    
    # Run all test directories
    results = {}
    for test_dir in test_dirs:
        results[test_dir] = run_tests_for_directory(test_dir, python_executable)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for test_dir, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{test_dir:<40} {status}")
        if not passed:
            all_passed = False
    
    print(f"\nOverall result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
