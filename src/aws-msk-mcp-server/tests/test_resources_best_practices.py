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

"""Unit tests for the resources/best_practices.py module."""

import json
import pytest
import unittest
from awslabs.aws_msk_mcp_server.resources.best_practices import (
    INSTANCE_SPECS,
    LEADER_IMBALANCE_TOLERANCE_PERCENT,
    MAX_CPU_UTILIZATION_PERCENT,
    RECOMMENDED_CPU_UTILIZATION_PERCENT,
    RECOMMENDED_MIN_INSYNC_REPLICAS,
    RECOMMENDED_REPLICATION_FACTOR,
    STORAGE_UTILIZATION_CRITICAL_PERCENT,
    STORAGE_UTILIZATION_WARNING_PERCENT,
    UNDER_REPLICATED_PARTITIONS_TOLERANCE,
    get_cluster_best_practices,
    register_module,
)
from unittest.mock import MagicMock


class TestBestPractices:
    """Tests for the best_practices.py module."""

    def test_get_cluster_best_practices_valid_instance(self):
        """Test get_cluster_best_practices with a valid instance type."""
        # Test with a standard instance type
        instance_type = 'kafka.m5.large'
        num_brokers = 3

        result = get_cluster_best_practices(instance_type, num_brokers)

        # Verify the result contains expected fields
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == f'{num_brokers} (provided as input)'
        assert result['vCPU per Broker'] == INSTANCE_SPECS[instance_type]['vCPU']
        assert (
            result['Memory (GB) per Broker']
            == f'{INSTANCE_SPECS[instance_type]["Memory (GB)"]} (available on the host)'
        )

        # Verify calculated fields
        expected_recommended_partitions = (
            INSTANCE_SPECS[instance_type]['Partitions per Broker Recommended'] * num_brokers
        )
        assert result['Recommended Max Partitions per Cluster'] == expected_recommended_partitions

        # Verify replication factor and min in-sync replicas
        assert f'{RECOMMENDED_REPLICATION_FACTOR} (recommended)' == result['Replication Factor']
        assert result['Minimum In-Sync Replicas'] == RECOMMENDED_MIN_INSYNC_REPLICAS

    def test_get_cluster_best_practices_express_instance(self):
        """Test get_cluster_best_practices with an express instance type."""
        # Test with an express instance type
        instance_type = 'express.m7g.large'
        num_brokers = 2

        result = get_cluster_best_practices(instance_type, num_brokers)

        # Verify the result contains expected fields
        assert result['Instance Type'] == f'{instance_type} (provided as input)'

        # For express clusters, replication factor should always be 3
        assert (
            '3 (Note: For express clusters, replication factor should always be 3)'
            == result['Replication Factor']
        )

    def test_get_cluster_best_practices_invalid_instance(self):
        """Test get_cluster_best_practices with an invalid instance type."""
        instance_type = 'invalid.instance.type'
        num_brokers = 3

        result = get_cluster_best_practices(instance_type, num_brokers)

        # Verify the result contains an error message
        assert 'Error' in result
        assert (
            result['Error'] == f"Instance type '{instance_type}' is not supported or recognized."
        )

    def test_get_cluster_best_practices_small_cluster(self):
        """Test get_cluster_best_practices with a small number of brokers."""
        instance_type = 'kafka.m5.large'
        num_brokers = 1  # Smaller than recommended replication factor

        result = get_cluster_best_practices(instance_type, num_brokers)

        # Verify replication factor and min in-sync replicas are adjusted
        assert f'{num_brokers} (recommended)' == result['Replication Factor']
        assert result['Minimum In-Sync Replicas'] == num_brokers

    @pytest.mark.asyncio
    async def test_register_module(self):
        """Test that register_module registers the expected resources."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call the function under test
        await register_module(mock_mcp)

        # Verify that mcp.resource was called twice (once for each resource)
        assert mock_mcp.resource.call_count == 2

        # Verify the first resource registration (msk_best_practices)
        first_call_args = mock_mcp.resource.call_args_list[0][1]
        assert first_call_args['uri'] == 'resource://msk-best-practices'
        assert first_call_args['name'] == 'MSKBestPractices'
        assert first_call_args['mime_type'] == 'application/json'

        # Verify the second resource registration (msk_cluster_best_practices)
        second_call_args = mock_mcp.resource.call_args_list[1][1]
        assert (
            second_call_args['uri']
            == 'resource://msk-best-practices/cluster/{instance_type}/{number_of_brokers}'
        )
        assert second_call_args['name'] == 'MSKClusterBestPractices'
        assert second_call_args['mime_type'] == 'application/json'

    @pytest.mark.asyncio
    async def test_msk_best_practices_resource(self):
        """Test the msk_best_practices resource function."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        await register_module(mock_mcp)

        # Extract the msk_best_practices function
        msk_best_practices_func = mock_resource_decorator.call_args_list[0][0][0]

        # Call the function
        result_json = await msk_best_practices_func()

        # Parse the JSON result
        result = json.loads(result_json)

        # Verify the result structure
        assert 'thresholds' in result
        assert 'instance_specs' in result
        assert 'instance_categories' in result

        # Verify thresholds
        assert (
            result['thresholds']['cpu_utilization']['recommended_max']
            == RECOMMENDED_CPU_UTILIZATION_PERCENT
        )
        assert (
            result['thresholds']['cpu_utilization']['critical_max'] == MAX_CPU_UTILIZATION_PERCENT
        )
        assert (
            result['thresholds']['disk_utilization']['warning']
            == STORAGE_UTILIZATION_WARNING_PERCENT
        )
        assert (
            result['thresholds']['disk_utilization']['critical']
            == STORAGE_UTILIZATION_CRITICAL_PERCENT
        )

        # Verify instance categories
        assert all(key.startswith('kafka.') for key in result['instance_categories']['standard'])
        assert all(key.startswith('express.') for key in result['instance_categories']['express'])

        # Verify that all instance types are included
        for instance_type in INSTANCE_SPECS.keys():
            assert instance_type in result['instance_specs']

        # Verify that the instance specs match the constants
        assert result['instance_specs'] == INSTANCE_SPECS

        # Verify replication thresholds
        assert (
            result['thresholds']['replication']['recommended_factor']
            == RECOMMENDED_REPLICATION_FACTOR
        )
        assert (
            result['thresholds']['replication']['min_insync_replicas']
            == RECOMMENDED_MIN_INSYNC_REPLICAS
        )
        assert 'description' in result['thresholds']['replication']

        # Verify under-replicated partitions threshold
        assert (
            result['thresholds']['under_replicated_partitions']['tolerance']
            == UNDER_REPLICATED_PARTITIONS_TOLERANCE
        )
        assert 'description' in result['thresholds']['under_replicated_partitions']

        # Verify leader imbalance threshold
        assert (
            result['thresholds']['leader_imbalance']['tolerance_percent']
            == LEADER_IMBALANCE_TOLERANCE_PERCENT
        )
        assert 'description' in result['thresholds']['leader_imbalance']

    @pytest.mark.asyncio
    async def test_msk_cluster_best_practices_resource(self):
        """Test the msk_cluster_best_practices resource function."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        await register_module(mock_mcp)

        # Extract the msk_cluster_best_practices function
        msk_cluster_best_practices_func = mock_resource_decorator.call_args_list[1][0][0]

        # Call the function with valid parameters
        instance_type = 'kafka.m5.large'
        number_of_brokers = 3
        result_json = await msk_cluster_best_practices_func(instance_type, number_of_brokers)

        # Parse the JSON result
        result = json.loads(result_json)

        # Verify the result
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == f'{number_of_brokers} (provided as input)'

        # Call the function with an invalid instance type
        invalid_instance_type = 'invalid.instance.type'
        result_json = await msk_cluster_best_practices_func(
            invalid_instance_type, number_of_brokers
        )

        # Parse the JSON result
        result = json.loads(result_json)

        # Verify the result contains an error message
        assert 'Error' in result

    @pytest.mark.asyncio
    async def test_msk_cluster_best_practices_resource_with_express_instance(self):
        """Test the msk_cluster_best_practices resource function with an express instance."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        await register_module(mock_mcp)

        # Extract the msk_cluster_best_practices function
        msk_cluster_best_practices_func = mock_resource_decorator.call_args_list[1][0][0]

        # Call the function with an express instance type
        instance_type = 'express.m7g.large'
        number_of_brokers = 2
        result_json = await msk_cluster_best_practices_func(instance_type, number_of_brokers)

        # Parse the JSON result
        result = json.loads(result_json)

        # Verify the result
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == f'{number_of_brokers} (provided as input)'
        assert (
            '(Note: For express clusters, replication factor should always be 3)'
            in result['Replication Factor']
        )

    @pytest.mark.asyncio
    async def test_msk_cluster_best_practices_resource_with_small_cluster(self):
        """Test the msk_cluster_best_practices resource function with a small cluster."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        await register_module(mock_mcp)

        # Extract the msk_cluster_best_practices function
        msk_cluster_best_practices_func = mock_resource_decorator.call_args_list[1][0][0]

        # Call the function with a small number of brokers
        instance_type = 'kafka.m5.large'
        number_of_brokers = 1
        result_json = await msk_cluster_best_practices_func(instance_type, number_of_brokers)

        # Parse the JSON result
        result = json.loads(result_json)

        # Verify the result
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == f'{number_of_brokers} (provided as input)'
        assert f'{number_of_brokers} (recommended)' == result['Replication Factor']
        assert result['Minimum In-Sync Replicas'] == number_of_brokers

    @pytest.mark.asyncio
    async def test_msk_cluster_best_practices_resource_with_string_number(self):
        """Test the msk_cluster_best_practices resource function with a string number."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        await register_module(mock_mcp)

        # Extract the msk_cluster_best_practices function
        msk_cluster_best_practices_func = mock_resource_decorator.call_args_list[1][0][0]

        # Call the function with a string number
        instance_type = 'kafka.m5.large'
        number_of_brokers = '3'  # String instead of int
        result_json = await msk_cluster_best_practices_func(instance_type, number_of_brokers)

        # Parse the JSON result
        result = json.loads(result_json)

        # Verify the result
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == '3 (provided as input)'  # Should be converted to int


if __name__ == '__main__':
    unittest.main()
