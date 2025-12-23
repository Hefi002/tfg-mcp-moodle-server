#!/usr/bin/env python3
"""Test runner script with common testing scenarios.

Usage:
    python run_tests.py [option]

Options:
    all         - Run all tests (default)
    unit        - Run only unit tests
    integration - Run only integration tests
    coverage    - Run all tests with coverage report
    watch       - Run tests in watch mode (requires pytest-watch)
"""

import sys
import subprocess


def run_command(cmd):
    """Run a shell command and return exit code."""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 80)
    result = subprocess.run(cmd)
    return result.returncode


def main():
    option = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    commands = {
        "all": ["pytest"],
        "unit": ["pytest", "tests/test_moodle.py"],
        "integration": ["pytest", "tests/test_mcp.py"],
        "coverage": [
            "pytest",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing"
        ],
        "watch": ["pytest-watch", "--", "-v"],
        "verbose": ["pytest", "-vv", "-s"],
        "failed": ["pytest", "--lf"],  # last failed
        "exitfirst": ["pytest", "-x"],  # exit on first failure
    }
    
    if option not in commands:
        print(f"Unknown option: {option}")
        print(__doc__)
        return 1
    
    return run_command(commands[option])


if __name__ == "__main__":
    sys.exit(main())
