#!/usr/bin/env python3
"""Test runner script for EarnORM.

This script provides convenient commands for running different types of tests
with appropriate configurations and reporting.
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def run_unit_tests(
    coverage: bool = False,
    parallel: bool = False,
    verbose: bool = False,
    pattern: Optional[str] = None
) -> int:
    """Run unit tests."""
    cmd = ["poetry", "run", "pytest", "tests/unit/"]
    
    if coverage:
        cmd.extend(["--cov=earnorm", "--cov-report=term-missing", "--cov-report=html"])
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    if verbose:
        cmd.append("-v")
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    cmd.extend(["-m", "unit"])
    
    return run_command(cmd)


def run_integration_tests(
    coverage: bool = False,
    parallel: bool = False,
    verbose: bool = False,
    pattern: Optional[str] = None
) -> int:
    """Run integration tests."""
    cmd = ["poetry", "run", "pytest", "tests/integration/"]
    
    if coverage:
        cmd.extend(["--cov=earnorm", "--cov-report=term-missing", "--cov-report=html"])
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    if verbose:
        cmd.append("-v")
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    cmd.extend(["-m", "integration"])
    
    return run_command(cmd)


def run_e2e_tests(
    coverage: bool = False,
    verbose: bool = False,
    pattern: Optional[str] = None
) -> int:
    """Run end-to-end tests."""
    cmd = ["poetry", "run", "pytest", "tests/e2e/"]
    
    if coverage:
        cmd.extend(["--cov=earnorm", "--cov-report=term-missing", "--cov-report=html"])
    
    # E2E tests should not run in parallel
    if verbose:
        cmd.append("-v")
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    cmd.extend(["-m", "e2e"])
    
    return run_command(cmd)


def run_all_tests(
    coverage: bool = False,
    parallel: bool = False,
    verbose: bool = False,
    pattern: Optional[str] = None
) -> int:
    """Run all tests."""
    cmd = ["poetry", "run", "pytest"]
    
    if coverage:
        cmd.extend(["--cov=earnorm", "--cov-report=term-missing", "--cov-report=html"])
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    if verbose:
        cmd.append("-v")
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    return run_command(cmd)


def run_benchmark_tests(verbose: bool = False) -> int:
    """Run benchmark tests."""
    cmd = ["poetry", "run", "pytest", "--benchmark-only"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_type_checking() -> int:
    """Run type checking with mypy."""
    cmd = ["poetry", "run", "mypy", "earnorm"]
    return run_command(cmd)


def run_linting() -> int:
    """Run linting with ruff."""
    cmd = ["poetry", "run", "ruff", "check", "earnorm"]
    return run_command(cmd)


def run_formatting_check() -> int:
    """Check code formatting with black."""
    cmd = ["poetry", "run", "black", "--check", "earnorm"]
    return run_command(cmd)


def run_quality_checks() -> int:
    """Run all quality checks (type checking, linting, formatting)."""
    print("Running quality checks...")
    
    print("\n1. Type checking...")
    type_result = run_type_checking()
    
    print("\n2. Linting...")
    lint_result = run_linting()
    
    print("\n3. Formatting check...")
    format_result = run_formatting_check()
    
    if type_result != 0:
        print("❌ Type checking failed")
    else:
        print("✅ Type checking passed")
    
    if lint_result != 0:
        print("❌ Linting failed")
    else:
        print("✅ Linting passed")
    
    if format_result != 0:
        print("❌ Formatting check failed")
    else:
        print("✅ Formatting check passed")
    
    return max(type_result, lint_result, format_result)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="EarnORM Test Runner")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "e2e", "all", "benchmark", "quality"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--pattern", "-k",
        help="Run tests matching pattern"
    )
    
    args = parser.parse_args()
    
    # Set working directory to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Run appropriate tests
    if args.test_type == "unit":
        exit_code = run_unit_tests(
            coverage=args.coverage,
            parallel=args.parallel,
            verbose=args.verbose,
            pattern=args.pattern
        )
    elif args.test_type == "integration":
        exit_code = run_integration_tests(
            coverage=args.coverage,
            parallel=args.parallel,
            verbose=args.verbose,
            pattern=args.pattern
        )
    elif args.test_type == "e2e":
        exit_code = run_e2e_tests(
            coverage=args.coverage,
            verbose=args.verbose,
            pattern=args.pattern
        )
    elif args.test_type == "all":
        exit_code = run_all_tests(
            coverage=args.coverage,
            parallel=args.parallel,
            verbose=args.verbose,
            pattern=args.pattern
        )
    elif args.test_type == "benchmark":
        exit_code = run_benchmark_tests(verbose=args.verbose)
    elif args.test_type == "quality":
        exit_code = run_quality_checks()
    else:
        print(f"Unknown test type: {args.test_type}")
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
