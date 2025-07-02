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

"""Test fixtures for the cost-explorer-mcp-server tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def reset_client_cache():
    """Reset the global client cache before each test."""
    import awslabs.cost_explorer_mcp_server.helpers

    # Reset the global client cache to ensure clean state for each test
    awslabs.cost_explorer_mcp_server.helpers._cost_explorer_client = None
    yield
    # Clean up after test
    awslabs.cost_explorer_mcp_server.helpers._cost_explorer_client = None


@pytest.fixture
def mock_cost_explorer_client():
    """Provide a mock Cost Explorer client for tests."""
    mock_client = MagicMock()

    # Set up common mock responses
    mock_client.get_dimension_values.return_value = {
        'DimensionValues': [
            {'Value': 'Amazon Elastic Compute Cloud - Compute'},
            {'Value': 'Amazon Simple Storage Service'},
        ]
    }

    mock_client.get_tags.return_value = {'Tags': ['dev', 'prod', 'test']}

    mock_client.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                'Groups': [
                    {
                        'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                        'Metrics': {'UnblendedCost': {'Amount': '100.50', 'Unit': 'USD'}},
                    }
                ],
            }
        ]
    }

    return mock_client


@pytest.fixture
def mock_aws_environment():
    """Mock AWS environment variables for testing."""
    with patch.dict('os.environ', {'AWS_REGION': 'us-east-1', 'AWS_PROFILE': 'test-profile'}):
        yield


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""
    context = MagicMock()
    return context


@pytest.fixture
def sample_cost_explorer_response():
    """Create a sample AWS Cost Explorer API response."""
    return {
        'GroupDefinitions': [{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                'Total': {},
                'Groups': [
                    {
                        'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                        'Metrics': {'UnblendedCost': {'Amount': '100.0', 'Unit': 'USD'}},
                    },
                    {
                        'Keys': ['Amazon Simple Storage Service'],
                        'Metrics': {'UnblendedCost': {'Amount': '50.0', 'Unit': 'USD'}},
                    },
                    {
                        'Keys': ['Amazon Relational Database Service'],
                        'Metrics': {'UnblendedCost': {'Amount': '200.0', 'Unit': 'USD'}},
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_dimension_values_response():
    """Create a sample AWS Cost Explorer dimension values response."""
    return {
        'DimensionValues': [
            {'Value': 'Amazon Elastic Compute Cloud - Compute', 'Attributes': {}},
            {'Value': 'Amazon Simple Storage Service', 'Attributes': {}},
            {'Value': 'Amazon Relational Database Service', 'Attributes': {}},
            {'Value': 'AWS Lambda', 'Attributes': {}},
            {'Value': 'Amazon DynamoDB', 'Attributes': {}},
        ],
        'ReturnSize': 5,
        'TotalSize': 5,
    }


@pytest.fixture
def sample_tag_values_response():
    """Create a sample AWS Cost Explorer tag values response."""
    return {'Tags': ['dev', 'prod', 'test', 'staging'], 'ReturnSize': 4, 'TotalSize': 4}


@pytest.fixture
def sample_usage_quantity_response():
    """Create a sample AWS Cost Explorer usage quantity response."""
    return {
        'GroupDefinitions': [{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                'Total': {},
                'Groups': [
                    {
                        'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                        'Metrics': {'UsageQuantity': {'Amount': '730.0', 'Unit': 'Hrs'}},
                    },
                    {
                        'Keys': ['Amazon Simple Storage Service'],
                        'Metrics': {'UsageQuantity': {'Amount': '1024.0', 'Unit': 'GB'}},
                    },
                ],
            }
        ],
    }
