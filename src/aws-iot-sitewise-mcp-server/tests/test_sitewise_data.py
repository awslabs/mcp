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

"""Tests for AWS IoT SiteWise Data Ingestion and Retrieval Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data import (
    batch_get_asset_property_aggregates,
    batch_get_asset_property_value,
    batch_get_asset_property_value_history,
    batch_put_asset_property_value,
    execute_query,
    get_asset_property_aggregates,
    get_asset_property_value,
    get_asset_property_value_history,
    get_interpolated_asset_property_values,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseData:
    """Test cases for SiteWise data ingestion and retrieval tools."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_put_asset_property_value_success(self, mock_boto_client):
        """Test successful batch data ingestion."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock the response
        mock_response = {'errorEntries': []}
        mock_client.batch_put_asset_property_value.return_value = mock_response

        # Test data
        entries = [
            {
                'entryId': 'entry1',
                'assetId': 'test-asset-123',
                'propertyId': 'test-property-456',
                'propertyValues': [
                    {
                        'value': {'doubleValue': 25.5},
                        'timestamp': {'timeInSeconds': 1640995200},
                        'quality': 'GOOD',
                    }
                ],
            }
        ]

        # Call the function
        result = batch_put_asset_property_value(entries=entries, region='us-east-1')

        # Verify the result
        assert result['success'] is True
        assert result['error_entries'] == []

        # Verify the client was called correctly
        mock_client.batch_put_asset_property_value.assert_called_once_with(entries=entries)

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_asset_property_value_success(self, mock_boto_client):
        """Test successful property value retrieval."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock the response
        mock_response = {
            'propertyValue': {
                'value': {'doubleValue': 25.5},
                'timestamp': {'timeInSeconds': 1640995200},
                'quality': 'GOOD',
            }
        }
        mock_client.get_asset_property_value.return_value = mock_response

        # Call the function
        result = get_asset_property_value(
            asset_id='test-asset-123',
            property_id='test-property-456',
            region='us-east-1',
        )

        # Verify the result
        assert result['success'] is True
        assert result['value']['doubleValue'] == 25.5
        assert result['quality'] == 'GOOD'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_asset_property_value_history_success(self, mock_boto_client):
        """Test successful property value history retrieval."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetPropertyValueHistory': [
                {
                    'value': {'doubleValue': 25.5},
                    'timestamp': {'timeInSeconds': 1640995200},
                },
                {
                    'value': {'doubleValue': 26.0},
                    'timestamp': {'timeInSeconds': 1640995260},
                },
            ],
            'nextToken': 'token-123',
        }
        mock_client.get_asset_property_value_history.return_value = mock_response

        result = get_asset_property_value_history(
            asset_id='test-asset-123',
            property_id='test-property-456',
            property_alias=None,
            start_date=None,
            end_date=None,
            qualities=None,
            time_ordering='ASCENDING',
            next_token=None,
            max_results=100,
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['asset_property_value_history']) == 2

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_asset_property_aggregates_success(self, mock_boto_client):
        """Test successful property aggregates retrieval."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'aggregatedValues': [
                {
                    'timestamp': {'timeInSeconds': 1640995200},
                    'value': {'average': 25.5},
                },
            ],
            'nextToken': 'token-123',
        }
        mock_client.get_asset_property_aggregates.return_value = mock_response

        result = get_asset_property_aggregates(
            asset_id='test-asset-123',
            property_id='test-property-456',
            property_alias=None,
            aggregate_types=None,
            resolution='1h',
            start_date=None,
            end_date=None,
            qualities=None,
            time_ordering='ASCENDING',
            next_token=None,
            max_results=100,
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['aggregated_values']) == 1

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_interpolated_asset_property_values_success(self, mock_boto_client):
        """Test successful interpolated values retrieval."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'interpolatedAssetPropertyValues': [
                {
                    'timestamp': {'timeInSeconds': 1640995200},
                    'value': {'doubleValue': 25.5},
                },
            ],
            'nextToken': 'token-123',
        }
        mock_client.get_interpolated_asset_property_values.return_value = mock_response

        result = get_interpolated_asset_property_values(
            asset_id='test-asset-123',
            property_id='test-property-456',
            start_time_in_seconds=1640995200,
            end_time_in_seconds=1640999000,
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['interpolated_asset_property_values']) == 1

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_get_asset_property_value_success(self, mock_boto_client):
        """Test successful batch get property values."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'successEntries': [
                {'entryId': 'entry1', 'propertyValue': {'value': {'doubleValue': 25.5}}}
            ],
            'skippedEntries': [],
            'errorEntries': [],
            'nextToken': 'token-123',
        }
        mock_client.batch_get_asset_property_value.return_value = mock_response

        entries = [{'entryId': 'entry1', 'assetId': 'asset-123', 'propertyId': 'prop-456'}]
        result = batch_get_asset_property_value(entries=entries, region='us-east-1')

        assert result['success'] is True
        assert len(result['success_entries']) == 1

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_get_asset_property_value_history_success(self, mock_boto_client):
        """Test successful batch get property value history."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'successEntries': [{'entryId': 'entry1', 'assetPropertyValueHistory': []}],
            'skippedEntries': [],
            'errorEntries': [],
        }
        mock_client.batch_get_asset_property_value_history.return_value = mock_response

        entries = [{'entryId': 'entry1', 'assetId': 'asset-123', 'propertyId': 'prop-456'}]
        result = batch_get_asset_property_value_history(entries=entries, region='us-east-1')

        assert result['success'] is True
        assert len(result['success_entries']) == 1

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_get_asset_property_aggregates_success(self, mock_boto_client):
        """Test successful batch get property aggregates."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'successEntries': [{'entryId': 'entry1', 'aggregatedValues': []}],
            'skippedEntries': [],
            'errorEntries': [],
        }
        mock_client.batch_get_asset_property_aggregates.return_value = mock_response

        entries = [{'entryId': 'entry1', 'assetId': 'asset-123', 'propertyId': 'prop-456'}]
        result = batch_get_asset_property_aggregates(entries=entries, region='us-east-1')

        assert result['success'] is True
        assert len(result['success_entries']) == 1

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_execute_query_success(self, mock_boto_client):
        """Test successful query execution."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'columns': [{'name': 'asset_id', 'type': {'scalarType': 'VARCHAR'}}],
            'rows': [{'data': [{'scalarValue': 'asset-123'}]}],
            'nextToken': 'token-123',
            'queryStatistics': {'queryExecutionTime': 100},
            'queryStatus': 'COMPLETED',
        }
        mock_client.execute_query.return_value = mock_response

        result = execute_query(
            query_statement='SELECT asset_id FROM asset',
            region='us-east-1',
            next_token=None,
            max_results=100,
        )

        assert result['success'] is True
        assert len(result['columns']) == 1
        assert len(result['rows']) == 1
        assert result['query_status'] == 'COMPLETED'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_execute_query_validation_errors(self, mock_boto_client):
        """Test validation errors in execute_query."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test empty query
        result = execute_query(query_statement='', region='us-east-1')
        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'

        # Test query too long
        result = execute_query(query_statement='a' * 70000, region='us-east-1')
        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_client_error_handling(self, mock_boto_client):
        """Test ClientError handling."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid query'}}
        mock_client.execute_query.side_effect = ClientError(error_response, 'ExecuteQuery')

        result = execute_query(
            query_statement='SELECT * FROM invalid_table',
            region='us-east-1',
            next_token=None,
            max_results=100,
        )

        assert result['success'] is False
        assert result['error_code'] == 'InvalidRequestException'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_asset_property_value_with_all_params(self, mock_boto_client):
        """Test get asset property value with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'propertyValue': {
                'value': {'doubleValue': 42.5},
                'timestamp': {'timeInSeconds': 1609459200, 'offsetInNanos': 0},
                'quality': 'GOOD',
            }
        }
        mock_client.get_asset_property_value.return_value = mock_response

        # Test with asset_id and property_id
        result = get_asset_property_value(
            asset_id='test-asset-123',
            property_id='test-prop-456',
            property_alias=None,
            region='us-west-2',
        )

        assert result['success'] is True
        mock_client.get_asset_property_value.assert_called_once_with(
            assetId='test-asset-123', propertyId='test-prop-456'
        )

        # Test with property_alias only
        mock_client.reset_mock()
        result = get_asset_property_value(
            asset_id=None,
            property_id=None,
            property_alias='/company/plant/temperature',
            region='us-east-1',
        )

        assert result['success'] is True
        mock_client.get_asset_property_value.assert_called_once_with(
            propertyAlias='/company/plant/temperature'
        )

        # Test with all parameters
        mock_client.reset_mock()
        result = get_asset_property_value(
            asset_id='test-asset-123',
            property_id='test-prop-456',
            property_alias='/company/plant/temperature',
            region='us-west-2',
        )

        assert result['success'] is True
        mock_client.get_asset_property_value.assert_called_once_with(
            assetId='test-asset-123',
            propertyId='test-prop-456',
            propertyAlias='/company/plant/temperature',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_asset_property_value_history_with_all_params(self, mock_boto_client):
        """Test get asset property value history with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetPropertyValueHistory': [
                {
                    'value': {'doubleValue': 42.5},
                    'timestamp': {'timeInSeconds': 1609459200, 'offsetInNanos': 0},
                    'quality': 'GOOD',
                }
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.get_asset_property_value_history.return_value = mock_response

        result = get_asset_property_value_history(
            asset_id='test-asset-123',
            property_id='test-prop-456',
            property_alias='/company/plant/temperature',
            start_date='2021-01-01T00:00:00Z',
            end_date='2021-01-02T00:00:00Z',
            qualities=['GOOD', 'BAD'],
            time_ordering='DESCENDING',
            next_token='prev-token',
            max_results=200,
            region='us-west-2',
        )

        assert result['success'] is True
        assert len(result['asset_property_value_history']) == 1
        assert result['next_token'] == 'next-token-123'

        # Verify datetime parsing and all parameters were passed
        call_args = mock_client.get_asset_property_value_history.call_args[1]
        assert call_args['assetId'] == 'test-asset-123'
        assert call_args['propertyId'] == 'test-prop-456'
        assert call_args['propertyAlias'] == '/company/plant/temperature'
        assert call_args['qualities'] == ['GOOD', 'BAD']
        assert call_args['timeOrdering'] == 'DESCENDING'
        assert call_args['nextToken'] == 'prev-token'
        assert call_args['maxResults'] == 200

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_asset_property_aggregates_with_all_params(self, mock_boto_client):
        """Test get asset property aggregates with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'aggregatedValues': [
                {
                    'timestamp': {'timeInSeconds': 1609459200, 'offsetInNanos': 0},
                    'quality': 'GOOD',
                    'value': {'average': 42.5, 'count': 10},
                }
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.get_asset_property_aggregates.return_value = mock_response

        # Test with custom aggregate types
        result = get_asset_property_aggregates(
            asset_id='test-asset-123',
            property_id='test-prop-456',
            property_alias='/company/plant/temperature',
            aggregate_types=['AVERAGE', 'MAXIMUM', 'MINIMUM'],
            resolution='15m',
            start_date='2021-01-01T00:00:00Z',
            end_date='2021-01-02T00:00:00Z',
            qualities=['GOOD'],
            time_ordering='DESCENDING',
            next_token='prev-token',
            max_results=500,
            region='us-west-2',
        )

        assert result['success'] is True
        assert len(result['aggregated_values']) == 1

        # Test with default aggregate types (None)
        mock_client.reset_mock()
        result = get_asset_property_aggregates(
            asset_id='test-asset-123',
            property_id='test-prop-456',
            property_alias=None,
            aggregate_types=None,  # Should default to ["AVERAGE"]
            resolution='1h',
            start_date=None,
            end_date=None,
            qualities=None,
            time_ordering='ASCENDING',
            next_token=None,
            max_results=100,
            region='us-east-1',
        )

        assert result['success'] is True
        call_args = mock_client.get_asset_property_aggregates.call_args[1]
        assert call_args['aggregateTypes'] == ['AVERAGE']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_get_interpolated_asset_property_values_with_all_params(self, mock_boto_client):
        """Test get interpolated asset property values with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'interpolatedAssetPropertyValues': [
                {
                    'timestamp': {'timeInSeconds': 1609459200, 'offsetInNanos': 0},
                    'value': {'doubleValue': 42.5},
                }
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.get_interpolated_asset_property_values.return_value = mock_response

        result = get_interpolated_asset_property_values(
            asset_id='test-asset-123',
            property_id='test-prop-456',
            property_alias='/company/plant/temperature',
            start_time_in_seconds=1609459200,
            end_time_in_seconds=1609545600,
            quality='GOOD',
            interval_in_seconds=1800,
            next_token='prev-token',
            max_results=250,
            interpolation_type='LOCF_INTERPOLATION',
            interval_window_in_seconds=900,
            region='us-west-2',
        )

        assert result['success'] is True
        assert len(result['interpolated_asset_property_values']) == 1

        # Verify all parameters were passed correctly
        call_args = mock_client.get_interpolated_asset_property_values.call_args[1]
        assert call_args['assetId'] == 'test-asset-123'
        assert call_args['propertyId'] == 'test-prop-456'
        assert call_args['propertyAlias'] == '/company/plant/temperature'
        assert call_args['startTimeInSeconds'] == 1609459200
        assert call_args['endTimeInSeconds'] == 1609545600
        assert call_args['quality'] == 'GOOD'
        assert call_args['intervalInSeconds'] == 1800
        assert call_args['nextToken'] == 'prev-token'
        assert call_args['maxResults'] == 250
        assert call_args['type'] == 'LOCF_INTERPOLATION'
        assert call_args['intervalWindowInSeconds'] == 900

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_get_asset_property_value_with_next_token(self, mock_boto_client):
        """Test batch get asset property value with next token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'successEntries': [{'entryId': 'entry1'}],
            'skippedEntries': [],
            'errorEntries': [],
            'nextToken': 'next-token-123',
        }
        mock_client.batch_get_asset_property_value.return_value = mock_response

        entries = [{'entryId': 'entry1', 'assetId': 'asset-123', 'propertyId': 'prop-456'}]

        # Test with next_token
        result = batch_get_asset_property_value(
            entries=entries, next_token='prev-token', region='us-west-2'
        )

        assert result['success'] is True
        mock_client.batch_get_asset_property_value.assert_called_once_with(
            entries=entries, nextToken='prev-token'
        )

        # Test without next_token
        mock_client.reset_mock()
        result = batch_get_asset_property_value(
            entries=entries,
            next_token=None,
            region='us-east-1',
        )

        assert result['success'] is True
        mock_client.batch_get_asset_property_value.assert_called_once_with(entries=entries)

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_get_asset_property_value_history_with_next_token(self, mock_boto_client):
        """Test batch get asset property value history with next token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'successEntries': [{'entryId': 'entry1'}],
            'skippedEntries': [],
            'errorEntries': [],
            'nextToken': 'next-token-123',
        }
        mock_client.batch_get_asset_property_value_history.return_value = mock_response

        entries = [{'entryId': 'entry1', 'assetId': 'asset-123', 'propertyId': 'prop-456'}]

        # Test with next_token
        result = batch_get_asset_property_value_history(
            entries=entries,
            next_token='prev-token',
            max_results=500,
            region='us-west-2',
        )

        assert result['success'] is True
        mock_client.batch_get_asset_property_value_history.assert_called_once_with(
            entries=entries, maxResults=500, nextToken='prev-token'
        )

        # Test without next_token
        mock_client.reset_mock()
        result = batch_get_asset_property_value_history(
            entries=entries,
            next_token=None,
            max_results=200,
            region='us-east-1',
        )

        assert result['success'] is True
        mock_client.batch_get_asset_property_value_history.assert_called_once_with(
            entries=entries, maxResults=200
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_batch_get_asset_property_aggregates_with_next_token(self, mock_boto_client):
        """Test batch get asset property aggregates with next token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'successEntries': [{'entryId': 'entry1'}],
            'skippedEntries': [],
            'errorEntries': [],
            'nextToken': 'next-token-123',
        }
        mock_client.batch_get_asset_property_aggregates.return_value = mock_response

        entries = [{'entryId': 'entry1', 'assetId': 'asset-123', 'propertyId': 'prop-456'}]

        # Test with next_token
        result = batch_get_asset_property_aggregates(
            entries=entries,
            next_token='prev-token',
            max_results=750,
            region='us-west-2',
        )

        assert result['success'] is True
        mock_client.batch_get_asset_property_aggregates.assert_called_once_with(
            entries=entries, maxResults=750, nextToken='prev-token'
        )

        # Test without next_token
        mock_client.reset_mock()
        result = batch_get_asset_property_aggregates(
            entries=entries,
            next_token=None,
            max_results=300,
            region='us-east-1',
        )

        assert result['success'] is True
        mock_client.batch_get_asset_property_aggregates.assert_called_once_with(
            entries=entries, maxResults=300
        )

    def test_execute_query_additional_validation_errors(self):
        """Test execute query validation error cases."""
        # Test empty query
        result = execute_query(
            query_statement='',
            region='us-east-1',
            next_token=None,
            max_results=100,
        )
        assert result['success'] is False
        assert 'Query statement cannot be empty' in result['error']

        # Test whitespace-only query
        result = execute_query(
            query_statement='   ',
            region='us-east-1',
            next_token=None,
            max_results=100,
        )
        assert result['success'] is False
        assert 'Query statement cannot be empty' in result['error']

        # Test query too long (over 64KB)
        long_query = "SELECT * FROM asset WHERE asset_name = '" + 'x' * 65537 + "'"
        result = execute_query(
            query_statement=long_query,
            region='us-east-1',
            next_token=None,
            max_results=100,
        )
        assert result['success'] is False
        assert 'Query statement cannot exceed 64KB' in result['error']

        # Test next token too long
        result = execute_query(
            query_statement='SELECT asset_id FROM asset',
            region='us-east-1',
            next_token='x' * 4097,  # Exceeds 4096 character limit
            max_results=100,
        )
        assert result['success'] is False
        assert 'Next token too long' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_execute_query_with_all_params(self, mock_boto_client):
        """Test execute query with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'columns': [{'name': 'asset_id', 'type': {'scalarType': 'VARCHAR'}}],
            'rows': [{'data': [{'scalarValue': 'asset-123'}]}],
            'nextToken': 'next-token-123',
            'queryStatistics': {'scannedRows': 100, 'executionTimeInMillis': 250},
            'queryStatus': 'COMPLETED',
        }
        mock_client.execute_query.return_value = mock_response

        query = "SELECT asset_id, asset_name FROM asset WHERE asset_name LIKE 'Test%'"
        result = execute_query(
            query_statement=query,
            region='us-west-2',
            next_token='prev-token',
            max_results=2000,
        )

        assert result['success'] is True
        assert len(result['columns']) == 1
        assert len(result['rows']) == 1
        assert result['next_token'] == 'next-token-123'
        assert result['query_statistics']['scannedRows'] == 100
        assert result['query_status'] == 'COMPLETED'

        mock_client.execute_query.assert_called_once_with(
            queryStatement=query, maxResults=2000, nextToken='prev-token'
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_execute_query_without_optional_params(self, mock_boto_client):
        """Test execute query without optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'columns': [],
            'rows': [],
            'queryStatistics': {},
            'queryStatus': 'COMPLETED',
        }
        mock_client.execute_query.return_value = mock_response

        query = 'SELECT COUNT(*) FROM asset'
        result = execute_query(
            query_statement=query,
            region='us-east-1',
            next_token=None,
            max_results=100,
        )

        assert result['success'] is True

        # Verify only required parameters were passed
        mock_client.execute_query.assert_called_once_with(queryStatement=query, maxResults=100)

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_all_functions_client_error_handling(self, mock_boto_client):
        """Test that all functions handle ClientError exceptions properly."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InternalFailureException',
                'Message': 'Internal server error',
            }
        }

        # Test batch_put_asset_property_value error handling
        mock_client.batch_put_asset_property_value.side_effect = ClientError(
            error_response, 'BatchPutAssetPropertyValue'
        )
        result = batch_put_asset_property_value(entries=[{'entryId': 'test'}])
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test get_asset_property_value error handling
        mock_client.get_asset_property_value.side_effect = ClientError(
            error_response, 'GetAssetPropertyValue'
        )
        result = get_asset_property_value(
            asset_id='test-123',
            property_id=None,
            property_alias=None,
            region='us-east-1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test get_asset_property_value_history error handling
        mock_client.get_asset_property_value_history.side_effect = ClientError(
            error_response, 'GetAssetPropertyValueHistory'
        )
        result = get_asset_property_value_history(
            asset_id='test-123',
            property_id=None,
            property_alias=None,
            start_date=None,
            end_date=None,
            qualities=None,
            time_ordering='ASCENDING',
            next_token=None,
            max_results=100,
            region='us-east-1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test get_asset_property_aggregates error handling
        mock_client.get_asset_property_aggregates.side_effect = ClientError(
            error_response, 'GetAssetPropertyAggregates'
        )
        result = get_asset_property_aggregates(
            asset_id='test-123',
            property_id=None,
            property_alias=None,
            aggregate_types=None,
            resolution='1h',
            start_date=None,
            end_date=None,
            qualities=None,
            time_ordering='ASCENDING',
            next_token=None,
            max_results=100,
            region='us-east-1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test get_interpolated_asset_property_values error handling
        mock_client.get_interpolated_asset_property_values.side_effect = ClientError(
            error_response, 'GetInterpolatedAssetPropertyValues'
        )
        result = get_interpolated_asset_property_values(
            asset_id='test-123',
            start_time_in_seconds=1609459200,
            end_time_in_seconds=1609545600,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test batch_get_asset_property_value error handling
        mock_client.batch_get_asset_property_value.side_effect = ClientError(
            error_response, 'BatchGetAssetPropertyValue'
        )
        result = batch_get_asset_property_value(
            entries=[{'entryId': 'test'}],
            next_token=None,
            region='us-east-1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test batch_get_asset_property_value_history error handling
        mock_client.batch_get_asset_property_value_history.side_effect = ClientError(
            error_response, 'BatchGetAssetPropertyValueHistory'
        )
        result = batch_get_asset_property_value_history(
            entries=[{'entryId': 'test'}],
            next_token=None,
            max_results=100,
            region='us-east-1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test batch_get_asset_property_aggregates error handling
        mock_client.batch_get_asset_property_aggregates.side_effect = ClientError(
            error_response, 'BatchGetAssetPropertyAggregates'
        )
        result = batch_get_asset_property_aggregates(
            entries=[{'entryId': 'test'}],
            next_token=None,
            max_results=100,
            region='us-east-1',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test execute_query error handling
        mock_client.execute_query.side_effect = ClientError(error_response, 'ExecuteQuery')
        result = execute_query(
            query_statement='SELECT asset_id FROM asset',
            region='us-east-1',
            next_token=None,
            max_results=100,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'


if __name__ == '__main__':
    pytest.main([__file__])
