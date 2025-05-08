# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Pytest configuration for AWS Location Service MCP Server tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 client for testing."""
    mock_client = MagicMock()

    # Mock search_place_index_for_text response
    mock_client.search_place_index_for_text.return_value = {
        'Results': [
            {
                'Place': {
                    'Label': 'Seattle, WA, USA',
                    'Geometry': {'Point': [-122.3321, 47.6062]},
                    'Country': 'USA',
                    'Region': 'Washington',
                    'Municipality': 'Seattle',
                }
            }
        ]
    }

    with patch('boto3.client', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""
    context = MagicMock()

    # Make the error method awaitable
    async def async_error(*args, **kwargs):
        return None

    context.error = MagicMock(side_effect=async_error)
    return context
