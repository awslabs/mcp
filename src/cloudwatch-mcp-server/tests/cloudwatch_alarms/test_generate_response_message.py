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

"""Comprehensive tests for the _generate_response_message method.

This module contains focused unit tests for the _generate_response_message method
in the CloudWatchAlarmsTools class. The tests cover all possible combinations of
parameters and edge cases to ensure complete test coverage.

The _generate_response_message method is responsible for generating appropriate
response messages for LLM agents based on filtering results, pagination state,
and alarm counts.
"""

import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools import CloudWatchAlarmsTools


class TestGenerateResponseMessage:
    """Comprehensive tests for the _generate_response_message method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CloudWatchAlarmsTools()

    def test_empty_results_with_autoscaling_included(self):
        """Test empty results when autoscaling alarms are included."""
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=0,
        )
        assert result == 'No active alarms found'

    def test_empty_results_with_autoscaling_included_and_processed_alarms(self):
        """Test empty results when autoscaling alarms are included but some alarms were processed."""
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=5,
        )
        assert result == 'No active alarms found'

    def test_empty_results_with_no_alarms_processed(self):
        """Test empty results when no alarms were processed at all."""
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=0,
        )
        assert result == 'No active alarms found'

    def test_empty_results_with_filtering_and_filtered_alarms(self):
        """Test empty results when filtering is enabled and some alarms were filtered out."""
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=3,
            total_processed=3,
        )
        expected = 'No non-autoscaling active alarms found. 3 autoscaling alarms were filtered out. Set include_autoscaling_alarms=True to see all alarms.'
        assert result == expected

    def test_empty_results_with_filtering_and_no_filtered_alarms(self):
        """Test empty results when filtering is enabled but no alarms were filtered out."""
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=2,
        )
        assert result == 'No non-autoscaling active alarms found'

    def test_results_with_autoscaling_included_and_more_results(self):
        """Test results when autoscaling alarms are included and more results are available."""
        result = self.tools._generate_response_message(
            items_to_return=5,
            has_more_results=True,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=10,
        )
        assert result == 'Showing 5 alarms (more available)'

    def test_results_with_autoscaling_included_and_no_more_results(self):
        """Test results when autoscaling alarms are included and no more results are available."""
        result = self.tools._generate_response_message(
            items_to_return=5,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=5,
        )
        assert result is None

    def test_results_with_filtering_and_filtered_alarms_and_more_results(self):
        """Test results when filtering is enabled, alarms were filtered, and more results are available."""
        result = self.tools._generate_response_message(
            items_to_return=3,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=2,
            total_processed=8,
        )
        expected = 'Showing 3 non-autoscaling alarms (filtered out 2 autoscaling alarms, more non-autoscaling alarms available)'
        assert result == expected

    def test_results_with_filtering_and_filtered_alarms_and_no_more_results(self):
        """Test results when filtering is enabled, alarms were filtered, and no more results are available."""
        result = self.tools._generate_response_message(
            items_to_return=3,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=2,
            total_processed=5,
        )
        expected = 'Found 3 non-autoscaling alarms (filtered out 2 autoscaling alarms)'
        assert result == expected

    def test_results_with_filtering_and_no_filtered_alarms_and_more_results(self):
        """Test results when filtering is enabled, no alarms were filtered, and more results are available."""
        result = self.tools._generate_response_message(
            items_to_return=4,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=8,
        )
        expected = 'Showing 4 alarms (no autoscaling alarms found, more alarms available)'
        assert result == expected

    def test_results_with_filtering_and_no_filtered_alarms_and_no_more_results(self):
        """Test results when filtering is enabled, no alarms were filtered, and no more results are available."""
        result = self.tools._generate_response_message(
            items_to_return=4,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=4,
        )
        expected = 'Found 4 alarms (no autoscaling alarms found)'
        assert result == expected

    def test_edge_case_zero_items_with_large_filtered_count(self):
        """Test edge case with zero items returned but large filtered count."""
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=100,
            total_processed=100,
        )
        expected = 'No non-autoscaling active alarms found. 100 autoscaling alarms were filtered out. Set include_autoscaling_alarms=True to see all alarms.'
        assert result == expected

    def test_edge_case_single_item_with_filtering_and_more_results(self):
        """Test edge case with single item returned, filtering enabled, and more results available."""
        result = self.tools._generate_response_message(
            items_to_return=1,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=5,
            total_processed=10,
        )
        expected = 'Showing 1 non-autoscaling alarms (filtered out 5 autoscaling alarms, more non-autoscaling alarms available)'
        assert result == expected

    def test_edge_case_single_item_with_no_filtering_and_no_more_results(self):
        """Test edge case with single item returned, no filtering, and no more results available."""
        result = self.tools._generate_response_message(
            items_to_return=1,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=1,
        )
        expected = 'Found 1 alarms (no autoscaling alarms found)'
        assert result == expected

    def test_parameter_boundary_conditions(self):
        """Test various boundary conditions for parameters."""
        # Test with maximum reasonable values
        result = self.tools._generate_response_message(
            items_to_return=1000,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=500,
            total_processed=2000,
        )
        expected = 'Showing 1000 non-autoscaling alarms (filtered out 500 autoscaling alarms, more non-autoscaling alarms available)'
        assert result == expected

        # Test with zero filtered count but non-zero processed
        result = self.tools._generate_response_message(
            items_to_return=10,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=10,
        )
        expected = 'Found 10 alarms (no autoscaling alarms found)'
        assert result == expected

    def test_all_combinations_of_boolean_parameters(self):
        """Test all combinations of boolean parameters with non-zero items."""
        # include_autoscaling_alarms=True, has_more_results=True
        result = self.tools._generate_response_message(
            items_to_return=5,
            has_more_results=True,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=10,
        )
        assert result == 'Showing 5 alarms (more available)'

        # include_autoscaling_alarms=True, has_more_results=False
        result = self.tools._generate_response_message(
            items_to_return=5,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=5,
        )
        assert result is None

        # include_autoscaling_alarms=False, has_more_results=True, filtered_count > 0
        result = self.tools._generate_response_message(
            items_to_return=3,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=2,
            total_processed=8,
        )
        expected = 'Showing 3 non-autoscaling alarms (filtered out 2 autoscaling alarms, more non-autoscaling alarms available)'
        assert result == expected

        # include_autoscaling_alarms=False, has_more_results=False, filtered_count > 0
        result = self.tools._generate_response_message(
            items_to_return=3,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=2,
            total_processed=5,
        )
        expected = 'Found 3 non-autoscaling alarms (filtered out 2 autoscaling alarms)'
        assert result == expected

        # include_autoscaling_alarms=False, has_more_results=True, filtered_count = 0
        result = self.tools._generate_response_message(
            items_to_return=4,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=8,
        )
        expected = 'Showing 4 alarms (no autoscaling alarms found, more alarms available)'
        assert result == expected

        # include_autoscaling_alarms=False, has_more_results=False, filtered_count = 0
        result = self.tools._generate_response_message(
            items_to_return=4,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=4,
        )
        expected = 'Found 4 alarms (no autoscaling alarms found)'
        assert result == expected

    def test_message_content_accuracy(self):
        """Test that message content accurately reflects the parameters."""
        # Test that filtered count is correctly included in message
        result = self.tools._generate_response_message(
            items_to_return=2,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=7,
            total_processed=9,
        )
        assert result is not None
        assert '2 non-autoscaling alarms' in result
        assert 'filtered out 7 autoscaling alarms' in result
        assert 'more' not in result  # Should not mention more results

        # Test that items_to_return count is correctly included
        result = self.tools._generate_response_message(
            items_to_return=15,
            has_more_results=True,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=20,
        )
        assert result is not None
        assert 'Showing 15 alarms' in result
        assert 'more available' in result

    def test_return_type_consistency(self):
        """Test that return types are consistent (str or None)."""
        # Test cases that should return strings
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=0,
        )
        assert isinstance(result, str)

        result = self.tools._generate_response_message(
            items_to_return=5,
            has_more_results=True,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=10,
        )
        assert isinstance(result, str)

        # Test case that should return None
        result = self.tools._generate_response_message(
            items_to_return=5,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,
            total_processed=5,
        )
        assert result is None

    def test_logical_consistency_of_parameters(self):
        """Test logical consistency between parameters."""
        # When items_to_return > 0 and include_autoscaling_alarms=False,
        # filtered_count should be <= total_processed - items_to_return
        result = self.tools._generate_response_message(
            items_to_return=3,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=2,  # 2 filtered + 3 returned = 5 total processed
            total_processed=5,
        )
        expected = 'Found 3 non-autoscaling alarms (filtered out 2 autoscaling alarms)'
        assert result == expected

        # Test with edge case where filtered_count equals total_processed - items_to_return
        result = self.tools._generate_response_message(
            items_to_return=1,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=9,  # 9 filtered + 1 returned = 10 total processed
            total_processed=10,
        )
        expected = 'Found 1 non-autoscaling alarms (filtered out 9 autoscaling alarms)'
        assert result == expected


class TestGenerateResponseMessageIntegration:
    """Integration tests for _generate_response_message with realistic scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CloudWatchAlarmsTools()

    def test_realistic_scenario_mixed_alarms_with_pagination(self):
        """Test realistic scenario with mixed alarms and pagination."""
        # Scenario: 50 total alarms, 30 autoscaling, 20 non-autoscaling, requesting 10
        result = self.tools._generate_response_message(
            items_to_return=10,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=30,
            total_processed=50,
        )
        expected = 'Showing 10 non-autoscaling alarms (filtered out 30 autoscaling alarms, more non-autoscaling alarms available)'
        assert result == expected

    def test_realistic_scenario_all_autoscaling_alarms(self):
        """Test realistic scenario where all alarms are autoscaling."""
        # Scenario: All 25 alarms are autoscaling, filtering enabled
        result = self.tools._generate_response_message(
            items_to_return=0,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=25,
            total_processed=25,
        )
        expected = 'No non-autoscaling active alarms found. 25 autoscaling alarms were filtered out. Set include_autoscaling_alarms=True to see all alarms.'
        assert result == expected

    def test_realistic_scenario_no_autoscaling_alarms(self):
        """Test realistic scenario where no alarms are autoscaling."""
        # Scenario: 15 alarms, none are autoscaling, filtering enabled
        result = self.tools._generate_response_message(
            items_to_return=15,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=0,
            total_processed=15,
        )
        expected = 'Found 15 alarms (no autoscaling alarms found)'
        assert result == expected

    def test_realistic_scenario_backward_compatibility(self):
        """Test realistic scenario for backward compatibility (filtering disabled)."""
        # Scenario: 20 alarms total, filtering disabled (backward compatibility)
        result = self.tools._generate_response_message(
            items_to_return=20,
            has_more_results=False,
            include_autoscaling_alarms=True,
            filtered_count=0,  # No filtering occurred
            total_processed=20,
        )
        assert result is None  # No message needed for successful results without filtering

    def test_realistic_scenario_large_scale_filtering(self):
        """Test realistic scenario with large-scale filtering."""
        # Scenario: 500 total alarms, 450 autoscaling, 50 non-autoscaling, requesting 25
        result = self.tools._generate_response_message(
            items_to_return=25,
            has_more_results=True,
            include_autoscaling_alarms=False,
            filtered_count=450,
            total_processed=500,
        )
        expected = 'Showing 25 non-autoscaling alarms (filtered out 450 autoscaling alarms, more non-autoscaling alarms available)'
        assert result == expected

    def test_realistic_scenario_small_dataset(self):
        """Test realistic scenario with small dataset."""
        # Scenario: 3 total alarms, 1 autoscaling, 2 non-autoscaling, requesting 10
        result = self.tools._generate_response_message(
            items_to_return=2,
            has_more_results=False,
            include_autoscaling_alarms=False,
            filtered_count=1,
            total_processed=3,
        )
        expected = 'Found 2 non-autoscaling alarms (filtered out 1 autoscaling alarms)'
        assert result == expected