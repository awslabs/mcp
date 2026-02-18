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

"""Property-based tests for FindingClassifier crash severity classification.

This module contains property-based tests validating the correctness properties
of the crash severity classification system.

Feature: oss-fuzz-integration, Property 7: Crash Severity Classification
Validates: Requirements 16.1, 16.2, 16.3
"""

from __future__ import annotations

from fuzzing.classifier import (
    ASAN_CRITICAL_PATTERNS,
    CODE_EXECUTION_PATTERNS,
    HIGH_SEVERITY_PATTERNS,
    CrashInfo,
    FindingClassifier,
    Severity,
)
from hypothesis import assume, given, settings
from hypothesis import strategies as st


# =============================================================================
# Hypothesis Strategies for Crash Information
# =============================================================================


def crash_info_strategy(
    crash_type: st.SearchStrategy[str] | None = None,
    stack_trace: st.SearchStrategy[str] | None = None,
) -> st.SearchStrategy[CrashInfo]:
    """Strategy for generating CrashInfo objects.

    Args:
        crash_type: Optional strategy for crash_type field
        stack_trace: Optional strategy for stack_trace field

    Returns:
        A strategy that generates CrashInfo objects
    """
    if crash_type is None:
        crash_type = st.text(min_size=1, max_size=50)
    if stack_trace is None:
        stack_trace = st.text(min_size=0, max_size=500)

    return st.builds(
        CrashInfo,
        target_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        crash_type=crash_type,
        stack_trace=stack_trace,
        input_data=st.binary(min_size=1, max_size=100),
    )


def asan_memory_error_stack_trace() -> st.SearchStrategy[str]:
    """Strategy for generating stack traces with ASAN memory error patterns."""
    asan_patterns = [
        'AddressSanitizer: heap-buffer-overflow on address',
        'AddressSanitizer: stack-buffer-overflow on address',
        'AddressSanitizer: heap-use-after-free on address',
        'AddressSanitizer: stack-use-after-free on address',
        'AddressSanitizer: double-free on address',
        'AddressSanitizer: invalid-free on address',
        'AddressSanitizer: use-after-poison on address',
        'AddressSanitizer: container-overflow on address',
        'AddressSanitizer: global-buffer-overflow on address',
        'AddressSanitizer: stack-overflow on address',
        'AddressSanitizer: alloc-dealloc-mismatch on address',
        'AddressSanitizer: SEGV on unknown address',
        'AddressSanitizer: BUS on unknown address',
        'UndefinedBehaviorSanitizer: null-pointer dereference',
        'UndefinedBehaviorSanitizer: signed-integer-overflow',
        'MemorySanitizer: use-of-uninitialized-value',
        'LeakSanitizer: detected memory leaks',
        'Segmentation fault (core dumped)',
        'SIGSEGV received',
        'SIGBUS received',
        'SIGFPE received',
    ]
    return st.sampled_from(asan_patterns).flatmap(
        lambda pattern: st.builds(
            lambda prefix, suffix: f'{prefix}\n{pattern}\n{suffix}',
            prefix=st.text(min_size=0, max_size=100),
            suffix=st.text(min_size=0, max_size=100),
        )
    )


def code_execution_stack_trace() -> st.SearchStrategy[str]:
    """Strategy for generating stack traces with code execution indicators."""
    code_exec_patterns = [
        'exec(user_input)',
        'eval(malicious_code)',
        'subprocess.call(cmd, shell=True)',
        'os.system(command)',
        '__import__(module_name)',
        'pickle.loads(untrusted_data)',
        'yaml.unsafe_load(data)',
        'shell=True in subprocess',
        'command injection detected',
        'code execution vulnerability',
        'arbitrary code execution',
        'remote code execution detected',
        'RCE vulnerability found',
    ]
    return st.sampled_from(code_exec_patterns).flatmap(
        lambda pattern: st.builds(
            lambda prefix, suffix: f'{prefix}\n{pattern}\n{suffix}',
            prefix=st.text(min_size=0, max_size=100),
            suffix=st.text(min_size=0, max_size=100),
        )
    )


def high_severity_stack_trace() -> st.SearchStrategy[str]:
    """Strategy for generating stack traces with HIGH severity patterns."""
    high_patterns = [
        'timeout after 30 seconds',
        'Timeout exceeded',
        'TIMEOUT: operation took too long',
        'out of memory error',
        'OutOfMemoryError: Java heap space',
        'OOM killer invoked',
        'MemoryError: unable to allocate',
        'RecursionError: maximum recursion depth exceeded',
        'maximum recursion depth exceeded in comparison',
        'information disclosure detected',
        'sensitive data exposed',
        'credential leak detected',
        'password exposed in logs',
        'secret key leaked',
        'token leak in response',
        'path traversal vulnerability',
        'directory traversal detected',
        'SSRF vulnerability found',
        'XXE injection detected',
        'SQL injection detected',
        'injection detected in query',
    ]
    return st.sampled_from(high_patterns).flatmap(
        lambda pattern: st.builds(
            lambda prefix, suffix: f'{prefix}\n{pattern}\n{suffix}',
            prefix=st.text(min_size=0, max_size=100),
            suffix=st.text(min_size=0, max_size=100),
        )
    )


def medium_severity_stack_trace() -> st.SearchStrategy[str]:
    """Strategy for generating stack traces with unhandled Python exceptions."""
    exception_patterns = [
        'Traceback (most recent call last):\n  File "test.py", line 10\nValueError: invalid value',
        'Traceback (most recent call last):\n  File "app.py", line 25\nKeyError: missing_key',
        'Traceback (most recent call last):\n  File "main.py", line 5\nTypeError: expected str',
        'Exception: Something went wrong',
        'RuntimeError: unexpected state',
        'AttributeError: object has no attribute',
        'IndexError: list index out of range',
        'raise ValueError("invalid input")',
        'raise TypeError("wrong type")',
    ]
    return st.sampled_from(exception_patterns).flatmap(
        lambda pattern: st.builds(
            lambda prefix, suffix: f'{prefix}\n{pattern}\n{suffix}',
            prefix=st.text(min_size=0, max_size=50),
            suffix=st.text(min_size=0, max_size=50),
        )
    )


def low_severity_stack_trace() -> st.SearchStrategy[str]:
    """Strategy for generating stack traces with no security indicators.

    These are benign stack traces that don't match any severity patterns.
    """
    # Generate text that explicitly avoids all known patterns
    return st.text(
        alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789_ \n'),
        min_size=10,
        max_size=200,
    ).filter(lambda s: not _contains_any_severity_pattern(s))


def _contains_any_severity_pattern(text: str) -> bool:
    """Check if text contains any known severity pattern."""
    import re

    text_lower = text.lower()

    # Check ASAN patterns
    for pattern in ASAN_CRITICAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Check code execution patterns
    for pattern in CODE_EXECUTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Check HIGH severity patterns
    for pattern in HIGH_SEVERITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Check exception indicators
    exception_indicators = [
        'traceback',
        'exception',
        'error:',
        'raise ',
    ]
    for indicator in exception_indicators:
        if indicator in text_lower:
            return True

    return False


# =============================================================================
# Property Tests for Crash Severity Classification
# =============================================================================


class TestCrashSeverityClassification:
    """Property tests for crash severity classification.

    Feature: oss-fuzz-integration, Property 7: Crash Severity Classification
    Validates: Requirements 16.1, 16.2, 16.3

    Property 7: Crash Severity Classification
    *For any* crash detected during fuzzing, the `FindingClassifier.classify()`
    function SHALL assign exactly one severity level based on crash characteristics:
    - CRITICAL: if stack trace contains ASAN memory error patterns or code execution indicators
    - HIGH: if crash involves timeout, OOM, or information disclosure patterns
    - MEDIUM: if crash is an unhandled Python exception in non-security code
    - LOW: otherwise

    The classification SHALL be deterministic for the same crash information.
    """

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.classifier = FindingClassifier()

    # -------------------------------------------------------------------------
    # Property: Classification always returns exactly one severity level
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_classify_returns_exactly_one_severity(self, crash_info: CrashInfo) -> None:
        """For any crash, classify() returns exactly one Severity enum value.

        **Validates: Requirements 16.1, 16.2, 16.3**
        """
        result = self.classifier.classify(crash_info)

        # Must be a Severity enum value
        assert isinstance(result, Severity)

        # Must be one of the valid severity levels
        assert result in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]

    # -------------------------------------------------------------------------
    # Property: CRITICAL classification for ASAN memory errors
    # -------------------------------------------------------------------------

    @given(crash_info_strategy(stack_trace=asan_memory_error_stack_trace()))
    @settings(max_examples=100, deadline=None)
    def test_asan_memory_errors_classified_as_critical(self, crash_info: CrashInfo) -> None:
        """Crashes with ASAN memory error patterns SHALL be classified as CRITICAL.

        **Validates: Requirements 16.1**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.CRITICAL

    @given(
        crash_info_strategy(
            crash_type=st.sampled_from(['ASAN', 'asan', 'AddressSanitizer', 'sanitizer']),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_asan_crash_type_classified_as_critical(self, crash_info: CrashInfo) -> None:
        """Crashes with ASAN-related crash_type SHALL be classified as CRITICAL.

        **Validates: Requirements 16.1**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.CRITICAL

    # -------------------------------------------------------------------------
    # Property: CRITICAL classification for code execution indicators
    # -------------------------------------------------------------------------

    @given(crash_info_strategy(stack_trace=code_execution_stack_trace()))
    @settings(max_examples=100, deadline=None)
    def test_code_execution_classified_as_critical(self, crash_info: CrashInfo) -> None:
        """Crashes with code execution indicators SHALL be classified as CRITICAL.

        **Validates: Requirements 16.1**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.CRITICAL

    # -------------------------------------------------------------------------
    # Property: HIGH classification for DoS/information disclosure
    # -------------------------------------------------------------------------

    @given(crash_info_strategy(stack_trace=high_severity_stack_trace()))
    @settings(max_examples=100, deadline=None)
    def test_dos_disclosure_classified_as_high(self, crash_info: CrashInfo) -> None:
        """Crashes with DoS or information disclosure patterns SHALL be classified as HIGH.

        **Validates: Requirements 16.2**
        """
        result = self.classifier.classify(crash_info)
        # HIGH severity patterns should result in HIGH classification
        # unless there's also a CRITICAL pattern (which takes precedence)
        assert result in [Severity.CRITICAL, Severity.HIGH]

    @given(
        crash_info_strategy(
            crash_type=st.sampled_from(['timeout', 'Timeout', 'TIMEOUT']),
            stack_trace=low_severity_stack_trace(),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_timeout_crash_type_classified_as_high(self, crash_info: CrashInfo) -> None:
        """Crashes with timeout crash_type SHALL be classified as HIGH.

        **Validates: Requirements 16.2**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.HIGH

    @given(
        crash_info_strategy(
            crash_type=st.sampled_from(['oom', 'OOM', 'out of memory']),
            stack_trace=low_severity_stack_trace(),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_oom_crash_type_classified_as_high(self, crash_info: CrashInfo) -> None:
        """Crashes with OOM crash_type SHALL be classified as HIGH.

        **Validates: Requirements 16.2**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.HIGH

    # -------------------------------------------------------------------------
    # Property: MEDIUM classification for unhandled exceptions
    # -------------------------------------------------------------------------

    @given(
        crash_info_strategy(
            crash_type=st.just('exception'),
            stack_trace=medium_severity_stack_trace(),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_unhandled_exceptions_classified_as_medium(self, crash_info: CrashInfo) -> None:
        """Unhandled Python exceptions SHALL be classified as MEDIUM.

        **Validates: Requirements 16.3**
        """
        result = self.classifier.classify(crash_info)
        # MEDIUM unless there's a higher severity pattern
        assert result in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]

    # -------------------------------------------------------------------------
    # Property: LOW classification for minor issues
    # -------------------------------------------------------------------------

    @given(
        crash_info_strategy(
            crash_type=st.just('minor'),
            stack_trace=low_severity_stack_trace(),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_minor_issues_classified_as_low(self, crash_info: CrashInfo) -> None:
        """Crashes without security indicators SHALL be classified as LOW.

        **Validates: Requirements 16.1, 16.2, 16.3**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.LOW

    # -------------------------------------------------------------------------
    # Property: Classification is deterministic
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_classification_is_deterministic(self, crash_info: CrashInfo) -> None:
        """Classification SHALL be deterministic for the same crash information.

        **Validates: Requirements 16.1, 16.2, 16.3**
        """
        result1 = self.classifier.classify(crash_info)
        result2 = self.classifier.classify(crash_info)
        result3 = self.classifier.classify(crash_info)

        assert result1 == result2 == result3

    @given(st.data())
    @settings(max_examples=50, deadline=None)
    def test_same_crash_info_same_classification(self, data: st.DataObject) -> None:
        """Two CrashInfo objects with identical data SHALL have same classification.

        **Validates: Requirements 16.1, 16.2, 16.3**
        """
        # Generate crash info components
        target_name = data.draw(st.text(min_size=1, max_size=30).filter(lambda x: x.strip()))
        crash_type = data.draw(st.text(min_size=1, max_size=30))
        stack_trace = data.draw(st.text(min_size=0, max_size=200))
        input_data = data.draw(st.binary(min_size=1, max_size=50))

        # Create two identical CrashInfo objects
        crash1 = CrashInfo(
            target_name=target_name,
            crash_type=crash_type,
            stack_trace=stack_trace,
            input_data=input_data,
        )
        crash2 = CrashInfo(
            target_name=target_name,
            crash_type=crash_type,
            stack_trace=stack_trace,
            input_data=input_data,
        )

        result1 = self.classifier.classify(crash1)
        result2 = self.classifier.classify(crash2)

        assert result1 == result2

    # -------------------------------------------------------------------------
    # Property: Severity priority (CRITICAL > HIGH > MEDIUM > LOW)
    # -------------------------------------------------------------------------

    @given(
        crash_info_strategy(
            crash_type=st.sampled_from(['ASAN', 'timeout']),
            stack_trace=st.just('AddressSanitizer: heap-buffer-overflow\ntimeout detected'),
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_critical_takes_precedence_over_high(self, crash_info: CrashInfo) -> None:
        """When both CRITICAL and HIGH patterns present, CRITICAL takes precedence.

        **Validates: Requirements 16.1, 16.2**
        """
        result = self.classifier.classify(crash_info)
        # CRITICAL should take precedence
        assert result == Severity.CRITICAL

    @given(
        crash_info_strategy(
            stack_trace=st.just(
                'AddressSanitizer: heap-buffer-overflow\nTraceback (most recent call last):'
            ),
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_critical_takes_precedence_over_medium(self, crash_info: CrashInfo) -> None:
        """When both CRITICAL and MEDIUM patterns present, CRITICAL takes precedence.

        **Validates: Requirements 16.1, 16.3**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.CRITICAL

    @given(
        crash_info_strategy(
            crash_type=st.just('timeout'),
            stack_trace=st.just('timeout detected\nTraceback (most recent call last):'),
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_high_takes_precedence_over_medium(self, crash_info: CrashInfo) -> None:
        """When both HIGH and MEDIUM patterns present, HIGH takes precedence.

        **Validates: Requirements 16.2, 16.3**
        """
        result = self.classifier.classify(crash_info)
        assert result == Severity.HIGH


class TestClassifierWithSpecificPatterns:
    """Unit tests for specific pattern matching in classifier.

    These tests verify that specific known patterns are correctly classified.
    """

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.classifier = FindingClassifier()

    def test_heap_buffer_overflow_is_critical(self) -> None:
        """Heap buffer overflow should be CRITICAL.

        **Validates: Requirements 16.1**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='AddressSanitizer: heap-buffer-overflow on address 0x123',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.CRITICAL

    def test_use_after_free_is_critical(self) -> None:
        """Use-after-free should be CRITICAL.

        **Validates: Requirements 16.1**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='AddressSanitizer: heap-use-after-free on address 0x456',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.CRITICAL

    def test_segfault_is_critical(self) -> None:
        """Segmentation fault should be CRITICAL.

        **Validates: Requirements 16.1**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='Segmentation fault (core dumped)',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.CRITICAL

    def test_eval_code_execution_is_critical(self) -> None:
        """Code execution via eval should be CRITICAL.

        **Validates: Requirements 16.1**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='eval(user_input) executed malicious code',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.CRITICAL

    def test_timeout_is_high(self) -> None:
        """Timeout should be HIGH.

        **Validates: Requirements 16.2**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='timeout',
            stack_trace='Operation timed out after 30 seconds',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.HIGH

    def test_memory_error_is_high(self) -> None:
        """MemoryError should be HIGH.

        **Validates: Requirements 16.2**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='MemoryError: unable to allocate 1GB',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.HIGH

    def test_recursion_error_is_high(self) -> None:
        """RecursionError should be HIGH.

        **Validates: Requirements 16.2**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='RecursionError: maximum recursion depth exceeded',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.HIGH

    def test_sql_injection_is_high(self) -> None:
        """SQL injection detection should be HIGH.

        **Validates: Requirements 16.2**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='security',
            stack_trace='SQL injection detected in query parameter',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.HIGH

    def test_python_traceback_is_medium(self) -> None:
        """Python traceback should be MEDIUM.

        **Validates: Requirements 16.3**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='exception',
            stack_trace='Traceback (most recent call last):\n  File "test.py"\nValueError: bad',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.MEDIUM

    def test_generic_exception_is_medium(self) -> None:
        """Generic exception should be MEDIUM.

        **Validates: Requirements 16.3**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='exception',
            stack_trace='Exception: Something went wrong',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.MEDIUM

    def test_benign_crash_is_low(self) -> None:
        """Benign crash without security indicators should be LOW.

        **Validates: Requirements 16.1, 16.2, 16.3**
        """
        crash = CrashInfo(
            target_name='test_target',
            crash_type='minor',
            stack_trace='some benign log output with no security patterns',
            input_data=b'test',
        )
        assert self.classifier.classify(crash) == Severity.LOW


# =============================================================================
# Property Tests for Crash Report Completeness
# =============================================================================


class TestCrashReportCompleteness:
    """Property tests for crash report completeness.

    Feature: oss-fuzz-integration, Property 8: Crash Report Completeness
    Validates: Requirements 16.4, 16.5

    Property 8: Crash Report Completeness
    *For any* crash captured during fuzzing, the generated crash report SHALL contain:
    - The exact input bytes that caused the crash
    - A SHA256 hash of the input for deduplication
    - The full stack trace
    - The target name that crashed
    - A timestamp of when the crash occurred
    """

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.classifier = FindingClassifier()

    # -------------------------------------------------------------------------
    # Property: Report contains target name
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_target_name(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL contain the target name that crashed.

        **Validates: Requirements 16.4, 16.5**
        """
        report = self.classifier.generate_report(crash_info)

        # The target name must appear in the report
        assert crash_info.target_name in report, (
            f"Target name '{crash_info.target_name}' not found in report"
        )

    # -------------------------------------------------------------------------
    # Property: Report contains input hash for deduplication
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_input_hash(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL contain SHA256 hash of input for deduplication.

        **Validates: Requirements 16.4, 16.5**
        """
        report = self.classifier.generate_report(crash_info)

        # The input hash must appear in the report
        assert crash_info.input_hash in report, (
            f"Input hash '{crash_info.input_hash}' not found in report"
        )

        # Verify the hash is a valid SHA256 (64 hex characters)
        assert len(crash_info.input_hash) == 64, (
            f'Input hash should be 64 characters, got {len(crash_info.input_hash)}'
        )
        assert all(c in '0123456789abcdef' for c in crash_info.input_hash), (
            'Input hash should only contain hex characters'
        )

    # -------------------------------------------------------------------------
    # Property: Report contains full stack trace
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_stack_trace(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL contain the full stack trace.

        **Validates: Requirements 16.5**
        """
        report = self.classifier.generate_report(crash_info)

        # The full stack trace must appear in the report
        assert crash_info.stack_trace in report, (
            f'Stack trace not found in report. Expected:\n{crash_info.stack_trace}'
        )

    # -------------------------------------------------------------------------
    # Property: Report contains timestamp
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_timestamp(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL contain a timestamp of when the crash occurred.

        **Validates: Requirements 16.4, 16.5**
        """
        report = self.classifier.generate_report(crash_info)

        # The timestamp should appear in ISO format in the report
        timestamp_str = crash_info.timestamp.isoformat()
        assert timestamp_str in report, f"Timestamp '{timestamp_str}' not found in report"

    # -------------------------------------------------------------------------
    # Property: Report contains input data representation
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_input_data_representation(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL contain representation of the exact input bytes.

        **Validates: Requirements 16.4, 16.5**

        The input data should be represented either as:
        - UTF-8 decoded string (if printable)
        - Hex representation (if binary)
        """
        report = self.classifier.generate_report(crash_info)

        # Check that input data section exists
        assert 'INPUT DATA' in report, 'Report should have INPUT DATA section'

        # The input should be represented in some form
        # Either as UTF-8 or as hex
        try:
            decoded = crash_info.input_data.decode('utf-8')
            if all(c.isprintable() or c in '\n\r\t' for c in decoded):
                # Should be UTF-8 representation
                assert 'UTF-8' in report or decoded in report, (
                    'UTF-8 decodable input should appear in report'
                )
            else:
                # Should be hex representation
                assert 'Hex' in report, 'Non-printable input should be shown as hex'
        except UnicodeDecodeError:
            # Should be hex representation
            assert 'Hex' in report, 'Binary input should be shown as hex'

    # -------------------------------------------------------------------------
    # Property: CrashInfo automatically computes SHA256 hash
    # -------------------------------------------------------------------------

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=100, deadline=None)
    def test_crash_info_computes_sha256_hash(self, input_data: bytes) -> None:
        """CrashInfo SHALL automatically compute SHA256 hash of input data.

        **Validates: Requirements 16.4**
        """
        import hashlib

        crash_info = CrashInfo(
            target_name='test_target',
            crash_type='crash',
            stack_trace='test stack trace',
            input_data=input_data,
        )

        # Hash should be computed automatically
        expected_hash = hashlib.sha256(input_data).hexdigest()
        assert crash_info.input_hash == expected_hash, (
            f'Expected hash {expected_hash}, got {crash_info.input_hash}'
        )

    # -------------------------------------------------------------------------
    # Property: Same input produces same hash (deduplication)
    # -------------------------------------------------------------------------

    @given(st.binary(min_size=1, max_size=500))
    @settings(max_examples=100, deadline=None)
    def test_same_input_produces_same_hash(self, input_data: bytes) -> None:
        """Same input bytes SHALL produce same hash for deduplication.

        **Validates: Requirements 16.4**
        """
        crash1 = CrashInfo(
            target_name='target1',
            crash_type='crash1',
            stack_trace='trace1',
            input_data=input_data,
        )
        crash2 = CrashInfo(
            target_name='target2',
            crash_type='crash2',
            stack_trace='trace2',
            input_data=input_data,
        )

        # Same input should produce same hash regardless of other fields
        assert crash1.input_hash == crash2.input_hash, (
            'Same input data should produce same hash for deduplication'
        )

    # -------------------------------------------------------------------------
    # Property: Different inputs produce different hashes
    # -------------------------------------------------------------------------

    @given(
        st.binary(min_size=1, max_size=500),
        st.binary(min_size=1, max_size=500),
    )
    @settings(max_examples=100, deadline=None)
    def test_different_inputs_produce_different_hashes(self, input1: bytes, input2: bytes) -> None:
        """Different input bytes SHALL produce different hashes.

        **Validates: Requirements 16.4**
        """
        assume(input1 != input2)  # Only test when inputs are different

        crash1 = CrashInfo(
            target_name='target',
            crash_type='crash',
            stack_trace='trace',
            input_data=input1,
        )
        crash2 = CrashInfo(
            target_name='target',
            crash_type='crash',
            stack_trace='trace',
            input_data=input2,
        )

        # Different inputs should produce different hashes
        assert crash1.input_hash != crash2.input_hash, (
            'Different input data should produce different hashes'
        )

    # -------------------------------------------------------------------------
    # Property: Report is complete (contains all required fields)
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_is_complete(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL contain all required fields for debugging.

        **Validates: Requirements 16.4, 16.5**

        Required fields:
        - Target name
        - Severity classification
        - Crash type
        - Timestamp
        - Input hash
        - Input data representation
        - Stack trace
        """
        report = self.classifier.generate_report(crash_info)

        # Check all required sections/fields are present
        required_elements = [
            ('Target:', 'Target name label'),
            (crash_info.target_name, 'Target name value'),
            ('Severity:', 'Severity label'),
            ('Crash Type:', 'Crash type label'),
            (crash_info.crash_type, 'Crash type value'),
            ('Timestamp:', 'Timestamp label'),
            ('Input Hash:', 'Input hash label'),
            (crash_info.input_hash, 'Input hash value'),
            ('INPUT DATA', 'Input data section'),
            ('STACK TRACE', 'Stack trace section'),
            (crash_info.stack_trace, 'Stack trace content'),
        ]

        for element, description in required_elements:
            assert element in report, f"Report missing {description}: '{element}'"

    # -------------------------------------------------------------------------
    # Property: Report format is consistent
    # -------------------------------------------------------------------------

    @given(crash_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_has_consistent_format(self, crash_info: CrashInfo) -> None:
        """Crash report SHALL have consistent format with clear sections.

        **Validates: Requirements 16.5**
        """
        report = self.classifier.generate_report(crash_info)

        # Report should have header
        assert 'FUZZING CRASH REPORT' in report, "Report should have 'FUZZING CRASH REPORT' header"

        # Report should have section separators
        assert '=' * 80 in report, 'Report should have section separators'
        assert '-' * 80 in report, 'Report should have subsection separators'

        # Sections should appear in logical order
        header_pos = report.find('FUZZING CRASH REPORT')
        input_pos = report.find('INPUT DATA')
        trace_pos = report.find('STACK TRACE')

        assert header_pos < input_pos < trace_pos, (
            'Report sections should be in order: header, input data, stack trace'
        )


class TestCrashInfoModel:
    """Unit tests for CrashInfo model validation and hash computation.

    These tests verify specific behaviors of the CrashInfo data model.
    """

    def test_crash_info_requires_target_name(self) -> None:
        """CrashInfo should require target_name field.

        **Validates: Requirements 16.4, 16.5**
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CrashInfo(
                crash_type='crash',
                stack_trace='trace',
                input_data=b'test',
            )

    def test_crash_info_requires_crash_type(self) -> None:
        """CrashInfo should require crash_type field.

        **Validates: Requirements 16.4, 16.5**
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CrashInfo(
                target_name='target',
                stack_trace='trace',
                input_data=b'test',
            )

    def test_crash_info_requires_stack_trace(self) -> None:
        """CrashInfo should require stack_trace field.

        **Validates: Requirements 16.5**
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CrashInfo(
                target_name='target',
                crash_type='crash',
                input_data=b'test',
            )

    def test_crash_info_requires_input_data(self) -> None:
        """CrashInfo should require input_data field.

        **Validates: Requirements 16.4**
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CrashInfo(
                target_name='target',
                crash_type='crash',
                stack_trace='trace',
            )

    def test_crash_info_auto_generates_timestamp(self) -> None:
        """CrashInfo should auto-generate timestamp if not provided.

        **Validates: Requirements 16.4, 16.5**
        """
        from datetime import datetime, timezone

        before = datetime.now(timezone.utc)
        crash = CrashInfo(
            target_name='target',
            crash_type='crash',
            stack_trace='trace',
            input_data=b'test',
        )
        after = datetime.now(timezone.utc)

        assert before <= crash.timestamp <= after, (
            'Timestamp should be auto-generated to current time'
        )

    def test_crash_info_preserves_exact_input_bytes(self) -> None:
        """CrashInfo should preserve exact input bytes.

        **Validates: Requirements 16.4**
        """
        test_inputs = [
            b'simple ascii',
            b'\x00\x01\x02\xff\xfe',  # Binary with null bytes
            b'unicode: \xc3\xa9\xc3\xa0',  # UTF-8 encoded
            b'mixed\x00binary\xffdata',
            bytes(range(256)),  # All byte values
        ]

        for input_data in test_inputs:
            crash = CrashInfo(
                target_name='target',
                crash_type='crash',
                stack_trace='trace',
                input_data=input_data,
            )
            assert crash.input_data == input_data, (
                f'Input data should be preserved exactly: {input_data!r}'
            )

    def test_crash_info_hash_is_sha256(self) -> None:
        """CrashInfo hash should be valid SHA256.

        **Validates: Requirements 16.4**
        """
        import hashlib

        input_data = b'test input for hashing'
        crash = CrashInfo(
            target_name='target',
            crash_type='crash',
            stack_trace='trace',
            input_data=input_data,
        )

        expected = hashlib.sha256(input_data).hexdigest()
        assert crash.input_hash == expected
        assert len(crash.input_hash) == 64  # SHA256 produces 64 hex chars

    def test_crash_info_with_reproducer_path(self) -> None:
        """CrashInfo should support optional reproducer_path.

        **Validates: Requirements 16.4**
        """
        from pathlib import Path

        crash = CrashInfo(
            target_name='target',
            crash_type='crash',
            stack_trace='trace',
            input_data=b'test',
            reproducer_path=Path('/tmp/crash-123'),
        )

        assert crash.reproducer_path == Path('/tmp/crash-123')

    def test_report_includes_reproducer_path_when_present(self) -> None:
        """Report should include reproducer path when provided.

        **Validates: Requirements 16.4, 16.5**
        """
        from pathlib import Path

        classifier = FindingClassifier()
        crash = CrashInfo(
            target_name='target',
            crash_type='crash',
            stack_trace='trace',
            input_data=b'test',
            reproducer_path=Path('/tmp/crash-reproducer-abc123'),
        )

        report = classifier.generate_report(crash)

        assert 'REPRODUCER' in report, 'Report should have reproducer section'
        assert '/tmp/crash-reproducer-abc123' in report, 'Report should include reproducer path'
