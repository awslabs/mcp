#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
AWS Network MCP Server Implementation Validation Script.

This script provides comprehensive validation that the resolution plan
has been successfully implemented. It checks:

1. Test Results: 167/167 tests passing
2. Code Coverage: 80%+ coverage achieved
3. Code Quality: Zero ruff violations
4. Security: All security tests passing
5. AWS Labs Compliance: All OSPO requirements met
6. FastMCP Compatibility: No private API dependencies

Usage:
    python scripts/validate_implementation.py
"""

import sys
import os
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class ValidationResult:
    """Container for validation check results."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.details = {}
        self.errors = []
        
    def __str__(self):
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if self.passed else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        return f"{self.name}: {status}\n  {self.message}"

class ImplementationValidator:
    """Comprehensive validator for resolution plan implementation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = []
        self.exit_code = 0
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """
        Run shell command and return return code, stdout, stderr.
        
        Args:
            cmd: Command as list of arguments
            cwd: Working directory
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    @staticmethod
    def print_header(text: str):
        """Print formatted header."""
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BLUE}{Colors.BOLD}{text:^70}{Colors.RESET}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    @staticmethod
    def print_section(text: str):
        """Print formatted section header."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
        print(f"{Colors.CYAN}{'-'*70}{Colors.RESET}")
    
    def validate_test_suite(self) -> ValidationResult:
        """
        Validate all tests are passing (167/167).
        
        This runs the complete pytest suite and verifies:
        - All integration tests pass
        - All security tests pass
        - No FastMCP compatibility issues
        """
        result = ValidationResult("Test Suite (167/167)")
        
        self.print_section("Running Full Test Suite...")
        
        # Run pytest with comprehensive reporting
        returncode, stdout, stderr = self.run_command([
            sys.executable, "-m", "pytest", "tests/",
            "--maxfail=0",
            "--tb=short",
            "-v",
            "-q"  # Quiet mode for CI
        ])
        
        # Parse results
        if returncode == 0:
            result.passed = True
            result.message = "All tests passing"
            
            # Extract test count
            passed_match = re.search(r'(\d+) passed', stdout)
            if passed_match:
                passed_count = int(passed_match.group(1))
                result.details['passed'] = passed_count
                
            # Check for expected count
            if passed_count < 167:
                result.passed = False
                result.errors.append(f"Expected 167 tests, found {passed_count}")
        else:
            result.passed = False
            result.message = "Tests failed"
            result.errors.append(f"Pytest exit code: {returncode}")
            
            # Extract failure details
            failures = re.findall(r'FAILED .+', stderr)
            if failures:
                result.errors.extend(failures[:5])  # Show first 5 failures
        
        # Check for specific test categories
        if "integration" in stdout.lower():
            result.details['integration_tests'] = "Found"
        if "security" in stdout.lower():
            result.details['security_tests'] = "Found"
            
        return result
    
    def validate_coverage(self) -> ValidationResult:
        """
        Validate code coverage is 80% or higher.
        
        Runs coverage analysis and verifies the coverage threshold.
        """
        result = ValidationResult("Code Coverage (80%+)")
        
        self.print_section("Checking Code Coverage...")
        
        # Run pytest with coverage
        returncode, stdout, stderr = self.run_command([
            sys.executable, "-m", "pytest", "tests/",
            "--cov=awslabs",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=80"
        ])
        
        # Parse coverage percentage
        coverage_match = re.search(r'(\d+)%', stdout)
        if coverage_match:
            coverage_percent = int(coverage_match.group(1))
            result.details['coverage_percent'] = coverage_percent
            
            if coverage_percent >= 80:
                result.passed = True
                result.message = f"Coverage {coverage_percent}% meets 80% threshold"
            else:
                result.passed = False
                result.message = f"Coverage {coverage_percent}% below 80% threshold"
                
                # Extract missing files
                missing = re.findall(r'(.+\.py).+\s+(\d+%)', stdout)
                if missing:
                    result.details['low_coverage_files'] = missing[:10]
        else:
            result.passed = False
            result.message = "Could not parse coverage percentage"
            result.errors.append("Coverage report format unexpected")
            
        return result
    
    def validate_code_quality(self) -> ValidationResult:
        """
        Validate zero ruff violations.
        
        Runs ruff linting and formatting checks.
        """
        result = ValidationResult("Code Quality (Zero Ruff Violations)")
        
        self.print_section("Running Code Quality Checks...")
        
        # Check ruff linting
        returncode, stdout, stderr = self.run_command([
            sys.executable, "-m", "ruff", "check", "."
        ])
        
        if returncode == 0:
            result.passed = True
            result.message = "No ruff violations found"
            result.details['violations'] = 0
        else:
            # Parse violation count
            violation_match = re.search(r'Found (\d+) errors?', stdout)
            if violation_match:
                violation_count = int(violation_match.group(1))
                result.details['violations'] = violation_count
                
                if violation_count == 0:
                    result.passed = True
                    result.message = "No violations"
                else:
                    result.passed = False
                    result.message = f"{violation_count} ruff violations found"
                    
                    # Extract specific violations
                    violation_lines = stdout.split('\n')
                    result.errors = [line for line in violation_lines if line.strip() and not line.startswith