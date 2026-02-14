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

"""Finding classifier and crash reporting for OSS-Fuzz integration.

This module provides the FindingClassifier class for classifying fuzzing findings
by severity and generating crash reports with stack traces and input data.

The severity classification follows these rules:
- CRITICAL: Memory corruption, code execution (ASAN errors, segfaults)
- HIGH: Denial of service, information disclosure (timeout, OOM)
- MEDIUM: Unhandled exceptions in non-security-critical code
- LOW: Minor issues

Example usage:
    ```python
    from fuzzing.classifier import FindingClassifier, CrashInfo, Severity

    crash = CrashInfo(
        target_name='fuzz_sql_injection',
        crash_type='ASAN',
        stack_trace='AddressSanitizer: heap-buffer-overflow...',
        input_data=b'malicious input',
    )

    classifier = FindingClassifier()
    severity = classifier.classify(crash)
    report = classifier.generate_report(crash)
    ```
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class Severity(str, Enum):
    """Severity levels for fuzzing findings.

    Classification follows security impact:
    - CRITICAL: Memory corruption, code execution
    - HIGH: DoS, information disclosure
    - MEDIUM: Unhandled exceptions
    - LOW: Minor issues
    """

    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class CrashInfo(BaseModel):
    """Information about a fuzzing crash.

    Captures all relevant data about a crash for classification and debugging.
    """

    target_name: str = Field(..., description='Name of the fuzz target')
    crash_type: str = Field(..., description='Type of crash (e.g., ASAN, timeout)')
    stack_trace: str = Field(..., description='Full stack trace')
    input_data: bytes = Field(..., description='Input that caused the crash')
    input_hash: str = Field(default='', description='SHA256 hash of input data')
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reproducer_path: Optional[Path] = Field(None, description='Path to reproducer file')

    model_config = {'arbitrary_types_allowed': True}

    @field_validator('input_hash', mode='before')
    @classmethod
    def compute_hash_if_empty(cls, v: str, info) -> str:
        """Compute SHA256 hash of input_data if not provided."""
        if v:
            return v
        # Access input_data from the values being validated
        input_data = info.data.get('input_data', b'')
        if isinstance(input_data, bytes):
            return hashlib.sha256(input_data).hexdigest()
        return ''

    def __init__(self, **data):
        """Initialize CrashInfo and compute hash if not provided."""
        super().__init__(**data)
        # Ensure hash is computed after initialization
        if not self.input_hash and self.input_data:
            object.__setattr__(self, 'input_hash', hashlib.sha256(self.input_data).hexdigest())


class Finding(BaseModel):
    """A classified security finding from fuzzing.

    Represents a complete finding with severity classification and metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description='Unique finding ID')
    severity: Severity = Field(..., description='Severity level')
    title: str = Field(..., description='Short description')
    description: str = Field(..., description='Detailed description')
    crash_info: CrashInfo = Field(..., description='Associated crash information')
    cwe_id: Optional[str] = Field(None, description='CWE identifier if applicable')
    remediation: Optional[str] = Field(None, description='Suggested fix')


# ASAN memory error patterns that indicate CRITICAL severity
ASAN_CRITICAL_PATTERNS = [
    r'AddressSanitizer:\s*(heap-buffer-overflow|stack-buffer-overflow)',
    r'AddressSanitizer:\s*(heap-use-after-free|stack-use-after-free)',
    r'AddressSanitizer:\s*(double-free|invalid-free)',
    r'AddressSanitizer:\s*(use-after-poison|container-overflow)',
    r'AddressSanitizer:\s*(global-buffer-overflow|stack-overflow)',
    r'AddressSanitizer:\s*(alloc-dealloc-mismatch)',
    r'AddressSanitizer:\s*(SEGV|BUS|FPE)',
    r'UndefinedBehaviorSanitizer:\s*(null-pointer|signed-integer-overflow)',
    r'MemorySanitizer:\s*(use-of-uninitialized-value)',
    r'LeakSanitizer:\s*(detected memory leaks)',
    r'Segmentation fault',
    r'SIGSEGV',
    r'SIGBUS',
    r'SIGFPE',
]

# Code execution indicators that indicate CRITICAL severity
CODE_EXECUTION_PATTERNS = [
    r'exec\s*\(',
    r'eval\s*\(',
    r'subprocess\.call',
    r'os\.system',
    r'__import__',
    r'pickle\.loads',
    r'yaml\.unsafe_load',
    r'shell\s*=\s*True',
    r'command injection',
    r'code execution',
    r'arbitrary code',
    r'remote code',
    r'RCE',
]

# HIGH severity patterns (DoS, information disclosure)
HIGH_SEVERITY_PATTERNS = [
    r'timeout',
    r'Timeout',
    r'TIMEOUT',
    r'out of memory',
    r'OutOfMemory',
    r'OOM',
    r'MemoryError',
    r'RecursionError',
    r'maximum recursion depth',
    r'information disclosure',
    r'sensitive data',
    r'credential',
    r'password',
    r'secret',
    r'token leak',
    r'path traversal',
    r'directory traversal',
    r'SSRF',
    r'XXE',
    r'SQL injection',
    r'injection detected',
]

# Compiled regex patterns for efficiency
_ASAN_CRITICAL_RE = [re.compile(p, re.IGNORECASE) for p in ASAN_CRITICAL_PATTERNS]
_CODE_EXECUTION_RE = [re.compile(p, re.IGNORECASE) for p in CODE_EXECUTION_PATTERNS]
_HIGH_SEVERITY_RE = [re.compile(p, re.IGNORECASE) for p in HIGH_SEVERITY_PATTERNS]


class FindingClassifier:
    """Classifies fuzzing findings by severity.

    Implements severity classification based on crash characteristics:
    - CRITICAL: Memory corruption (ASAN errors) or code execution indicators
    - HIGH: Denial of service (timeout, OOM) or information disclosure
    - MEDIUM: Unhandled Python exceptions in non-security code
    - LOW: Minor issues

    The classification is deterministic for the same crash information.
    """

    def classify(self, crash_info: CrashInfo) -> Severity:
        """Classify a crash by severity.

        Analyzes the crash type and stack trace to determine severity level.
        The classification is deterministic for the same crash information.

        Args:
            crash_info: Information about the crash to classify

        Returns:
            The severity level (CRITICAL, HIGH, MEDIUM, or LOW)
        """
        crash_type = crash_info.crash_type.lower()
        stack_trace = crash_info.stack_trace

        # Check for CRITICAL: ASAN memory errors
        if self._is_asan_memory_error(crash_type, stack_trace):
            return Severity.CRITICAL

        # Check for CRITICAL: Code execution indicators
        if self._is_code_execution(stack_trace):
            return Severity.CRITICAL

        # Check for HIGH: DoS or information disclosure
        if self._is_dos_or_disclosure(crash_type, stack_trace):
            return Severity.HIGH

        # Check for MEDIUM: Unhandled Python exceptions
        if self._is_unhandled_exception(crash_type, stack_trace):
            return Severity.MEDIUM

        # Default to LOW for minor issues
        return Severity.LOW

    def _is_asan_memory_error(self, crash_type: str, stack_trace: str) -> bool:
        """Check if crash involves ASAN memory errors."""
        # Check crash type
        if 'asan' in crash_type or 'sanitizer' in crash_type:
            return True

        # Check stack trace for ASAN patterns
        for pattern in _ASAN_CRITICAL_RE:
            if pattern.search(stack_trace):
                return True

        return False

    def _is_code_execution(self, stack_trace: str) -> bool:
        """Check if crash involves code execution indicators."""
        for pattern in _CODE_EXECUTION_RE:
            if pattern.search(stack_trace):
                return True
        return False

    def _is_dos_or_disclosure(self, crash_type: str, stack_trace: str) -> bool:
        """Check if crash involves DoS or information disclosure."""
        # Check crash type
        if crash_type in ('timeout', 'oom', 'out of memory'):
            return True

        # Check stack trace for HIGH severity patterns
        for pattern in _HIGH_SEVERITY_RE:
            if pattern.search(stack_trace):
                return True

        return False

    def _is_unhandled_exception(self, crash_type: str, stack_trace: str) -> bool:
        """Check if crash is an unhandled Python exception."""
        # Common Python exception indicators
        exception_indicators = [
            'Traceback (most recent call last)',
            'Exception:',
            'Error:',
            'raise ',
            'exception',
        ]

        for indicator in exception_indicators:
            if indicator.lower() in stack_trace.lower():
                return True

        # Check crash type for exception-related terms
        if 'exception' in crash_type or 'error' in crash_type:
            return True

        return False

    def generate_report(self, crash_info: CrashInfo) -> str:
        """Generate a human-readable crash report.

        Creates a detailed report containing all crash information
        for debugging and remediation.

        Args:
            crash_info: Information about the crash

        Returns:
            A formatted string containing the crash report
        """
        severity = self.classify(crash_info)

        # Format input data for display (truncate if too long)
        input_display = self._format_input_data(crash_info.input_data)

        report_lines = [
            '=' * 80,
            'FUZZING CRASH REPORT',
            '=' * 80,
            '',
            f'Target:     {crash_info.target_name}',
            f'Severity:   {severity.value.upper()}',
            f'Crash Type: {crash_info.crash_type}',
            f'Timestamp:  {crash_info.timestamp.isoformat()}',
            f'Input Hash: {crash_info.input_hash}',
            '',
            '-' * 80,
            'INPUT DATA',
            '-' * 80,
            input_display,
            '',
            '-' * 80,
            'STACK TRACE',
            '-' * 80,
            crash_info.stack_trace,
            '',
        ]

        if crash_info.reproducer_path:
            report_lines.extend(
                [
                    '-' * 80,
                    'REPRODUCER',
                    '-' * 80,
                    f'Path: {crash_info.reproducer_path}',
                    '',
                ]
            )

        report_lines.append('=' * 80)

        return '\n'.join(report_lines)

    def _format_input_data(self, data: bytes, max_length: int = 500) -> str:
        """Format input data for display in report.

        Args:
            data: The raw input bytes
            max_length: Maximum length to display

        Returns:
            Formatted string representation of the input
        """
        if len(data) <= max_length:
            # Try to decode as UTF-8, fall back to hex
            try:
                decoded = data.decode('utf-8')
                # Check if it's printable
                if all(c.isprintable() or c in '\n\r\t' for c in decoded):
                    return f'UTF-8 ({len(data)} bytes):\n{decoded}'
            except UnicodeDecodeError:
                pass

            # Fall back to hex representation
            hex_str = data.hex()
            return f'Hex ({len(data)} bytes):\n{hex_str}'
        else:
            # Truncate and show hex
            truncated = data[:max_length]
            hex_str = truncated.hex()
            return f'Hex ({len(data)} bytes, truncated to {max_length}):\n{hex_str}...'

    def create_finding(
        self,
        crash_info: CrashInfo,
        title: Optional[str] = None,
        description: Optional[str] = None,
        cwe_id: Optional[str] = None,
        remediation: Optional[str] = None,
    ) -> Finding:
        """Create a complete Finding from crash information.

        Args:
            crash_info: The crash information
            title: Optional custom title (auto-generated if not provided)
            description: Optional custom description (auto-generated if not provided)
            cwe_id: Optional CWE identifier
            remediation: Optional remediation guidance

        Returns:
            A complete Finding object
        """
        severity = self.classify(crash_info)

        if title is None:
            title = (
                f'{severity.value.upper()}: {crash_info.crash_type} in {crash_info.target_name}'
            )

        if description is None:
            description = self._generate_description(crash_info, severity)

        return Finding(
            severity=severity,
            title=title,
            description=description,
            crash_info=crash_info,
            cwe_id=cwe_id,
            remediation=remediation,
        )

    def _generate_description(self, crash_info: CrashInfo, severity: Severity) -> str:
        """Generate a description based on crash info and severity."""
        severity_descriptions = {
            Severity.CRITICAL: (
                'A critical security issue was detected that may involve '
                'memory corruption or potential code execution.'
            ),
            Severity.HIGH: (
                'A high severity issue was detected that may cause '
                'denial of service or information disclosure.'
            ),
            Severity.MEDIUM: (
                'An unhandled exception was detected that may indicate '
                'a bug in input validation or error handling.'
            ),
            Severity.LOW: (
                'A minor issue was detected that should be reviewed '
                'but is unlikely to have significant security impact.'
            ),
        }

        base_desc = severity_descriptions.get(severity, 'An issue was detected.')

        return (
            f'{base_desc}\n\n'
            f'Crash Type: {crash_info.crash_type}\n'
            f'Target: {crash_info.target_name}\n'
            f'Input Hash: {crash_info.input_hash}'
        )
