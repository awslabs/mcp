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

"""Tests for utils module."""

from awslabs.cloudwatch_appsignals_mcp_server.utils import (
    calculate_name_similarity,
    parse_timestamp,
    remove_null_values,
)
from datetime import datetime, timedelta, timezone


class TestRemoveNullValues:
    """Test remove_null_values function."""

    def test_remove_null_values_basic(self):
        """Test removing None values from dictionary."""
        data = {'key1': 'value1', 'key2': None, 'key3': 'value3', 'key4': None}

        result = remove_null_values(data)

        assert result == {'key1': 'value1', 'key3': 'value3'}

    def test_remove_null_values_empty_dict(self):
        """Test with empty dictionary."""
        result = remove_null_values({})
        assert result == {}

    def test_remove_null_values_no_nulls(self):
        """Test with dictionary containing no None values."""
        data = {'key1': 'value1', 'key2': 'value2'}
        result = remove_null_values(data)
        assert result == data

    def test_remove_null_values_all_nulls(self):
        """Test with dictionary containing only None values."""
        data = {'key1': None, 'key2': None}
        result = remove_null_values(data)
        assert result == {}

    def test_remove_null_values_preserves_other_falsy(self):
        """Test that other falsy values are preserved."""
        data = {'empty_string': '', 'zero': 0, 'false': False, 'empty_list': [], 'none': None}

        result = remove_null_values(data)

        expected = {'empty_string': '', 'zero': 0, 'false': False, 'empty_list': []}
        assert result == expected


class TestParseTimestamp:
    """Test parse_timestamp function."""

    def test_parse_timestamp_unix_seconds(self):
        """Test parsing unix timestamp."""
        timestamp_str = '1640995200'  # 2022-01-01 00:00:00 UTC
        result = parse_timestamp(timestamp_str)

        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_iso_format_with_z(self):
        """Test parsing ISO format with Z suffix."""
        timestamp_str = '2022-01-01T00:00:00Z'
        result = parse_timestamp(timestamp_str)

        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_iso_format_with_offset(self):
        """Test parsing ISO format with timezone offset."""
        timestamp_str = '2022-01-01T00:00:00+00:00'
        result = parse_timestamp(timestamp_str)

        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_standard_format(self):
        """Test parsing standard 'YYYY-MM-DD HH:MM:SS' format."""
        timestamp_str = '2022-01-01 00:00:00'
        result = parse_timestamp(timestamp_str)

        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_non_string_input(self):
        """Test parsing non-string input (converted to string)."""
        timestamp_int = 1640995200
        result = parse_timestamp(str(timestamp_int))

        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_invalid_format_uses_default(self):
        """Test that invalid format falls back to default."""
        timestamp_str = 'invalid-timestamp'
        result = parse_timestamp(timestamp_str, default_hours=1)

        # Should be approximately 1 hour ago
        expected_time = datetime.now(timezone.utc) - timedelta(hours=1)
        time_diff = abs((result - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_parse_timestamp_empty_string_uses_default(self):
        """Test that empty string falls back to default."""
        result = parse_timestamp('', default_hours=2)

        # Should be approximately 2 hours ago
        expected_time = datetime.now(timezone.utc) - timedelta(hours=2)
        time_diff = abs((result - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_parse_timestamp_none_uses_default(self):
        """Test that None input falls back to default."""
        result = parse_timestamp('', default_hours=3)  # Use empty string instead of None

        # Should be approximately 3 hours ago
        expected_time = datetime.now(timezone.utc) - timedelta(hours=3)
        time_diff = abs((result - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_parse_timestamp_default_hours_parameter(self):
        """Test default_hours parameter works correctly."""
        result = parse_timestamp('invalid', default_hours=12)

        # Should be approximately 12 hours ago
        expected_time = datetime.now(timezone.utc) - timedelta(hours=12)
        time_diff = abs((result - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds


class TestCalculateNameSimilarity:
    """Test calculate_name_similarity function."""

    def test_exact_match(self):
        """Test exact match returns 100."""
        result = calculate_name_similarity('payment-service', 'payment-service')
        assert result == 100

    def test_case_insensitive_exact_match(self):
        """Test case insensitive exact match returns 100."""
        result = calculate_name_similarity('Payment-Service', 'payment-service')
        assert result == 100

    def test_normalized_match(self):
        """Test normalized match (different separators) returns 95."""
        result = calculate_name_similarity('payment_service', 'payment-service')
        assert result == 95

    def test_normalized_match_with_dots(self):
        """Test normalized match with dots returns 95."""
        result = calculate_name_similarity('payment.service', 'payment-service')
        assert result == 95

    def test_empty_strings(self):
        """Test empty strings return 0."""
        assert calculate_name_similarity('', 'test') == 0
        assert calculate_name_similarity('test', '') == 0
        assert calculate_name_similarity('', '') == 0

    def test_word_based_matching(self):
        """Test word-based matching."""
        result = calculate_name_similarity('payment service api', 'api payment service')
        assert result > 80  # Should have high score due to word matches

    def test_partial_word_matching(self):
        """Test partial word matching."""
        result = calculate_name_similarity('payment service', 'payment gateway service')
        assert result > 50  # Should have decent score due to common words

    def test_substring_matching_target_in_candidate(self):
        """Test substring matching when target is contained in candidate."""
        result = calculate_name_similarity('payment', 'payment-service-api')
        assert result > 5  # Should get some points for containment

    def test_substring_matching_candidate_in_target(self):
        """Test substring matching when candidate is contained in target."""
        result = calculate_name_similarity('payment-service-api', 'payment')
        assert result > 3  # Should get some points for containment

    def test_slo_key_terms_matching(self):
        """Test SLO-specific key terms matching."""
        result = calculate_name_similarity(
            'payment latency slo', 'payment service latency', name_type='slo'
        )
        assert result > 45  # Should get bonus for 'latency' key term

    def test_service_key_terms_matching(self):
        """Test service-specific key terms matching."""
        result = calculate_name_similarity(
            'payment service api', 'payment api service', name_type='service'
        )
        assert result > 70  # Should get bonus for 'service' and 'api' key terms

    def test_length_difference_penalty(self):
        """Test penalty for very different lengths."""
        # Very different lengths should be penalized
        short_name = 'api'
        long_name = 'very-long-service-name-with-many-words-that-dont-match'

        result = calculate_name_similarity(short_name, long_name)
        assert result < 50  # Should be penalized for length difference

    def test_moderate_length_difference_penalty(self):
        """Test moderate penalty for moderately different lengths."""
        name1 = 'payment-service'
        name2 = 'payment-service-with-extra-words'

        result = calculate_name_similarity(name1, name2)
        # Should still have some score but with penalty for length difference
        assert 10 < result < 50

    def test_no_common_words(self):
        """Test names with no common words."""
        result = calculate_name_similarity('payment-service', 'user-database')
        assert result < 30  # Should have low score

    def test_high_word_coverage_bonus(self):
        """Test bonus for high word coverage."""
        result = calculate_name_similarity('payment service', 'payment service api')
        assert result > 70  # Should get bonus for 80%+ word coverage

    def test_moderate_word_coverage_bonus(self):
        """Test bonus for moderate word coverage."""
        result = calculate_name_similarity('payment service api', 'payment service database cache')
        assert result > 30  # Should get bonus for common words

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        result = calculate_name_similarity('  payment service  ', 'payment-service')
        assert result > 5  # Should get some points after normalization

    def test_multiple_key_terms_slo(self):
        """Test multiple SLO key terms increase score."""
        result = calculate_name_similarity(
            'payment latency error slo',
            'payment service latency error monitoring',
            name_type='slo',
        )
        assert result > 45  # Should get bonus for multiple key terms

    def test_multiple_key_terms_service(self):
        """Test multiple service key terms increase score."""
        result = calculate_name_similarity(
            'payment api service backend', 'payment backend api microservice', name_type='service'
        )
        assert result >= 70  # Should get bonus for multiple key terms

    def test_score_capped_at_100(self):
        """Test that score is capped at 100."""
        # Even with many bonuses, score shouldn't exceed 100
        result = calculate_name_similarity('payment-service', 'payment-service')
        assert result == 100

    def test_score_minimum_zero(self):
        """Test that score doesn't go below 0."""
        # Even with penalties, score shouldn't go below 0
        result = calculate_name_similarity(
            'a', 'very-long-completely-different-service-name-with-no-similarity-whatsoever'
        )
        assert result >= 0

    def test_complex_similarity_scenario(self):
        """Test complex similarity scenario."""
        target = 'payment-gateway-service'
        candidate = 'payment_service_gateway_api'

        result = calculate_name_similarity(target, candidate, name_type='service')

        # Should have some score due to common words after normalization
        assert result > 5

    def test_different_name_types(self):
        """Test that name_type affects scoring."""
        target = 'payment latency'
        candidate = 'payment service latency'

        slo_score = calculate_name_similarity(target, candidate, name_type='slo')
        service_score = calculate_name_similarity(target, candidate, name_type='service')

        # SLO should score higher due to 'latency' being a key SLO term
        assert slo_score >= service_score
