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

"""Unit tests for constants module."""

import os
from awslabs.aws_healthomics_mcp_server import consts
from unittest.mock import patch


class TestConstants:
    """Test cases for constants configuration."""

    @patch.dict(os.environ, {'HEALTHOMICS_DEFAULT_MAX_RESULTS': '25'})
    def test_default_max_results_from_environment(self):
        """Test DEFAULT_MAX_RESULTS uses value from environment variable."""
        # Need to reload the module to pick up the environment variable
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 25

    @patch.dict(os.environ, {}, clear=True)
    def test_default_max_results_default_value(self):
        """Test DEFAULT_MAX_RESULTS uses default value when no environment variable."""
        # Need to reload the module to pick up the cleared environment
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 10

    @patch.dict(os.environ, {'HEALTHOMICS_DEFAULT_MAX_RESULTS': '100'})
    def test_default_max_results_custom_value(self):
        """Test DEFAULT_MAX_RESULTS uses custom value from environment."""
        # Need to reload the module to pick up the environment variable
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 100

    @patch.dict(os.environ, {'HEALTHOMICS_DEFAULT_MAX_RESULTS': 'invalid'})
    def test_default_max_results_invalid_value(self):
        """Test DEFAULT_MAX_RESULTS handles invalid environment variable value."""
        # Should fall back to default value of 10 when invalid value is provided
        import importlib
        from awslabs.aws_healthomics_mcp_server import consts

        importlib.reload(consts)

        assert consts.DEFAULT_MAX_RESULTS == 10


class TestServiceConstants:
    """Test cases for service constants."""

    def test_default_region(self):
        """Test DEFAULT_REGION constant."""
        assert consts.DEFAULT_REGION == 'us-east-1'

    def test_default_storage_type(self):
        """Test DEFAULT_STORAGE_TYPE constant."""
        assert consts.DEFAULT_STORAGE_TYPE == 'DYNAMIC'

    def test_default_omics_service_name(self):
        """Test DEFAULT_OMICS_SERVICE_NAME constant."""
        assert consts.DEFAULT_OMICS_SERVICE_NAME == 'omics'

    def test_healthomics_supported_regions(self):
        """Test HEALTHOMICS_SUPPORTED_REGIONS constant."""
        expected_regions = [
            'ap-southeast-1',
            'eu-central-1',
            'eu-west-1',
            'eu-west-2',
            'il-central-1',
            'us-east-1',
            'us-west-2',
        ]
        assert consts.HEALTHOMICS_SUPPORTED_REGIONS == expected_regions
        assert isinstance(consts.HEALTHOMICS_SUPPORTED_REGIONS, list)
        assert len(consts.HEALTHOMICS_SUPPORTED_REGIONS) > 0


class TestStorageTypes:
    """Test cases for storage type constants."""

    def test_storage_type_constants(self):
        """Test storage type constants."""
        assert consts.STORAGE_TYPE_STATIC == 'STATIC'
        assert consts.STORAGE_TYPE_DYNAMIC == 'DYNAMIC'

    def test_storage_types_list(self):
        """Test STORAGE_TYPES list contains expected values."""
        expected_types = ['STATIC', 'DYNAMIC']
        assert consts.STORAGE_TYPES == expected_types
        assert consts.STORAGE_TYPE_STATIC in consts.STORAGE_TYPES
        assert consts.STORAGE_TYPE_DYNAMIC in consts.STORAGE_TYPES


class TestCacheBehaviors:
    """Test cases for cache behavior constants."""

    def test_cache_behavior_constants(self):
        """Test cache behavior constants."""
        assert consts.CACHE_BEHAVIOR_ALWAYS == 'CACHE_ALWAYS'
        assert consts.CACHE_BEHAVIOR_ON_FAILURE == 'CACHE_ON_FAILURE'

    def test_cache_behaviors_list(self):
        """Test CACHE_BEHAVIORS list contains expected values."""
        expected_behaviors = ['CACHE_ALWAYS', 'CACHE_ON_FAILURE']
        assert consts.CACHE_BEHAVIORS == expected_behaviors
        assert consts.CACHE_BEHAVIOR_ALWAYS in consts.CACHE_BEHAVIORS
        assert consts.CACHE_BEHAVIOR_ON_FAILURE in consts.CACHE_BEHAVIORS


class TestRunStatuses:
    """Test cases for run status constants."""

    def test_run_status_constants(self):
        """Test run status constants."""
        assert consts.RUN_STATUS_PENDING == 'PENDING'
        assert consts.RUN_STATUS_STARTING == 'STARTING'
        assert consts.RUN_STATUS_RUNNING == 'RUNNING'
        assert consts.RUN_STATUS_COMPLETED == 'COMPLETED'
        assert consts.RUN_STATUS_FAILED == 'FAILED'
        assert consts.RUN_STATUS_CANCELLED == 'CANCELLED'

    def test_run_statuses_list(self):
        """Test RUN_STATUSES list contains all expected values."""
        expected_statuses = [
            'PENDING',
            'STARTING',
            'RUNNING',
            'COMPLETED',
            'FAILED',
            'CANCELLED',
        ]
        assert consts.RUN_STATUSES == expected_statuses
        assert len(consts.RUN_STATUSES) == 6

        # Verify all individual constants are in the list
        assert consts.RUN_STATUS_PENDING in consts.RUN_STATUSES
        assert consts.RUN_STATUS_STARTING in consts.RUN_STATUSES
        assert consts.RUN_STATUS_RUNNING in consts.RUN_STATUSES
        assert consts.RUN_STATUS_COMPLETED in consts.RUN_STATUSES
        assert consts.RUN_STATUS_FAILED in consts.RUN_STATUSES
        assert consts.RUN_STATUS_CANCELLED in consts.RUN_STATUSES


class TestExportTypes:
    """Test cases for export type constants."""

    def test_export_type_definition(self):
        """Test EXPORT_TYPE_DEFINITION constant."""
        assert consts.EXPORT_TYPE_DEFINITION == 'DEFINITION'


class TestErrorMessages:
    """Test cases for error message constants."""

    def test_error_message_constants(self):
        """Test error message constants."""
        assert consts.ERROR_INVALID_STORAGE_TYPE == 'Invalid storage type. Must be one of: {}'
        assert consts.ERROR_INVALID_CACHE_BEHAVIOR == 'Invalid cache behavior. Must be one of: {}'
        assert consts.ERROR_INVALID_RUN_STATUS == 'Invalid run status. Must be one of: {}'
        assert consts.ERROR_STATIC_STORAGE_REQUIRES_CAPACITY == (
            'Storage capacity is required when using STATIC storage type'
        )

    def test_error_messages_are_strings(self):
        """Test that all error messages are strings."""
        assert isinstance(consts.ERROR_INVALID_STORAGE_TYPE, str)
        assert isinstance(consts.ERROR_INVALID_CACHE_BEHAVIOR, str)
        assert isinstance(consts.ERROR_INVALID_RUN_STATUS, str)
        assert isinstance(consts.ERROR_STATIC_STORAGE_REQUIRES_CAPACITY, str)

    def test_error_messages_contain_placeholders(self):
        """Test that parameterized error messages contain format placeholders."""
        assert '{}' in consts.ERROR_INVALID_STORAGE_TYPE
        assert '{}' in consts.ERROR_INVALID_CACHE_BEHAVIOR
        assert '{}' in consts.ERROR_INVALID_RUN_STATUS
        # ERROR_STATIC_STORAGE_REQUIRES_CAPACITY doesn't have placeholders


class TestConstantsIntegration:
    """Integration tests for constants."""

    def test_storage_types_match_individual_constants(self):
        """Test that STORAGE_TYPES list matches individual storage type constants."""
        assert consts.STORAGE_TYPE_STATIC in consts.STORAGE_TYPES
        assert consts.STORAGE_TYPE_DYNAMIC in consts.STORAGE_TYPES
        assert len(consts.STORAGE_TYPES) == 2

    def test_cache_behaviors_match_individual_constants(self):
        """Test that CACHE_BEHAVIORS list matches individual cache behavior constants."""
        assert consts.CACHE_BEHAVIOR_ALWAYS in consts.CACHE_BEHAVIORS
        assert consts.CACHE_BEHAVIOR_ON_FAILURE in consts.CACHE_BEHAVIORS
        assert len(consts.CACHE_BEHAVIORS) == 2

    def test_run_statuses_completeness(self):
        """Test that RUN_STATUSES contains all defined run status constants."""
        # This test ensures we don't forget to add new statuses to the list
        individual_statuses = [
            consts.RUN_STATUS_PENDING,
            consts.RUN_STATUS_STARTING,
            consts.RUN_STATUS_RUNNING,
            consts.RUN_STATUS_COMPLETED,
            consts.RUN_STATUS_FAILED,
            consts.RUN_STATUS_CANCELLED,
        ]
        assert set(consts.RUN_STATUSES) == set(individual_statuses)

    def test_default_region_in_supported_regions(self):
        """Test that DEFAULT_REGION is included in HEALTHOMICS_SUPPORTED_REGIONS."""
        assert consts.DEFAULT_REGION in consts.HEALTHOMICS_SUPPORTED_REGIONS
