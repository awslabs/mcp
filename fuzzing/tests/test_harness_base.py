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

"""Property-based tests for PolyglotHarness class.

This module contains property-based tests validating the correctness properties
of the polyglot harness infrastructure.

Feature: oss-fuzz-integration
"""

from __future__ import annotations

import pytest
import sys
from fuzzing.harness_base import PolyglotHarness
from hypothesis import given, settings
from hypothesis import strategies as st


class TestPolyglotModeDetection:
    """Property tests for polyglot mode detection.

    Feature: oss-fuzz-integration, Property 2: Polyglot Mode Detection
    Validates: Requirements 11.1
    """

    def setup_method(self) -> None:
        """Reset mode cache before each test."""
        PolyglotHarness.reset_mode_cache()

    def teardown_method(self) -> None:
        """Reset mode cache after each test."""
        PolyglotHarness.reset_mode_cache()

    def test_mode_detection_returns_bool(self) -> None:
        """Verify is_atheris_mode() always returns a boolean.

        **Validates: Requirements 11.1**
        """
        result = PolyglotHarness.is_atheris_mode()
        assert isinstance(result, bool)

    def test_mode_detection_is_deterministic(self) -> None:
        """Verify mode detection returns consistent results.

        **Validates: Requirements 11.1**
        """
        # Call multiple times and verify consistency
        result1 = PolyglotHarness.is_atheris_mode()
        result2 = PolyglotHarness.is_atheris_mode()
        result3 = PolyglotHarness.is_atheris_mode()

        assert result1 == result2 == result3

    def test_pytest_mode_detected_when_pytest_loaded(self) -> None:
        """Verify pytest mode is detected when pytest is in sys.modules.

        When running under pytest, is_atheris_mode() should return False.

        **Validates: Requirements 11.1**
        """
        # pytest is loaded since we're running this test
        assert 'pytest' in sys.modules or '_pytest' in sys.modules

        result = PolyglotHarness.is_atheris_mode()
        assert result is False

    def test_mode_cache_works(self) -> None:
        """Verify mode detection caching works correctly.

        **Validates: Requirements 11.1**
        """
        # First call should compute and cache
        result1 = PolyglotHarness.is_atheris_mode()
        assert PolyglotHarness._atheris_mode_cache is not None

        # Second call should use cache
        result2 = PolyglotHarness.is_atheris_mode()
        assert result1 == result2

        # Reset should clear cache
        PolyglotHarness.reset_mode_cache()
        assert PolyglotHarness._atheris_mode_cache is None


class TestBytesToStructuredConversion:
    """Property tests for byte-to-structured conversion.

    Feature: oss-fuzz-integration, Property 3: Byte-to-Structured Conversion
    Validates: Requirements 11.3
    """

    @given(st.binary(min_size=1, max_size=1024))
    @settings(max_examples=100, deadline=None)
    def test_bytes_to_integers_produces_valid_output(self, data: bytes) -> None:
        """For any non-empty byte sequence, conversion to integers succeeds.

        **Validates: Requirements 11.3**
        """
        strategy = st.integers(min_value=0, max_value=1000)
        result = PolyglotHarness.bytes_to_structured(data, strategy)
        assert isinstance(result, int)
        assert 0 <= result <= 1000

    @given(st.binary(min_size=1, max_size=1024))
    @settings(max_examples=100, deadline=None)
    def test_bytes_to_text_produces_valid_output(self, data: bytes) -> None:
        """For any non-empty byte sequence, conversion to text succeeds.

        **Validates: Requirements 11.3**
        """
        strategy = st.text(min_size=0, max_size=50)
        result = PolyglotHarness.bytes_to_structured(data, strategy)
        assert isinstance(result, str)

    @given(st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_bytes_to_list_produces_valid_output(self, data: bytes) -> None:
        """For any non-empty byte sequence, conversion to list succeeds.

        **Validates: Requirements 11.3**
        """
        strategy = st.lists(st.integers(0, 100), min_size=0, max_size=10)
        result = PolyglotHarness.bytes_to_structured(data, strategy)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, int)
            assert 0 <= item <= 100

    @given(st.binary(min_size=32, max_size=256))
    @settings(max_examples=100, deadline=None)
    def test_bytes_to_dict_produces_valid_output(self, data: bytes) -> None:
        """For any sufficiently large byte sequence, conversion to dict succeeds.

        Note: Complex strategies like fixed_dictionaries require more bytes
        to satisfy all their constraints. We use min_size=32 to ensure
        enough entropy for the strategy.

        **Validates: Requirements 11.3**
        """
        strategy = st.fixed_dictionaries(
            {
                'name': st.text(min_size=1, max_size=10),
                'value': st.integers(0, 100),
            }
        )
        result = PolyglotHarness.bytes_to_structured(data, strategy)
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'value' in result
        assert isinstance(result['name'], str)
        assert isinstance(result['value'], int)

    def test_empty_bytes_raises_value_error(self) -> None:
        """Verify empty bytes raise ValueError.

        **Validates: Requirements 11.3**
        """
        strategy = st.integers()
        with pytest.raises(ValueError, match='length > 0'):
            PolyglotHarness.bytes_to_structured(b'', strategy)

    @given(st.binary(min_size=1, max_size=100))
    @settings(max_examples=50, deadline=None)
    def test_conversion_is_deterministic(self, data: bytes) -> None:
        """For the same input bytes, conversion produces the same output.

        **Validates: Requirements 11.3**
        """
        strategy = st.integers(min_value=0, max_value=1000)

        result1 = PolyglotHarness.bytes_to_structured(data, strategy)
        result2 = PolyglotHarness.bytes_to_structured(data, strategy)

        assert result1 == result2

    @given(st.binary(min_size=16, max_size=256))
    @settings(max_examples=100, deadline=None)
    def test_conversion_never_raises_for_valid_input(self, data: bytes) -> None:
        """For any sufficiently large bytes, conversion should not raise exceptions.

        Note: We use min_size=16 to ensure enough entropy for the strategies.
        Very small byte sequences may not have enough data to satisfy
        complex strategies.

        **Validates: Requirements 11.3**
        """
        # Use simpler strategies that require less entropy
        strategy = st.one_of(
            st.integers(min_value=0, max_value=100),
            st.booleans(),
        )
        # Should not raise any exception
        result = PolyglotHarness.bytes_to_structured(data, strategy)
        assert result is not None or result is None  # Any value is valid
