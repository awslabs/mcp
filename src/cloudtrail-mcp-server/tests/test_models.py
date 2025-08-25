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

"""Tests for CloudTrail MCP server models."""

import pytest
from awslabs.cloudtrail_mcp_server.models import (
    EventDataStore,
    QueryResult,
    QueryStatus,
)
from datetime import datetime, timezone


class TestEventDataStore:
    """Test EventDataStore model."""

    def test_event_data_store_with_pascal_case_fields(self):
        """Test EventDataStore with AWS API PascalCase field names."""
        data = {
            'EventDataStoreArn': 'arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/test-eds',
            'Name': 'TestEventDataStore',
            'Status': 'ENABLED',
            'MultiRegionEnabled': True,
            'OrganizationEnabled': False,
            'RetentionPeriod': 90,
            'TerminationProtectionEnabled': True,
            'CreatedTimestamp': datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'UpdatedTimestamp': datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            'KmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/test-key',
            'BillingMode': 'EXTENDABLE_RETENTION_PRICING',
        }

        eds = EventDataStore.model_validate(data)

        assert eds.event_data_store_arn == data['EventDataStoreArn']
        assert eds.name == data['Name']
        assert eds.status == data['Status']
        assert eds.multi_region_enabled == data['MultiRegionEnabled']
        assert eds.organization_enabled == data['OrganizationEnabled']
        assert eds.retention_period == data['RetentionPeriod']
        assert eds.termination_protection_enabled == data['TerminationProtectionEnabled']
        assert eds.created_timestamp == data['CreatedTimestamp']
        assert eds.updated_timestamp == data['UpdatedTimestamp']
        assert eds.kms_key_id == data['KmsKeyId']
        assert eds.billing_mode == data['BillingMode']

    def test_event_data_store_with_snake_case_fields(self):
        """Test EventDataStore with snake_case field names."""
        data = {
            'event_data_store_arn': 'arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/test-eds',
            'name': 'TestEventDataStore',
            'status': 'ENABLED',
            'multi_region_enabled': True,
            'organization_enabled': False,
            'retention_period': 90,
            'termination_protection_enabled': True,
            'created_timestamp': datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'updated_timestamp': datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            'kms_key_id': 'arn:aws:kms:us-east-1:123456789012:key/test-key',
            'billing_mode': 'EXTENDABLE_RETENTION_PRICING',
        }

        eds = EventDataStore.model_validate(data)

        assert eds.event_data_store_arn == data['event_data_store_arn']
        assert eds.name == data['name']
        assert eds.status == data['status']
        assert eds.multi_region_enabled == data['multi_region_enabled']
        assert eds.organization_enabled == data['organization_enabled']
        assert eds.retention_period == data['retention_period']
        assert eds.termination_protection_enabled == data['termination_protection_enabled']
        assert eds.created_timestamp == data['created_timestamp']
        assert eds.updated_timestamp == data['updated_timestamp']
        assert eds.kms_key_id == data['kms_key_id']
        assert eds.billing_mode == data['billing_mode']

    def test_event_data_store_with_minimal_fields(self):
        """Test EventDataStore with minimal required fields."""
        data = {}

        eds = EventDataStore.model_validate(data)

        # All fields should be None/optional
        assert eds.event_data_store_arn is None
        assert eds.name is None
        assert eds.status is None
        assert eds.multi_region_enabled is None
        assert eds.organization_enabled is None
        assert eds.retention_period is None
        assert eds.termination_protection_enabled is None
        assert eds.created_timestamp is None
        assert eds.updated_timestamp is None
        assert eds.kms_key_id is None
        assert eds.billing_mode is None
        assert eds.advanced_event_selectors is None

    def test_event_data_store_with_advanced_event_selectors(self):
        """Test EventDataStore with advanced event selectors."""
        data = {
            'Name': 'TestEDS',
            'AdvancedEventSelectors': [
                {
                    'Name': 'Log all management events',
                    'FieldSelectors': [{'Field': 'eventCategory', 'Equals': ['Management']}],
                },
                {
                    'Name': 'Log specific S3 events',
                    'FieldSelectors': [
                        {'Field': 'eventCategory', 'Equals': ['Data']},
                        {'Field': 'resources.type', 'Equals': ['AWS::S3::Object']},
                    ],
                },
            ],
        }

        eds = EventDataStore.model_validate(data)

        assert eds.name == 'TestEDS'
        assert eds.advanced_event_selectors is not None
        assert len(eds.advanced_event_selectors) == 2
        assert eds.advanced_event_selectors[0]['Name'] == 'Log all management events'
        assert eds.advanced_event_selectors[1]['Name'] == 'Log specific S3 events'

    def test_event_data_store_json_serialization(self):
        """Test EventDataStore JSON serialization with datetime fields."""
        data = {
            'Name': 'TestEDS',
            'CreatedTimestamp': datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'UpdatedTimestamp': datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        }

        eds = EventDataStore.model_validate(data)
        json_data = eds.model_dump(mode='json')

        assert json_data['name'] == 'TestEDS'
        assert '2023-01-01T12:00:00+00:00' in json_data['created_timestamp']
        assert '2023-01-15T12:00:00+00:00' in json_data['updated_timestamp']


class TestQueryResult:
    """Test QueryResult model."""

    def test_query_result_basic(self):
        """Test basic QueryResult creation."""
        result = QueryResult(query_id='test-query-123', query_status='FINISHED')

        assert result.query_id == 'test-query-123'
        assert result.query_status == 'FINISHED'
        assert result.query_statistics is None
        assert result.query_result_rows is None
        assert result.next_token is None
        assert result.error_message is None

    def test_query_result_with_statistics(self):
        """Test QueryResult with query statistics."""
        statistics = {
            'ResultsCount': 100,
            'TotalBytesScanned': 2048000,
            'BytesScanned': 1024000,
            'ExecutionTimeInMillis': 5000,
        }

        result = QueryResult(
            query_id='stats-query-456', query_status='FINISHED', query_statistics=statistics
        )

        assert result.query_id == 'stats-query-456'
        assert result.query_status == 'FINISHED'
        assert result.query_statistics == statistics
        assert result.query_statistics is not None
        assert result.query_statistics['ResultsCount'] == 100
        assert result.query_statistics['ExecutionTimeInMillis'] == 5000

    def test_query_result_with_rows(self):
        """Test QueryResult with result rows."""
        result_rows = [
            [{'VarCharValue': 'ConsoleLogin'}, {'VarCharValue': '10'}],
            [{'VarCharValue': 'CreateUser'}, {'VarCharValue': '5'}],
            [{'VarCharValue': 'DeleteUser'}, {'VarCharValue': '2'}],
        ]

        result = QueryResult(
            query_id='rows-query-789', query_status='FINISHED', query_result_rows=result_rows
        )

        assert result.query_id == 'rows-query-789'
        assert result.query_status == 'FINISHED'
        assert result.query_result_rows is not None
        assert len(result.query_result_rows) == 3
        assert result.query_result_rows[0][0]['VarCharValue'] == 'ConsoleLogin'
        assert result.query_result_rows[2][1]['VarCharValue'] == '2'

    def test_query_result_with_pagination(self):
        """Test QueryResult with pagination token."""
        result = QueryResult(
            query_id='paginated-query', query_status='FINISHED', next_token='next-page-token-123'
        )

        assert result.query_id == 'paginated-query'
        assert result.query_status == 'FINISHED'
        assert result.next_token == 'next-page-token-123'

    def test_query_result_with_error(self):
        """Test QueryResult with error message."""
        result = QueryResult(
            query_id='failed-query',
            query_status='FAILED',
            error_message='SQL syntax error: unexpected token',
        )

        assert result.query_id == 'failed-query'
        assert result.query_status == 'FAILED'
        assert result.error_message == 'SQL syntax error: unexpected token'

    def test_query_result_complete_example(self):
        """Test QueryResult with all fields populated."""
        statistics = {
            'ResultsCount': 50,
            'TotalBytesScanned': 1048576,
            'BytesScanned': 524288,
            'ExecutionTimeInMillis': 2500,
        }

        result_rows = [
            [{'VarCharValue': 'event1'}, {'VarCharValue': '25'}],
            [{'VarCharValue': 'event2'}, {'VarCharValue': '25'}],
        ]

        result = QueryResult(
            query_id='complete-query',
            query_status='FINISHED',
            query_statistics=statistics,
            query_result_rows=result_rows,
            next_token='next-token-abc',
            error_message=None,
        )

        assert result.query_id == 'complete-query'
        assert result.query_status == 'FINISHED'
        assert result.query_statistics is not None
        assert result.query_statistics['ResultsCount'] == 50
        assert result.query_result_rows is not None
        assert len(result.query_result_rows) == 2
        assert result.next_token == 'next-token-abc'
        assert result.error_message is None


class TestQueryStatus:
    """Test QueryStatus model."""

    def test_query_status_basic(self):
        """Test basic QueryStatus creation."""
        status = QueryStatus(query_id='status-query-123', query_status='RUNNING')

        assert status.query_id == 'status-query-123'
        assert status.query_status == 'RUNNING'
        assert status.query_statistics is None
        assert status.error_message is None
        assert status.delivery_s3_uri is None
        assert status.delivery_status is None

    def test_query_status_with_statistics(self):
        """Test QueryStatus with statistics."""
        statistics = {
            'ResultsCount': 0,  # Still running, no results yet
            'TotalBytesScanned': 0,
            'BytesScanned': 0,
            'ExecutionTimeInMillis': 15000,  # Running for 15 seconds
        }

        status = QueryStatus(
            query_id='running-query-456', query_status='RUNNING', query_statistics=statistics
        )

        assert status.query_id == 'running-query-456'
        assert status.query_status == 'RUNNING'
        assert status.query_statistics == statistics
        assert status.query_statistics is not None
        assert status.query_statistics['ExecutionTimeInMillis'] == 15000

    def test_query_status_finished_with_delivery(self):
        """Test QueryStatus for finished query with S3 delivery."""
        statistics = {
            'ResultsCount': 1000,
            'TotalBytesScanned': 10485760,
            'BytesScanned': 5242880,
            'ExecutionTimeInMillis': 30000,
        }

        status = QueryStatus(
            query_id='delivered-query-789',
            query_status='FINISHED',
            query_statistics=statistics,
            delivery_s3_uri='s3://my-cloudtrail-bucket/query-results/delivered-query-789/',
            delivery_status='SUCCESS',
        )

        assert status.query_id == 'delivered-query-789'
        assert status.query_status == 'FINISHED'
        assert status.query_statistics is not None
        assert status.query_statistics['ResultsCount'] == 1000
        assert (
            status.delivery_s3_uri
            == 's3://my-cloudtrail-bucket/query-results/delivered-query-789/'
        )
        assert status.delivery_status == 'SUCCESS'
        assert status.error_message is None

    def test_query_status_failed_with_error(self):
        """Test QueryStatus for failed query."""
        status = QueryStatus(
            query_id='failed-query-abc',
            query_status='FAILED',
            error_message='Table does not exist: nonexistent_eds',
        )

        assert status.query_id == 'failed-query-abc'
        assert status.query_status == 'FAILED'
        assert status.error_message == 'Table does not exist: nonexistent_eds'
        assert status.delivery_s3_uri is None
        assert status.delivery_status is None

    def test_query_status_cancelled(self):
        """Test QueryStatus for cancelled query."""
        statistics = {
            'ResultsCount': 0,
            'TotalBytesScanned': 1048576,  # Some bytes scanned before cancellation
            'BytesScanned': 0,
            'ExecutionTimeInMillis': 5000,
        }

        status = QueryStatus(
            query_id='cancelled-query-def', query_status='CANCELLED', query_statistics=statistics
        )

        assert status.query_id == 'cancelled-query-def'
        assert status.query_status == 'CANCELLED'
        assert status.query_statistics is not None
        assert status.query_statistics['TotalBytesScanned'] == 1048576
        assert status.error_message is None

    def test_query_status_timed_out(self):
        """Test QueryStatus for timed out query."""
        statistics = {
            'ResultsCount': 0,
            'TotalBytesScanned': 104857600,  # 100MB scanned before timeout
            'BytesScanned': 0,
            'ExecutionTimeInMillis': 300000,  # 5 minutes (timeout)
        }

        status = QueryStatus(
            query_id='timeout-query-ghi',
            query_status='TIMED_OUT',
            query_statistics=statistics,
            error_message='Query execution exceeded the maximum allowed time',
        )

        assert status.query_id == 'timeout-query-ghi'
        assert status.query_status == 'TIMED_OUT'
        assert status.query_statistics is not None
        assert status.query_statistics['ExecutionTimeInMillis'] == 300000
        assert status.error_message is not None
        assert 'maximum allowed time' in status.error_message

    def test_query_status_delivery_in_progress(self):
        """Test QueryStatus with delivery in progress."""
        status = QueryStatus(
            query_id='delivery-query-jkl',
            query_status='FINISHED',
            delivery_s3_uri='s3://results-bucket/query-results/delivery-query-jkl/',
            delivery_status='IN_PROGRESS',
        )

        assert status.query_id == 'delivery-query-jkl'
        assert status.query_status == 'FINISHED'
        assert status.delivery_s3_uri == 's3://results-bucket/query-results/delivery-query-jkl/'
        assert status.delivery_status == 'IN_PROGRESS'


class TestModelIntegration:
    """Test model integration and edge cases."""

    def test_models_with_none_values(self):
        """Test models handle None values correctly."""
        # EventDataStore with all None values
        eds = EventDataStore.model_validate({})
        assert all(
            getattr(eds, field) is None
            for field in [
                'event_data_store_arn',
                'name',
                'status',
                'multi_region_enabled',
                'organization_enabled',
                'retention_period',
                'termination_protection_enabled',
                'created_timestamp',
                'updated_timestamp',
                'kms_key_id',
                'billing_mode',
                'advanced_event_selectors',
            ]
        )

        # QueryResult with minimal fields
        qr = QueryResult(query_id='test', query_status='QUEUED')
        assert qr.query_statistics is None
        assert qr.query_result_rows is None
        assert qr.next_token is None
        assert qr.error_message is None

        # QueryStatus with minimal fields
        qs = QueryStatus(query_id='test', query_status='QUEUED')
        assert qs.query_statistics is None
        assert qs.error_message is None
        assert qs.delivery_s3_uri is None
        assert qs.delivery_status is None

    def test_models_json_serialization(self):
        """Test that models can be serialized to JSON."""
        # EventDataStore
        eds = EventDataStore.model_validate(
            {
                'name': 'TestEDS',
                'status': 'ENABLED',
                'created_timestamp': datetime.now(timezone.utc),
            }
        )
        eds_json = eds.model_dump(mode='json')
        assert 'name' in eds_json
        assert 'status' in eds_json
        assert 'created_timestamp' in eds_json

        # QueryResult
        qr = QueryResult(
            query_id='test-query', query_status='FINISHED', query_statistics={'ResultsCount': 10}
        )
        qr_json = qr.model_dump(mode='json')
        assert qr_json['query_id'] == 'test-query'
        assert qr_json['query_status'] == 'FINISHED'
        assert qr_json['query_statistics']['ResultsCount'] == 10

        # QueryStatus
        qs = QueryStatus(query_id='status-query', query_status='RUNNING')
        qs_json = qs.model_dump(mode='json')
        assert qs_json['query_id'] == 'status-query'
        assert qs_json['query_status'] == 'RUNNING'

    def test_model_field_aliases_consistency(self):
        """Test that field aliases work consistently across models."""
        # EventDataStore should accept both PascalCase and snake_case
        pascal_data = {'EventDataStoreArn': 'arn:test', 'Name': 'Test'}
        snake_data = {'event_data_store_arn': 'arn:test', 'name': 'Test'}

        eds_pascal = EventDataStore.model_validate(pascal_data)
        eds_snake = EventDataStore.model_validate(snake_data)

        assert eds_pascal.event_data_store_arn == eds_snake.event_data_store_arn
        assert eds_pascal.name == eds_snake.name

    def test_models_with_complex_data_types(self):
        """Test models with complex nested data structures."""
        # EventDataStore with complex advanced event selectors
        complex_selectors = [
            {
                'Name': 'Complex selector',
                'FieldSelectors': [
                    {
                        'Field': 'eventCategory',
                        'Equals': ['Management', 'Data'],
                        'NotEquals': ['Insight'],
                    },
                    {
                        'Field': 'resources.type',
                        'Equals': ['AWS::S3::Object', 'AWS::DynamoDB::Table'],
                        'StartsWith': ['AWS::'],
                        'EndsWith': ['::Object', '::Table'],
                    },
                ],
                'ExcludeManagementEventSources': ['kms.amazonaws.com'],
            }
        ]

        eds = EventDataStore.model_validate(
            {'name': 'ComplexEDS', 'advanced_event_selectors': complex_selectors}
        )

        assert eds.name == 'ComplexEDS'
        assert eds.advanced_event_selectors is not None
        assert len(eds.advanced_event_selectors) == 1
        assert len(eds.advanced_event_selectors[0]['FieldSelectors']) == 2
        assert 'ExcludeManagementEventSources' in eds.advanced_event_selectors[0]

        # QueryResult with complex result rows
        complex_rows = [
            [
                {'VarCharValue': 'ConsoleLogin'},
                {'TimestampValue': '2023-01-01T12:00:00Z'},
                {'DoubleValue': '1.0'},
                {'LongValue': '12345'},
            ],
            [
                {'VarCharValue': 'CreateUser'},
                {'TimestampValue': '2023-01-01T13:00:00Z'},
                {'DoubleValue': '2.5'},
                {'LongValue': '67890'},
            ],
        ]

        qr = QueryResult(
            query_id='complex-query', query_status='FINISHED', query_result_rows=complex_rows
        )

        assert qr.query_result_rows is not None
        assert len(qr.query_result_rows) == 2
        assert qr.query_result_rows[0][3]['LongValue'] == '12345'
        assert qr.query_result_rows[1][2]['DoubleValue'] == '2.5'


if __name__ == '__main__':
    pytest.main([__file__])
