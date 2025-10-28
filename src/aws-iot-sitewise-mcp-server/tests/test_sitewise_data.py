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
    create_buffered_ingestion_job,
    create_bulk_import_iam_role,
    create_bulk_import_job,
    describe_bulk_import_job,
    execute_query,
    get_asset_property_aggregates,
    get_asset_property_value,
    get_asset_property_value_history,
    get_interpolated_asset_property_values,
    list_bulk_import_jobs,
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

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_iam_client')
    def test_create_bulk_import_iam_role_success(self, mock_create_iam_client):
        """Test successful IAM role creation for bulk import."""
        mock_iam_client = Mock()
        mock_create_iam_client.return_value = mock_iam_client

        mock_iam_client.create_role.return_value = {
            'Role': {'Arn': 'arn:aws:iam::123456789012:role/TestRole'}
        }

        result = create_bulk_import_iam_role(
            role_name='TestRole',
            data_bucket_names=['test-data-bucket'],
            error_bucket_name='test-error-bucket',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['role_arn'] == 'arn:aws:iam::123456789012:role/TestRole'
        assert result['role_name'] == 'TestRole'
        mock_iam_client.create_role.assert_called_once()
        mock_iam_client.put_role_policy.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_iam_client')
    def test_create_bulk_import_iam_role_error(self, mock_create_iam_client):
        """Test IAM role creation error handling."""
        mock_iam_client = Mock()
        mock_create_iam_client.return_value = mock_iam_client

        error_response = {
            'Error': {'Code': 'EntityAlreadyExistsException', 'Message': 'Role already exists'}
        }
        mock_iam_client.create_role.side_effect = ClientError(error_response, 'CreateRole')

        result = create_bulk_import_iam_role(
            role_name='ExistingRole',
            data_bucket_names=['test-bucket'],
            error_bucket_name='error-bucket',
        )

        assert result['success'] is False
        assert 'error' in result

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_create_bulk_import_job_success(self, mock_boto_client):
        """Test successful bulk import job creation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.create_bulk_import_job.return_value = {
            'jobId': 'test-job-id',
            'jobName': 'test-job',
            'jobStatus': 'PENDING',
        }

        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'VALUE', 'DATA_TYPE', 'TIMESTAMP_SECONDS']}
                }
            },
            adaptive_ingestion=True,
        )

        assert result['success'] is True
        assert result['job_id'] == 'test-job-id'
        assert result['job_name'] == 'test-job'
        mock_client.create_bulk_import_job.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_create_buffered_ingestion_job_success(self, mock_boto_client):
        """Test successful buffered ingestion job creation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.create_bulk_import_job.return_value = {
            'jobId': 'buffered-job-id',
            'jobName': 'buffered-job',
            'jobStatus': 'PENDING',
        }

        result = create_buffered_ingestion_job(
            job_name='buffered-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'VALUE', 'DATA_TYPE', 'TIMESTAMP_SECONDS']}
                }
            },
        )

        assert result['success'] is True
        assert result['job_id'] == 'buffered-job-id'
        mock_client.create_bulk_import_job.assert_called_once()
        # Verify adaptive_ingestion was set to True
        call_args = mock_client.create_bulk_import_job.call_args[1]
        assert call_args['adaptiveIngestion'] is True

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_describe_bulk_import_job_success(self, mock_boto_client):
        """Test successful bulk import job description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.describe_bulk_import_job.return_value = {
            'jobId': '12345678-1234-1234-1234-123456789012',
            'jobName': 'test-job',
            'jobStatus': 'COMPLETED',
            'jobRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
        }

        result = describe_bulk_import_job(job_id='12345678-1234-1234-1234-123456789012')

        assert result['success'] is True
        assert result['job_id'] == '12345678-1234-1234-1234-123456789012'
        assert result['job_status'] == 'COMPLETED'
        mock_client.describe_bulk_import_job.assert_called_once_with(
            jobId='12345678-1234-1234-1234-123456789012'
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_list_bulk_import_jobs_success(self, mock_boto_client):
        """Test successful bulk import jobs listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.list_bulk_import_jobs.return_value = {
            'jobSummaries': [
                {'jobId': 'job1', 'jobName': 'test-job-1', 'jobStatus': 'COMPLETED'},
                {'jobId': 'job2', 'jobName': 'test-job-2', 'jobStatus': 'PENDING'},
            ]
        }

        result = list_bulk_import_jobs()

        assert result['success'] is True
        assert len(result['job_summaries']) == 2
        assert result['job_summaries'][0]['jobId'] == 'job1'
        mock_client.list_bulk_import_jobs.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_bulk_import_job_error_handling(self, mock_boto_client):
        """Test bulk import job error handling."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid job name'}}
        mock_client.create_bulk_import_job.side_effect = ClientError(
            error_response, 'CreateBulkImportJob'
        )

        result = create_bulk_import_job(
            job_name='',  # Invalid empty name
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'csv': {'columnNames': ['ALIAS', 'VALUE']}}},
            adaptive_ingestion=True,
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'

    def test_bulk_import_csv_validation_missing_column_names(self):
        """Test CSV validation fails when columnNames is missing."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'csv': {}}},
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV configuration must have "columnNames" field' in result['error']

    def test_bulk_import_csv_validation_empty_column_names(self):
        """Test CSV validation fails when columnNames is empty."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'csv': {'columnNames': []}}},
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV columnNames must be a non-empty list' in result['error']

    def test_bulk_import_csv_validation_invalid_column_name(self):
        """Test CSV validation fails with invalid column name."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'csv': {'columnNames': ['INVALID_COLUMN']}}},
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Invalid column name: INVALID_COLUMN' in result['error']

    def test_bulk_import_csv_validation_all_three_identifiers(self):
        """Test CSV validation fails when ASSET_ID, PROPERTY_ID, and ALIAS are all present."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {
                        'columnNames': [
                            'ASSET_ID',
                            'PROPERTY_ID',
                            'ALIAS',
                            'TIMESTAMP_SECONDS',
                            'VALUE',
                            'DATA_TYPE',
                        ]
                    }
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV cannot include ASSET_ID, PROPERTY_ID, and ALIAS together' in result['error']

    def test_bulk_import_csv_validation_asset_id_without_property_id(self):
        """Test CSV validation fails when ASSET_ID is present without PROPERTY_ID."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ASSET_ID', 'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']}
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV with ASSET_ID must also include PROPERTY_ID' in result['error']

    def test_bulk_import_csv_validation_property_id_without_asset_id(self):
        """Test CSV validation fails when PROPERTY_ID is present without ASSET_ID."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {
                        'columnNames': ['PROPERTY_ID', 'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']
                    }
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV with PROPERTY_ID must also include ASSET_ID' in result['error']

    def test_bulk_import_csv_validation_no_identifier_columns(self):
        """Test CSV validation fails when no identifier columns are present."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV must include either ALIAS or both ASSET_ID and PROPERTY_ID' in result['error']

    def test_bulk_import_csv_validation_missing_required_columns(self):
        """Test CSV validation fails when required columns are missing."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'CSV missing required columns' in result['error']

    def test_bulk_import_invalid_file_format(self):
        """Test validation fails when neither CSV nor Parquet is specified."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.txt'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'invalid': {}}},
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'File format must specify either "csv" or "parquet"' in result['error']

    def test_bulk_import_missing_file_format(self):
        """Test validation fails when fileFormat is missing."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={},
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Job configuration must have "fileFormat" field' in result['error']

    def test_bulk_import_invalid_file_format_type(self):
        """Test validation fails when fileFormat is not a dictionary."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': 'invalid'},
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'File format must be a dictionary' in result['error']

    def test_describe_bulk_import_job_empty_job_id(self):
        """Test validation fails with empty job ID."""
        result = describe_bulk_import_job(job_id='')
        assert result['success'] is False
        assert 'Job ID must be a non-empty string' in result['error']

    def test_describe_bulk_import_job_invalid_uuid_length(self):
        """Test validation fails with incorrect UUID length."""
        result = describe_bulk_import_job(job_id='12345678-1234-1234-1234-12345678901')  # 35 chars
        assert result['success'] is False
        assert 'Job ID must be in UUID format' in result['error']

    def test_describe_bulk_import_job_invalid_uuid_hyphens(self):
        """Test validation fails with incorrect number of hyphens."""
        result = describe_bulk_import_job(
            job_id='123456781234123412341234567890123456'
        )  # 36 chars, no hyphens
        assert result['success'] is False
        assert 'Job ID must be in UUID format' in result['error']

    def test_describe_bulk_import_job_invalid_uuid_format(self):
        """Test validation fails with wrong hyphen positions."""
        result = describe_bulk_import_job(
            job_id='1234567-8123-1234-1234-567890123456',  # 37 chars - too long
            region='us-east-1',
        )
        assert result['success'] is False
        assert 'Job ID must be in UUID format' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_bulk_import_csv_validation_valid_asset_property_combo(self, mock_boto_client):
        """Test CSV validation passes with valid ASSET_ID + PROPERTY_ID combination."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.describe_storage_configuration.return_value = {
            'storageType': 'SITEWISE_DEFAULT_STORAGE',
            'warmTier': {'state': 'ENABLED'},
        }
        mock_client.create_bulk_import_job.return_value = {
            'jobId': 'test-job-id',
            'jobName': 'test-job',
            'jobStatus': 'PENDING',
        }

        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {
                        'columnNames': [
                            'ASSET_ID',
                            'PROPERTY_ID',
                            'TIMESTAMP_SECONDS',
                            'VALUE',
                            'DATA_TYPE',
                        ]
                    }
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is True

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_bulk_import_parquet_validation_valid(self, mock_boto_client):
        """Test Parquet validation passes with valid configuration."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.describe_storage_configuration.return_value = {
            'storageType': 'SITEWISE_DEFAULT_STORAGE',
            'warmTier': {'state': 'ENABLED'},
        }
        mock_client.create_bulk_import_job.return_value = {
            'jobId': 'test-job-id',
            'jobName': 'test-job',
            'jobStatus': 'PENDING',
        }

        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.parquet'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'parquet': {}}},
            adaptive_ingestion=True,
        )
        assert result['success'] is True

    def test_buffered_ingestion_job_inherits_csv_validation(self):
        """Test that buffered ingestion job inherits CSV validation from bulk import."""
        result = create_buffered_ingestion_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={'fileFormat': {'csv': {'columnNames': ['INVALID_COLUMN']}}},
        )
        assert result['success'] is False
        assert 'Invalid column name: INVALID_COLUMN' in result['error']

    def test_create_bulk_import_job_adaptive_ingestion_not_boolean(self):
        """Test validation fails when adaptive_ingestion is not boolean."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']}
                }
            },
            adaptive_ingestion='not_boolean',  # Invalid type
            region='us-east-1',
        )
        assert result['success'] is False
        assert 'Please provide a boolean value for adaptive_ingestion' in result['error']

    def test_create_bulk_import_job_control_characters_in_name(self):
        """Test validation fails with control characters in job name."""
        result = create_bulk_import_job(
            job_name='test\x00job',  # Contains null character
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']}
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Job name cannot contain control characters' in result['error']

    def test_create_bulk_import_job_missing_job_role_arn(self):
        """Test validation fails with missing job role ARN."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='',  # Empty ARN
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Job role ARN is required' in result['error']

    def test_create_bulk_import_job_invalid_arn_format(self):
        """Test validation fails with invalid ARN format."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='invalid-arn-format',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Job role ARN must be a valid AWS ARN' in result['error']

    def test_create_bulk_import_job_arn_too_long(self):
        """Test validation fails with ARN too long."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/' + 'a' * 1600,  # Too long
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Job role ARN must be between 1 and 1600 characters' in result['error']

    def test_create_bulk_import_job_files_not_list(self):
        """Test validation fails when files is not a list."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files='not-a-list',  # Invalid type
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Files must be a non-empty list' in result['error']

    def test_create_bulk_import_job_file_not_dict(self):
        """Test validation fails when file is not a dictionary."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=['not-a-dict'],  # Invalid type
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Each file must be a dictionary' in result['error']

    def test_create_bulk_import_job_file_missing_bucket_key(self):
        """Test validation fails when file missing bucket or key."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket'}],  # Missing key
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Each file must have "bucket" and "key" fields' in result['error']

    def test_create_bulk_import_job_bucket_name_too_short(self):
        """Test validation fails with bucket name too short."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'ab', 'key': 'test.csv'}],  # Too short
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'S3 bucket name must be between 3 and 63 characters' in result['error']

    def test_create_bulk_import_job_error_location_not_dict(self):
        """Test validation fails when error report location is not dict."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location='not-a-dict',  # Invalid type
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Error report location must be a dictionary' in result['error']

    def test_create_bulk_import_job_error_location_missing_fields(self):
        """Test validation fails when error location missing fields."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket'},  # Missing prefix
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Error report location must have "bucket" and "prefix" fields' in result['error']

    def test_create_bulk_import_job_error_prefix_no_slash(self):
        """Test validation fails when error prefix doesn't end with slash."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={
                'bucket': 'error-bucket',
                'prefix': 'errors',
            },  # No trailing slash
            job_configuration={
                'fileFormat': {'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE']}}
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Error report prefix must end with a forward slash (/)' in result['error']

    def test_create_bulk_import_job_config_not_dict(self):
        """Test validation fails when job configuration is not dict."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration='not-a-dict',  # Invalid type
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Job configuration must be a dictionary' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_create_bulk_import_job_client_error(self, mock_create_client):
        """Test handling of AWS client errors."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_client.describe_storage_configuration.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'DescribeStorageConfiguration',
        )

        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'error-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']}
                }
            },
            adaptive_ingestion=False,  # This will trigger storage config check
            region='us-east-1',
        )
        assert result['success'] is False
        assert 'Failed to validate storage configuration' in result['error']

    def test_create_bulk_import_job_error_bucket_too_short(self):
        """Test create_bulk_import_job with error bucket name too short."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'ab', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE', 'QUALITY']}
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Error report bucket name must be between 3 and 63 characters' in result['error']

    def test_create_bulk_import_job_prefix_no_slash(self):
        """Test create_bulk_import_job with prefix not ending in slash."""
        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'test-bucket', 'prefix': 'errors'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE', 'QUALITY']}
                }
            },
            adaptive_ingestion=True,
        )
        assert result['success'] is False
        assert 'Error report prefix must end with a forward slash' in result['error']

    def test_list_bulk_import_jobs_invalid_filter(self):
        """Test list_bulk_import_jobs with invalid filter."""
        result = list_bulk_import_jobs(filter='INVALID')
        assert result['success'] is False
        assert 'Invalid filter: INVALID' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_list_bulk_import_jobs_client_error(self, mock_client):
        """Test list_bulk_import_jobs with AWS client error."""
        mock_sitewise = Mock()
        mock_client.return_value = mock_sitewise
        mock_sitewise.list_bulk_import_jobs.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListBulkImportJobs'
        )

        result = list_bulk_import_jobs()

        assert result['success'] is False
        assert result['error_code'] == 'AccessDenied'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.validation.check_storage_configuration_requirements'
    )
    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_create_bulk_import_job_aws_error(self, mock_client, mock_storage):
        """Test create_bulk_import_job AWS ClientError handling."""
        mock_storage.return_value = None
        mock_sitewise = Mock()
        mock_client.return_value = mock_sitewise
        mock_sitewise.create_bulk_import_job.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'CreateBulkImportJob'
        )

        result = create_bulk_import_job(
            job_name='test-job',
            job_role_arn='arn:aws:iam::123456789012:role/TestRole',
            files=[{'bucket': 'test-bucket', 'key': 'test.csv'}],
            error_report_location={'bucket': 'test-bucket', 'prefix': 'errors/'},
            job_configuration={
                'fileFormat': {
                    'csv': {'columnNames': ['ALIAS', 'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE']}
                }
            },
            adaptive_ingestion=True,
        )

        assert result['success'] is False
        assert result['error_code'] == 'AccessDenied'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_list_bulk_import_jobs_aws_error(self, mock_client):
        """Test list_bulk_import_jobs AWS ClientError handling."""
        mock_sitewise = Mock()
        mock_client.return_value = mock_sitewise
        mock_sitewise.list_bulk_import_jobs.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListBulkImportJobs',
        )

        result = list_bulk_import_jobs()

        assert result['success'] is False
        assert result['error_code'] == 'ThrottlingException'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_describe_bulk_import_job_aws_error(self, mock_client):
        """Test describe_bulk_import_job AWS ClientError handling."""
        mock_sitewise = Mock()
        mock_client.return_value = mock_sitewise
        mock_sitewise.describe_bulk_import_job.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFound', 'Message': 'Job not found'}},
            'DescribeBulkImportJob',
        )

        result = describe_bulk_import_job(job_id='12345678-1234-1234-1234-123456789012')

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFound'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_list_bulk_import_jobs_region_validation_workflow(self, mock_client):
        """Test list_bulk_import_jobs region validation in workflow."""
        result = list_bulk_import_jobs(
            filter='ALL', next_token=None, max_results=50, region='invalid_region!'
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'Invalid AWS region format' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data.create_sitewise_client')
    def test_list_bulk_import_jobs_max_results_validation_workflow(self, mock_client):
        """Test list_bulk_import_jobs max_results validation in workflow."""
        result = list_bulk_import_jobs(
            filter='ALL', next_token=None, max_results=0, region='us-east-1'
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'Max results must be at least 1' in result['error']


if __name__ == '__main__':
    pytest.main([__file__])
