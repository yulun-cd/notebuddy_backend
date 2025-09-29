#!/usr/bin/env python3
"""
Test runner script for NoteBuddy backend tests
"""
import subprocess
import sys
import os


def run_tests():
    """Run all tests using pytest"""
    print("🚀 Running NoteBuddy Backend Tests")
    print("=" * 50)

    # Set test environment
    os.environ["ENVIRONMENT"] = "test"

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_html",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode


def run_unit_tests_only():
    """Run only unit tests"""
    print("🧪 Running Unit Tests Only")
    print("=" * 50)

    os.environ["ENVIRONMENT"] = "test"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_crud.py",
        "tests/test_auth.py",
        "tests/test_ai_services.py",
        "-v",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Unit tests completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Unit tests failed with exit code {e.returncode}")
        return e.returncode


def run_integration_tests_only():
    """Run only integration tests"""
    print("🔗 Running Integration Tests Only")
    print("=" * 50)

    os.environ["ENVIRONMENT"] = "test"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_api_endpoints.py",
        "-v",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Integration tests completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Integration tests failed with exit code {e.returncode}")
        return e.returncode


def show_test_coverage():
    """Show test coverage report"""
    print("📊 Generating Test Coverage Report")
    print("=" * 50)

    os.environ["ENVIRONMENT"] = "test"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_html",
        "--quiet",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n📈 Coverage report generated in 'coverage_html' directory")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Coverage generation failed with exit code {e.returncode}")
        return e.returncode


def main():
    """Main function to run tests based on command line arguments"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "unit":
            return run_unit_tests_only()
        elif command == "integration":
            return run_integration_tests_only()
        elif command == "coverage":
            return show_test_coverage()
        elif command == "help":
            print_help()
            return 0
        else:
            print(f"Unknown command: {command}")
            print_help()
            return 1
    else:
        # Run all tests by default
        return run_tests()


def print_help():
    """Print help information"""
    print(
        """
NoteBuddy Backend Test Runner

Usage:
  python run_tests.py [command]

Commands:
  unit         - Run only unit tests
  integration  - Run only integration tests
  coverage     - Generate coverage report
  help         - Show this help message

If no command is provided, runs all tests with coverage.
"""
    )


if __name__ == "__main__":
    sys.exit(main())
