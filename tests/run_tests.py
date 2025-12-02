#!/usr/bin/env python3
"""
Test Runner Script for Mini-RAG / Second Brain

This script provides a convenient way to run different categories of tests
with appropriate configurations.

Usage:
    python tests/run_tests.py              # Run all tests
    python tests/run_tests.py --quick      # Run quick tests only (skip slow)
    python tests/run_tests.py --stress     # Run stress tests only
    python tests/run_tests.py --qa         # Run QA tests only
    python tests/run_tests.py --coverage   # Run with coverage report
    python tests/run_tests.py --verbose    # Verbose output
    python tests/run_tests.py --fail-fast  # Stop on first failure
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure we're in the right directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

# Add project to path
sys.path.insert(0, str(PROJECT_ROOT))


def run_tests(args):
    """Run tests with specified configuration."""

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Test directory
    test_dir = "tests/"

    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-v")  # Default to verbose

    # Add short traceback
    cmd.extend(["--tb", "short"])

    # Stop on first failure
    if args.fail_fast:
        cmd.append("-x")

    # Coverage
    if args.coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])

    # Test selection
    if args.quick:
        # Skip slow tests
        cmd.extend(["-m", "not slow"])
        print("\n🏃 Running QUICK tests (skipping slow/stress tests)...\n")
    elif args.stress:
        # Only stress tests
        cmd.extend(["-m", "slow"])
        print("\n💪 Running STRESS tests only...\n")
    elif args.qa:
        # Only QA/contract tests
        cmd.extend(["-k", "TestAPIContract or TestInputValidation or TestErrorHandling or TestSecurityHeaders"])
        print("\n🔍 Running QA tests only...\n")
    elif args.integration:
        # Only integration tests
        cmd.extend(["-k", "TestEndToEnd or TestIntegration"])
        print("\n🔗 Running INTEGRATION tests only...\n")
    elif args.unit:
        # Only unit tests (exclude slow and integration)
        cmd.extend(["-m", "not slow", "-k", "not EndToEnd and not Integration"])
        print("\n🧪 Running UNIT tests only...\n")
    else:
        print("\n🧪 Running ALL tests...\n")

    # Add test directory
    cmd.append(test_dir)

    # Add any extra args
    if args.extra:
        cmd.extend(args.extra)

    # Print command
    print(f"Command: {' '.join(cmd)}\n")
    print("=" * 60)

    # Run tests
    result = subprocess.run(cmd)

    return result.returncode


def setup_environment():
    """Set up environment for testing."""
    os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
    os.environ.setdefault("LOCAL_MODE", "true")

    # Check for required files
    required_files = [
        "server.py",
        "rag_pipeline.py",
        "retrieval.py",
        "raglite.py",
    ]

    missing = [f for f in required_files if not (PROJECT_ROOT / f).exists()]
    if missing:
        print(f"⚠️  Warning: Missing files: {missing}")


def check_dependencies():
    """Check if test dependencies are installed."""
    try:
        import pytest
        print(f"✓ pytest {pytest.__version__}")
    except ImportError:
        print("✗ pytest not installed. Run: pip install pytest")
        return False

    try:
        import pytest_asyncio
        print(f"✓ pytest-asyncio installed")
    except ImportError:
        print("⚠️  pytest-asyncio not installed. Some async tests may fail.")

    try:
        import httpx
        print(f"✓ httpx {httpx.__version__}")
    except ImportError:
        print("⚠️  httpx not installed. Some tests may fail.")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run Mini-RAG test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/run_tests.py                    # Run all tests
    python tests/run_tests.py --quick            # Skip slow tests
    python tests/run_tests.py --stress           # Only stress tests
    python tests/run_tests.py --qa               # Only QA tests
    python tests/run_tests.py --coverage         # With coverage report
    python tests/run_tests.py -k "test_health"   # Run specific test
        """
    )

    parser.add_argument("--quick", "-q", action="store_true",
                        help="Run quick tests only (skip slow/stress tests)")
    parser.add_argument("--stress", "-s", action="store_true",
                        help="Run stress tests only")
    parser.add_argument("--qa", action="store_true",
                        help="Run QA/contract tests only")
    parser.add_argument("--integration", "-i", action="store_true",
                        help="Run integration tests only")
    parser.add_argument("--unit", "-u", action="store_true",
                        help="Run unit tests only")
    parser.add_argument("--coverage", "-c", action="store_true",
                        help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--fail-fast", "-x", action="store_true",
                        help="Stop on first failure")
    parser.add_argument("--check-deps", action="store_true",
                        help="Check dependencies and exit")
    parser.add_argument("extra", nargs="*",
                        help="Extra arguments to pass to pytest")

    args = parser.parse_args()

    print("=" * 60)
    print("Mini-RAG Test Suite Runner")
    print("=" * 60)

    # Check dependencies
    if args.check_deps:
        check_dependencies()
        return 0

    if not check_dependencies():
        return 1

    # Setup environment
    setup_environment()

    # Run tests
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
