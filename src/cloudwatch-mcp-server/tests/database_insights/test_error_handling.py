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

"""Tests for error handling in Database Insights tools."""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from awslabs.cloudwatch_mcp_server.database_insights.tools import DatabaseInsightsTools


def create_client_error(error_code: str, message: str) -> ClientError:
    """Create a ClientError for testing."""
    return ClientError(
        {'Error': {'Code': error_code, 'Message': message}},
        'TestOperation',
    )


@pytest.fixture
def db_insights_tools():
    """Create a DatabaseInsightsTools instance."""
    return DatabaseInsightsTools()


class TestDatabaseInsightsToolsClientCreation:
    """Test client creation error handling."""

    def test_get_rds_client_error(self, db_insights_tools):
        """Test handling of RDS client creation error."""
        with patch('boto3.Session') as mock_session:
            mock_session.return_value.client.side_effect = Exception('Connection failed')

            with pytest.raises(Exception) as exc_info:
                db_insights_tools._get_rds_client('us-east-1')
            assert 'Connection failed' in str(exc_info.value)

    def test_get_pi_client_error(self, db_insights_tools):
        """Test handling of PI client creation error."""
        with patch('boto3.Session') as mock_session:
            mock_session.return_value.client.side_effect = Exception('Connection failed')

            with pytest.raises(Exception) as exc_info:
                db_insights_tools._get_pi_client('us-east-1')
            assert 'Connection failed' in str(exc_info.value)


class TestClientErrorCreation:
    """Test ClientError creation helper."""

    def test_create_client_error(self):
        """Test creating a ClientError for testing."""
        error = create_client_error('AccessDenied', 'User is not authorized')
        assert error.response['Error']['Code'] == 'AccessDenied'
        assert error.response['Error']['Message'] == 'User is not authorized'

    def test_create_client_error_different_codes(self):
        """Test creating ClientErrors with different error codes."""
        error_codes = [
            ('InvalidParameterValue', 'Invalid parameter'),
            ('DBInstanceNotFound', 'Database not found'),
            ('ThrottlingException', 'Rate exceeded'),
        ]

        for code, message in error_codes:
            error = create_client_error(code, message)
            assert error.response['Error']['Code'] == code
            assert error.response['Error']['Message'] == message

