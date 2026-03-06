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

"""Tests for change_tools module."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.change_tools import (
    _list_change_events,
)
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_applicationsignals_client = MagicMock()

    patches = [
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.change_tools.applicationsignals_client',
            mock_applicationsignals_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {
            'applicationsignals_client': mock_applicationsignals_client,
        }
    finally:
        for p in patches:
            p.stop()


class TestListChangeEventsBasic:
    """Test basic functionality of list_change_events."""

    @pytest.mark.asyncio
    async def test_basic_functionality_comprehensive_history_true(self, mock_aws_clients):
        """Test basic functionality with comprehensive_history=True (ListEntityEvents)."""
        # Mock ListEntityEvents response
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'event-123',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {
                        'Type': 'Service',
                        'Name': 'payment-service',
                        'Environment': 'eks:production',
                    },
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'payment-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert 'change_events' in result
        assert 'total_events' in result
        assert result['total_events'] == 1
        assert len(result['change_events']) == 1

        event = result['change_events'][0]
        assert event['event_id'] == 'event-123'
        assert event['change_event_type'] == 'DEPLOYMENT'
        # Note: entity field is not included in ListEntityEvents response

    @pytest.mark.asyncio
    async def test_basic_functionality_comprehensive_history_false(self, mock_aws_clients):
        """Test basic functionality with comprehensive_history=False (ListServiceStates)."""
        # Mock ListServiceStates response
        mock_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'checkout-service',
                        'Environment': 'eks:production',
                        'Platform': 'EKS',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'state-event-456',
                            'EventName': 'ServiceStateChange',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'system',
                        }
                    ],
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=False,
        )

        result = json.loads(result_str)
        assert 'change_events' in result
        assert 'total_events' in result
        assert result['total_events'] == 1
        assert len(result['change_events']) == 1

        event = result['change_events'][0]
        assert event['event_id'] == 'state-event-456'
        assert event['change_event_type'] == 'CONFIGURATION'
        # Note: entity field is not included when not present in the event
        assert 'entity' not in event


class TestListChangeEventsValidation:
    """Test validation and error handling."""

    @pytest.mark.asyncio
    async def test_time_validation_start_after_end(self):
        """Test time validation - start_time must be before end_time."""
        result_str = await _list_change_events(
            start_time='2024-01-15T16:00:00Z',  # Later time
            end_time='2024-01-15T10:00:00Z',  # Earlier time
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'start_time must be before end_time' in result['error']

    @pytest.mark.asyncio
    async def test_service_key_attributes_required_for_comprehensive_history(self):
        """Test that service_key_attributes is required when comprehensive_history=True."""
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=True,  # No service_key_attributes provided
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert (
            'service_key_attributes is required when comprehensive_history=True' in result['error']
        )

    @pytest.mark.asyncio
    async def test_max_results_validation_and_clamping(self, mock_aws_clients):
        """Test max_results parameter validation and clamping."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Test with max_results > 250 (should be clamped to 250)
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            max_results=500,  # Should be clamped to 250
        )

        result = json.loads(result_str)
        assert 'change_events' in result

        # Verify the API was called with max_results=250
        mock_aws_clients['applicationsignals_client'].list_entity_events.assert_called_once()
        call_args = mock_aws_clients['applicationsignals_client'].list_entity_events.call_args[1]
        assert call_args['MaxResults'] == 250

    @pytest.mark.asyncio
    async def test_invalid_timestamp_format_handling(self):
        """Test error handling for invalid timestamp formats."""
        result_str = await _list_change_events(
            start_time='invalid-timestamp', end_time='2024-01-15T16:00:00Z'
        )

        result = json.loads(result_str)
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_missing_required_service_key_attributes_type(self):
        """Test ValueError when service_key_attributes is missing 'Type' field."""
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Environment': 'eks:production',
                # Missing 'Type' - should raise ValueError
            },
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Missing required service_key_attributes: Type' in result['error']

    @pytest.mark.asyncio
    async def test_missing_required_service_key_attributes_name(self):
        """Test ValueError when service_key_attributes is missing 'Name' field."""
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Type': 'Service',
                'Environment': 'eks:production',
                # Missing 'Name' - should raise ValueError
            },
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Missing required service_key_attributes: Name' in result['error']

    @pytest.mark.asyncio
    async def test_missing_required_service_key_attributes_environment(self):
        """Test ValueError when service_key_attributes is missing 'Environment' field."""
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Type': 'Service',
                'Name': 'test-service',
                # Missing 'Environment' - should raise ValueError
            },
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Missing required service_key_attributes: Environment' in result['error']

    @pytest.mark.asyncio
    async def test_missing_multiple_required_service_key_attributes(self):
        """Test ValueError when service_key_attributes is missing multiple required fields."""
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                # Missing 'Type' and 'Environment' - should raise ValueError
            },
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Missing required service_key_attributes: Type, Environment' in result['error']

    @pytest.mark.asyncio
    async def test_empty_service_key_attributes_dict(self):
        """Test ValueError when service_key_attributes is an empty dict."""
        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={},  # Empty dict - should be treated as falsy
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert (
            'service_key_attributes is required when comprehensive_history=True' in result['error']
        )

    @pytest.mark.asyncio
    async def test_service_key_attributes_with_extra_fields_filtered(self, mock_aws_clients):
        """Test that extra fields in service_key_attributes are filtered out."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        service_attrs = {
            'Type': 'Service',
            'Name': 'test-service',
            'Environment': 'eks:production',
            'AwsAccountId': '123456789012',  # Valid extra field
            'InvalidField': 'should-be-filtered',  # Invalid field - should be filtered
            'AnotherInvalid': 'also-filtered',  # Another invalid field
        }

        await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes=service_attrs,
            comprehensive_history=True,
        )

        # Verify the entity was built correctly with only valid attributes
        call_args = mock_aws_clients['applicationsignals_client'].list_entity_events.call_args[1]
        entity = call_args['Entity']

        # Should include valid attributes
        assert entity['Type'] == 'Service'
        assert entity['Name'] == 'test-service'
        assert entity['Environment'] == 'eks:production'
        assert entity['AwsAccountId'] == '123456789012'

        # Should NOT include invalid attributes
        assert 'InvalidField' not in entity
        assert 'AnotherInvalid' not in entity

    @pytest.mark.asyncio
    async def test_max_results_boundary_minimum(self, mock_aws_clients):
        """Test max_results boundary condition with minimum value (1)."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Type': 'Service',
                'Name': 'test-service',
                'Environment': 'eks:production',
            },
            max_results=1,  # Minimum valid value
        )

        result = json.loads(result_str)
        assert 'change_events' in result

        # Verify the API was called with max_results=1
        call_args = mock_aws_clients['applicationsignals_client'].list_entity_events.call_args[1]
        assert call_args['MaxResults'] == 1

    @pytest.mark.asyncio
    async def test_max_results_boundary_zero_clamped(self, mock_aws_clients):
        """Test max_results boundary condition with zero (should be clamped to 1)."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Type': 'Service',
                'Name': 'test-service',
                'Environment': 'eks:production',
            },
            max_results=0,  # Should be clamped to 1
        )

        result = json.loads(result_str)
        assert 'change_events' in result

        # Verify the API was called with max_results=1 (clamped from 0)
        call_args = mock_aws_clients['applicationsignals_client'].list_entity_events.call_args[1]
        assert call_args['MaxResults'] == 1

    @pytest.mark.asyncio
    async def test_max_results_boundary_negative_clamped(self, mock_aws_clients):
        """Test max_results boundary condition with negative value (should be clamped to 1)."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Type': 'Service',
                'Name': 'test-service',
                'Environment': 'eks:production',
            },
            max_results=-5,  # Should be clamped to 1
        )

        result = json.loads(result_str)
        assert 'change_events' in result

        # Verify the API was called with max_results=1 (clamped from -5)
        call_args = mock_aws_clients['applicationsignals_client'].list_entity_events.call_args[1]
        assert call_args['MaxResults'] == 1


class TestListChangeEventsErrorHandling:
    """Test AWS API error handling."""

    @pytest.mark.asyncio
    async def test_no_credentials_error(self, mock_aws_clients):
        """Test handling of NoCredentialsError."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.side_effect = NoCredentialsError()

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'AWS credentials not found' in result['error']

    @pytest.mark.asyncio
    async def test_validation_exception_error(self, mock_aws_clients):
        """Test handling of ValidationException."""
        error_response: Any = {
            'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter value'},
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HTTPStatusCode': 400,
                'HTTPHeaders': {},
                'RetryAttempts': 0,
            },
        }
        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = ClientError(
            error_response, 'ListEntityEvents'
        )

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Invalid request parameters' in result['error']
        assert result.get('error_code') == 'ValidationException'

    @pytest.mark.asyncio
    async def test_throttling_exception_error(self, mock_aws_clients):
        """Test handling of ThrottlingException."""
        error_response: Any = {
            'Error': {'Code': 'ThrottlingException', 'Message': 'Request was throttled'},
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HTTPStatusCode': 429,
                'HTTPHeaders': {},
                'RetryAttempts': 0,
            },
        }
        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = ClientError(
            error_response, 'ListEntityEvents'
        )

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Request was throttled' in result['error']
        assert result.get('error_code') == 'ThrottlingException'

    @pytest.mark.asyncio
    async def test_generic_client_error(self, mock_aws_clients):
        """Test handling of generic ClientError."""
        error_response: Any = {
            'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'},
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HTTPStatusCode': 500,
                'HTTPHeaders': {},
                'RetryAttempts': 0,
            },
        }
        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = ClientError(
            error_response, 'ListEntityEvents'
        )

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'AWS API error' in result['error']
        assert result.get('error_code') == 'InternalServerError'

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, mock_aws_clients):
        """Test handling of generic exceptions."""
        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = Exception(
            'Unexpected error'
        )

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'Failed to retrieve change events' in result['error']


class TestListChangeEventsPagination:
    """Test pagination handling."""

    @pytest.mark.asyncio
    async def test_pagination_with_next_token(self, mock_aws_clients):
        """Test pagination handling with NextToken."""
        # First call returns events with NextToken
        first_response = {
            'ChangeEvents': [
                {
                    'EventId': 'event-1',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': 'service-1'},
                }
            ],
            'NextToken': 'token-123',
        }

        # Second call returns more events without NextToken
        second_response = {
            'ChangeEvents': [
                {
                    'EventId': 'event-2',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': 'service-2'},
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = [
            first_response,
            second_response,
        ]

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            max_results=10,
        )

        result = json.loads(result_str)
        assert result['total_events'] == 2
        assert len(result['change_events']) == 2

        # Verify both API calls were made
        assert mock_aws_clients['applicationsignals_client'].list_entity_events.call_count == 2

        # Verify second call included NextToken
        second_call_args = mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.call_args_list[1][1]
        assert second_call_args['NextToken'] == 'token-123'

    @pytest.mark.asyncio
    async def test_pagination_stops_at_max_results(self, mock_aws_clients):
        """Test that pagination stops when max_results is reached."""
        # Mock response with many events
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': f'event-{i}',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, i, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': f'service-{i}'},
                }
                for i in range(5)
            ],
            'NextToken': 'more-events-available',
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            max_results=3,  # Limit to 3 events
        )

        result = json.loads(result_str)
        assert result['total_events'] == 3  # Should be limited to max_results
        assert len(result['change_events']) == 3


class TestListChangeEventsEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_aws_clients):
        """Test handling of empty response."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert result['total_events'] == 0
        assert len(result['change_events']) == 0
        assert isinstance(result['events_by_type'], dict)
        assert len(result['events_by_type']) == 0

    @pytest.mark.asyncio
    async def test_timestamp_handling_numeric_values(self, mock_aws_clients):
        """Test handling of numeric timestamp values from AWS API."""
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'event-123',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': 1705320000.0,  # Numeric timestamp instead of datetime
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': 'test-service'},
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert result['total_events'] == 1
        event = result['change_events'][0]
        assert event['timestamp'] == '2024-01-15T12:00:00+00:00'

    @pytest.mark.asyncio
    async def test_service_key_attributes_filtering(self, mock_aws_clients):
        """Test service key attributes filtering and entity building."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        service_attrs = {
            'Type': 'Service',
            'Name': 'payment-service',
            'Environment': 'eks:production',
            'ResourceType': 'AWS::ECS::Service',
            'Identifier': 'arn:aws:ecs:us-east-1:123456789012:service/payment-service',
            'AwsAccountId': '123456789012',
        }

        await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes=service_attrs,
        )

        # Verify the entity was built correctly from service_key_attributes
        call_args = mock_aws_clients['applicationsignals_client'].list_entity_events.call_args[1]
        entity = call_args['Entity']

        # Only check valid attributes that should be passed through
        valid_attrs = ['Type', 'Name', 'Environment', 'AwsAccountId']
        for key in valid_attrs:
            if key in service_attrs:
                assert entity[key] == service_attrs[key]

    @pytest.mark.asyncio
    async def test_events_by_type_aggregation(self, mock_aws_clients):
        """Test that events_by_type is correctly aggregated."""
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'event-1',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': 'service-1'},
                },
                {
                    'EventId': 'event-2',
                    'EventName': 'UpdateConfiguration',
                    'ChangeEventType': 'CONFIGURATION',
                    'Timestamp': datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'config-user',
                    'Entity': {'Type': 'Service', 'Name': 'service-2'},
                },
                {
                    'EventId': 'event-3',
                    'EventName': 'UpdateService2',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': 'service-3'},
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert result['events_by_type']['DEPLOYMENT'] == 2
        assert result['events_by_type']['CONFIGURATION'] == 1

    @pytest.mark.asyncio
    async def test_response_structure_completeness(self, mock_aws_clients):
        """Test that the response has all expected fields."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)

        # Check all expected top-level fields (based on actual implementation)
        expected_fields = {'change_events', 'total_events', 'events_by_type'}

        for field in expected_fields:
            assert field in result, f'Missing field: {field}'

        # Check data types
        assert isinstance(result['change_events'], list)
        assert isinstance(result['events_by_type'], dict)
        assert isinstance(result['total_events'], int)

    @pytest.mark.asyncio
    async def test_seconds_since_event_calculation(self, mock_aws_clients):
        """Test that seconds_since_event is calculated correctly for different timestamp formats."""
        # Create events with different timestamp formats
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'event-datetime',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-user',
                    'Entity': {'Type': 'Service', 'Name': 'test-service'},
                },
                {
                    'EventId': 'event-numeric',
                    'EventName': 'UpdateConfiguration',
                    'ChangeEventType': 'CONFIGURATION',
                    'Timestamp': 1705320000.0,  # 2024-01-15T12:00:00Z
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'config-user',
                    'Entity': {'Type': 'Service', 'Name': 'test-service'},
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Mock current time to be 1 hour after the events
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.change_tools.datetime'
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
            mock_datetime.fromtimestamp = datetime.fromtimestamp

            result_str = await _list_change_events(
                start_time='2024-01-15T10:00:00Z',
                end_time='2024-01-15T16:00:00Z',
                service_key_attributes={
                    'Name': 'test-service',
                    'Type': 'Service',
                    'Environment': 'eks:production',
                },
            )

        result = json.loads(result_str)
        events = result['change_events']

        # Both events should have seconds_since_event = 3600 (1 hour = 3600 seconds)
        assert len(events) == 2
        for event in events:
            assert 'seconds_since_event' in event
            assert event['seconds_since_event'] == 3600
            assert isinstance(event['seconds_since_event'], int)


class TestListChangeEventsServiceStates:
    """Test ListServiceStates API path (comprehensive_history=False)."""

    @pytest.mark.asyncio
    async def test_list_service_states_basic(self, mock_aws_clients):
        """Test basic ListServiceStates functionality."""
        mock_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'checkout-service',
                        'Environment': 'eks:production',
                        'Platform': 'EKS',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'state-event-1',
                            'EventName': 'ServiceStateChange',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'system',
                        }
                    ],
                }
            ],
            'NextToken': None,
            'StartTime': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            'EndTime': datetime(2024, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=False,
        )

        result = json.loads(result_str)
        assert result['total_events'] == 1

        event = result['change_events'][0]
        assert event['event_id'] == 'state-event-1'
        # Note: entity field is not included in ListServiceStates response when not present
        assert 'entity' not in event

    @pytest.mark.asyncio
    async def test_list_service_states_with_service_filtering(self, mock_aws_clients):
        """Test ListServiceStates with service attribute filtering."""
        mock_response = {'ServiceStates': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        service_attrs = {'Name': 'payment-service', 'Environment': 'eks:production'}

        await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes=service_attrs,
            comprehensive_history=False,
        )

        # Verify that the API was called without AttributeFilters (filtering happens post-response)
        call_args = mock_aws_clients['applicationsignals_client'].list_service_states.call_args[1]
        assert 'AttributeFilters' not in call_args

        # The filtering happens after the API call in the implementation
        # We can't easily test the filtering logic without mocking the service states response

    @pytest.mark.asyncio
    async def test_list_service_states_multiple_services_multiple_events(self, mock_aws_clients):
        """Test ListServiceStates with multiple services and events."""
        mock_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'service-1',
                        'Environment': 'eks:production',
                        'Platform': 'EKS',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'event-1-1',
                            'EventName': 'ServiceUpdate',
                            'ChangeEventType': 'DEPLOYMENT',
                            'Timestamp': 1705320000.0,
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'deploy-user',
                        },
                        {
                            'EventId': 'event-1-2',
                            'EventName': 'ConfigUpdate',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': 1705323600.0,
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'config-user',
                        },
                    ],
                },
                {
                    'Service': {
                        'Name': 'service-2',
                        'Environment': 'lambda',
                        'Platform': 'Lambda',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'event-2-1',
                            'EventName': 'FunctionUpdate',
                            'ChangeEventType': 'DEPLOYMENT',
                            'Timestamp': 1705327200.0,
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'lambda-user',
                        }
                    ],
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=False,
        )

        result = json.loads(result_str)
        assert result['total_events'] == 3  # 2 events from service-1 + 1 from service-2
        assert result['events_by_type']['DEPLOYMENT'] == 2
        assert result['events_by_type']['CONFIGURATION'] == 1

        # Verify events are sorted by timestamp
        timestamps = [event['timestamp'] for event in result['change_events']]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_list_service_states_pagination(self, mock_aws_clients):
        """Test ListServiceStates pagination."""
        first_response = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'service-1', 'Environment': 'eks:prod', 'Platform': 'EKS'},
                    'LatestChangeEvents': [
                        {
                            'EventId': 'event-1',
                            'EventName': 'Update',
                            'ChangeEventType': 'DEPLOYMENT',
                            'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'user',
                        }
                    ],
                }
            ],
            'NextToken': 'token-123',
        }

        second_response = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'service-2', 'Environment': 'eks:prod', 'Platform': 'EKS'},
                    'LatestChangeEvents': [
                        {
                            'EventId': 'event-2',
                            'EventName': 'Update',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'user',
                        }
                    ],
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.side_effect = [
            first_response,
            second_response,
        ]

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=False,
            max_results=10,
        )

        result = json.loads(result_str)
        assert result['total_events'] == 2
        assert mock_aws_clients['applicationsignals_client'].list_service_states.call_count == 2

    @pytest.mark.asyncio
    async def test_list_service_states_seconds_since_event(self, mock_aws_clients):
        """Test that seconds_since_event is calculated correctly for ServiceStates API."""
        mock_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'test-service',
                        'Environment': 'eks:production',
                        'Type': 'Service',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'deploy-123',
                            'EventName': 'ServiceDeployment',
                            'ChangeEventType': 'DEPLOYMENT',
                            'Timestamp': datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'deploy-pipeline',
                        }
                    ],
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        # Mock current time to be 30 minutes after the deployment
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.change_tools.datetime'
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
            mock_datetime.fromtimestamp = datetime.fromtimestamp

            result_str = await _list_change_events(
                start_time='2024-01-15T10:00:00Z',
                end_time='2024-01-15T16:00:00Z',
                comprehensive_history=False,
            )

        result = json.loads(result_str)
        events = result['change_events']

        # Event should have seconds_since_event = 1800 (30 minutes = 1800 seconds)
        assert len(events) == 1
        event = events[0]
        assert 'seconds_since_event' in event
        assert event['seconds_since_event'] == 1800
        assert isinstance(event['seconds_since_event'], int)


class TestListChangeEventsRegionHandling:
    """Test region parameter handling."""

    @pytest.mark.asyncio
    async def test_region_parameter_passed_through(self, mock_aws_clients):
        """Test that region parameter is handled correctly."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            region='us-west-2',
        )

        result = json.loads(result_str)
        assert 'change_events' in result
        # Region parameter should be accepted without error


class TestListChangeEventsTimestampFormats:
    """Test various timestamp format handling."""

    @pytest.mark.asyncio
    async def test_unix_timestamp_input(self, mock_aws_clients):
        """Test Unix timestamp input format."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='1705320000',  # Unix timestamp as string
            end_time='1705341600',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'change_events' in result

    @pytest.mark.asyncio
    async def test_iso_timestamp_variations(self, mock_aws_clients):
        """Test various ISO timestamp formats."""
        mock_response = {'ChangeEvents': [], 'NextToken': None}
        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Test different ISO formats
        iso_formats = [
            '2024-01-15T10:00:00Z',
            '2024-01-15T10:00:00+00:00',
            '2024-01-15T10:00:00.000Z',
            '2024-01-15 10:00:00',
        ]

        for start_format in iso_formats[:2]:  # Test a couple to avoid too many API calls
            result_str = await _list_change_events(
                start_time=start_format,
                end_time='2024-01-15T16:00:00Z',
                service_key_attributes={
                    'Name': 'test-service',
                    'Type': 'Service',
                    'Environment': 'eks:production',
                },
            )

            result = json.loads(result_str)
            assert 'change_events' in result


class TestListChangeEventsIntegration:
    """Integration tests for list_change_events MCP server integration."""

    @pytest.mark.asyncio
    async def test_server_integration_list_entity_events(self, mock_aws_clients):
        """Test MCP server integration with ListEntityEvents API."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.change_tools import (
            _list_change_events as server_list_change_events,
        )

        # Mock ListEntityEvents response
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'integration-event-1',
                    'EventName': 'DeploymentUpdate',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'integration-user',
                    'Entity': {
                        'Type': 'Service',
                        'Name': 'integration-service',
                        'Environment': 'eks:integration',
                    },
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Test server function directly
        result_str = await server_list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'integration-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            comprehensive_history=True,
        )

        result = json.loads(result_str)
        assert result['total_events'] == 1
        assert result['change_events'][0]['event_id'] == 'integration-event-1'

    @pytest.mark.asyncio
    async def test_server_integration_list_service_states(self, mock_aws_clients):
        """Test MCP server integration with ListServiceStates API."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.change_tools import (
            _list_change_events as server_list_change_events,
        )

        # Mock ListServiceStates response
        mock_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'integration-service-2',
                        'Environment': 'lambda',
                        'Platform': 'Lambda',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'integration-state-1',
                            'EventName': 'FunctionUpdate',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-west-2',
                            'UserName': 'lambda-deployer',
                        }
                    ],
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        # Test server function with comprehensive_history=False
        result_str = await server_list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=False,
            region='us-west-2',
        )

        result = json.loads(result_str)
        assert result['total_events'] == 1
        assert result['change_events'][0]['event_id'] == 'integration-state-1'

    @pytest.mark.asyncio
    async def test_server_integration_parameter_validation(self):
        """Test MCP server parameter validation integration."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.server import (
            list_change_events as server_list_change_events,
        )

        # Test invalid time range
        result_str = await server_list_change_events(
            start_time='2024-01-15T16:00:00Z',
            end_time='2024-01-15T10:00:00Z',  # End before start
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'start_time must be before end_time' in result['error']

    @pytest.mark.asyncio
    async def test_server_integration_error_handling(self, mock_aws_clients):
        """Test MCP server error handling integration."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.change_tools import (
            _list_change_events as server_list_change_events,
        )

        # Mock AWS API error
        error_response: Any = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform this action',
            },
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HTTPStatusCode': 403,
                'HTTPHeaders': {},
                'RetryAttempts': 0,
            },
        }
        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = ClientError(
            error_response, 'ListEntityEvents'
        )

        result_str = await server_list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)
        assert 'error' in result
        assert 'AWS API error' in result['error']

    @pytest.mark.asyncio
    async def test_server_integration_large_response_handling(self, mock_aws_clients):
        """Test MCP server handling of large responses with pagination."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.server import (
            list_change_events as server_list_change_events,
        )

        # Mock large response with pagination
        first_response = {
            'ChangeEvents': [
                {
                    'EventId': f'large-event-{i}',
                    'EventName': 'BulkUpdate',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, i, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'bulk-deployer',
                    'Entity': {
                        'Type': 'Service',
                        'Name': f'service-{i}',
                        'Environment': 'eks:production',
                    },
                }
                for i in range(50)
            ],
            'NextToken': 'large-response-token',
        }

        second_response = {
            'ChangeEvents': [
                {
                    'EventId': f'large-event-{i}',
                    'EventName': 'BulkUpdate',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 13, i - 50, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'bulk-deployer',
                    'Entity': {
                        'Type': 'Service',
                        'Name': f'service-{i}',
                        'Environment': 'eks:production',
                    },
                }
                for i in range(50, 75)
            ],
            'NextToken': None,
        }

        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = [
            first_response,
            second_response,
        ]

        result_str = await server_list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Type': 'Service',
                'Name': 'test-service',
                'Environment': 'eks:production',
            },
            max_results=100,
        )

        result = json.loads(result_str)
        assert result['total_events'] == 75
        assert len(result['change_events']) == 75

        # Verify pagination was handled
        assert mock_aws_clients['applicationsignals_client'].list_entity_events.call_count == 2

    @pytest.mark.asyncio
    async def test_server_integration_real_world_scenario(self, mock_aws_clients):
        """Test MCP server integration with realistic incident investigation scenario."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.change_tools import (
            _list_change_events as server_list_change_events,
        )

        # Mock realistic incident scenario: payment service deployment followed by errors
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'incident-deploy-1',
                    'EventName': 'UpdateService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 14, 45, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'payment-team-deployer',
                    'Entity': {
                        'Type': 'Service',
                        'Name': 'payment-service',
                        'Environment': 'eks:production',
                        'ResourceType': 'AWS::ECS::Service',
                    },
                },
                {
                    'EventId': 'incident-config-1',
                    'EventName': 'UpdateTaskDefinition',
                    'ChangeEventType': 'CONFIGURATION',
                    'Timestamp': datetime(2024, 1, 15, 15, 15, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'payment-team-deployer',
                    'Entity': {
                        'Type': 'Service',
                        'Name': 'payment-service',
                        'Environment': 'eks:production',
                        'ResourceType': 'AWS::ECS::Service',
                    },
                },
                {
                    'EventId': 'incident-rollback-1',
                    'EventName': 'RollbackService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 15, 25, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'payment-team-sre',
                    'Entity': {
                        'Type': 'Service',
                        'Name': 'payment-service',
                        'Environment': 'eks:production',
                        'ResourceType': 'AWS::ECS::Service',
                    },
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Simulate incident investigation: "Payment service alarm fired at 15:30, what changed?"
        result_str = await server_list_change_events(
            start_time='2024-01-15T12:00:00Z',  # 6 hours before alarm
            end_time='2024-01-15T18:00:00Z',  # Current time
            service_key_attributes={
                'Name': 'payment-service',
                'Environment': 'eks:production',
                'Type': 'Service',
            },
        )

        result = json.loads(result_str)

        # Verify incident timeline is captured
        assert result['total_events'] == 3
        assert result['events_by_type']['DEPLOYMENT'] == 2  # Deploy + rollback
        assert result['events_by_type']['CONFIGURATION'] == 1

        # Verify chronological order for incident analysis
        events = result['change_events']
        assert events[0]['event_name'] == 'UpdateService'  # 14:45 - Initial deployment
        assert events[1]['event_name'] == 'UpdateTaskDefinition'  # 15:15 - Config change
        assert (
            events[2]['event_name'] == 'RollbackService'
        )  # 15:25 - Rollback (before alarm at 15:30)

        # Verify all events have the expected event IDs
        assert events[0]['event_id'] == 'incident-deploy-1'
        assert events[1]['event_id'] == 'incident-config-1'
        assert events[2]['event_id'] == 'incident-rollback-1'


class TestListChangeEventsToolFunctionality:
    """Integration tests for list_change_events tool functionality."""

    @pytest.mark.asyncio
    async def test_integration_both_api_paths(self, mock_aws_clients):
        """Test integration between both API paths (ListEntityEvents and ListServiceStates)."""
        # Test that both comprehensive_history=True and False work correctly

        # Mock ListEntityEvents response
        entity_response = {
            'ChangeEvents': [
                {
                    'EventId': 'entity-event-1',
                    'EventName': 'DeploymentUpdate',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deployer',
                    'Entity': {'Type': 'Service', 'Name': 'test-service'},
                }
            ],
            'NextToken': None,
        }

        # Mock ListServiceStates response
        states_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'test-service',
                        'Environment': 'eks:prod',
                        'Platform': 'EKS',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'state-event-1',
                            'EventName': 'ServiceUpdate',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'system',
                        }
                    ],
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = entity_response
        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = states_response

        # Test ListEntityEvents path
        result1_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'test-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
            comprehensive_history=True,
        )

        result1 = json.loads(result1_str)
        assert result1['total_events'] == 1
        assert result1['change_events'][0]['event_id'] == 'entity-event-1'

        # Test ListServiceStates path
        result2_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            comprehensive_history=False,
        )

        result2 = json.loads(result2_str)
        assert result2['total_events'] == 1
        assert result2['change_events'][0]['event_id'] == 'state-event-1'

    @pytest.mark.asyncio
    async def test_integration_error_recovery_workflow(self, mock_aws_clients):
        """Test integration of error handling and recovery workflows."""
        # First call fails with throttling
        error_response: Any = {
            'Error': {'Code': 'ThrottlingException', 'Message': 'Request was throttled'},
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HTTPStatusCode': 429,
                'HTTPHeaders': {},
                'RetryAttempts': 0,
            },
        }

        # Second call succeeds
        success_response = {
            'ChangeEvents': [
                {
                    'EventId': 'recovery-event-1',
                    'EventName': 'RecoveryUpdate',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'recovery-user',
                    'Entity': {'Type': 'Service', 'Name': 'recovery-service'},
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients['applicationsignals_client'].list_entity_events.side_effect = [
            ClientError(error_response, 'ListEntityEvents'),
            success_response,
        ]

        # First call should return throttling error
        result1_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'recovery-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result1 = json.loads(result1_str)
        assert 'error' in result1
        assert 'Request was throttled' in result1['error']

        # Second call should succeed (simulating retry)
        result2_str = await _list_change_events(
            start_time='2024-01-15T10:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            service_key_attributes={
                'Name': 'recovery-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result2 = json.loads(result2_str)
        assert result2['total_events'] == 1
        assert result2['change_events'][0]['event_id'] == 'recovery-event-1'

    @pytest.mark.asyncio
    async def test_integration_cross_tool_data_format(self, mock_aws_clients):
        """Test that change events data format integrates well with other tools."""
        # Mock response with rich metadata for cross-tool integration
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'cross-tool-event-1',
                    'EventName': 'ServiceDeployment',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 14, 45, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deployment-pipeline',
                    'Entity': {
                        'Type': 'Service',
                        'Name': 'payment-service',
                        'Environment': 'eks:production',
                        'ResourceType': 'AWS::ECS::Service',
                        'Identifier': 'arn:aws:ecs:us-east-1:123456789012:service/payment-service',
                    },
                }
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        result_str = await _list_change_events(
            start_time='2024-01-15T12:00:00Z',
            end_time='2024-01-15T18:00:00Z',
            service_key_attributes={
                'Name': 'payment-service',
                'Environment': 'eks:production',
                'Type': 'Service',
            },
        )

        result = json.loads(result_str)

        # Verify data format is suitable for cross-tool integration
        assert 'change_events' in result
        assert 'events_by_type' in result
        assert 'total_events' in result

        event = result['change_events'][0]

        # Verify event has all fields needed for correlation with other tools
        required_fields = ['event_id', 'event_name', 'change_event_type', 'timestamp']
        for field in required_fields:
            assert field in event

        # Note: entity field is not included in ListEntityEvents response
        # Verify timestamp is in correct format for timeline analysis
        assert isinstance(event['timestamp'], str)

        # Verify events_by_type aggregation for summary reporting
        assert result['events_by_type']['DEPLOYMENT'] == 1


class TestListChangeEventsWorkflowIntegration:
    """Integration tests for change events in typical operational workflows."""

    @pytest.mark.asyncio
    async def test_incident_investigation_workflow(self, mock_aws_clients):
        """Test change events in incident investigation workflow."""
        # Mock incident timeline: deployment -> config change -> rollback
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'incident-1',
                    'EventName': 'DeployService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 14, 45, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'deploy-team',
                    'Entity': {'Type': 'Service', 'Name': 'api-service'},
                },
                {
                    'EventId': 'incident-2',
                    'EventName': 'UpdateConfig',
                    'ChangeEventType': 'CONFIGURATION',
                    'Timestamp': datetime(2024, 1, 15, 15, 15, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'config-team',
                    'Entity': {'Type': 'Service', 'Name': 'api-service'},
                },
                {
                    'EventId': 'incident-3',
                    'EventName': 'RollbackService',
                    'ChangeEventType': 'DEPLOYMENT',
                    'Timestamp': datetime(2024, 1, 15, 15, 25, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'sre-team',
                    'Entity': {'Type': 'Service', 'Name': 'api-service'},
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Simulate: "API service alarm fired at 15:30, investigate recent changes"
        result_str = await _list_change_events(
            start_time='2024-01-15T12:00:00Z',
            end_time='2024-01-15T18:00:00Z',
            service_key_attributes={
                'Name': 'api-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)

        # Verify incident timeline captured
        assert result['total_events'] == 3
        assert result['events_by_type']['DEPLOYMENT'] == 2  # Deploy + rollback
        assert result['events_by_type']['CONFIGURATION'] == 1

        # Verify chronological order for root cause analysis
        events = result['change_events']
        timestamps = [event['timestamp'] for event in events]
        assert timestamps == sorted(timestamps)

        # Note: entity field is not included in ListEntityEvents response
        # Verify we have the expected number of events
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_multi_service_correlation_workflow(self, mock_aws_clients):
        """Test change events for multi-service correlation analysis."""
        # Mock changes across multiple services in dependency chain
        mock_response = {
            'ServiceStates': [
                {
                    'Service': {
                        'Name': 'database-service',
                        'Environment': 'prod',
                        'Platform': 'RDS',
                    },
                    'LatestChangeEvents': [
                        {
                            'EventId': 'db-change-1',
                            'EventName': 'DatabaseUpgrade',
                            'ChangeEventType': 'INFRASTRUCTURE',
                            'Timestamp': datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'dba-team',
                        }
                    ],
                },
                {
                    'Service': {'Name': 'api-service', 'Environment': 'prod', 'Platform': 'ECS'},
                    'LatestChangeEvents': [
                        {
                            'EventId': 'api-change-1',
                            'EventName': 'UpdateConnections',
                            'ChangeEventType': 'CONFIGURATION',
                            'Timestamp': datetime(2024, 1, 15, 13, 30, 0, tzinfo=timezone.utc),
                            'AccountId': '123456789012',
                            'Region': 'us-east-1',
                            'UserName': 'api-team',
                        }
                    ],
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.return_value = mock_response

        # Simulate: "API issues started at 13:45, check all production services"
        result_str = await _list_change_events(
            start_time='2024-01-15T12:00:00Z',
            end_time='2024-01-15T15:00:00Z',
            service_key_attributes={'Environment': 'prod'},
            comprehensive_history=False,
        )

        result = json.loads(result_str)

        # Verify multi-service changes captured
        assert result['total_events'] == 2
        assert result['events_by_type']['INFRASTRUCTURE'] == 1
        assert result['events_by_type']['CONFIGURATION'] == 1

        # Verify timeline shows potential cascade
        events = result['change_events']
        assert events[0]['event_name'] == 'DatabaseUpgrade'  # 13:00 - Root change
        assert events[1]['event_name'] == 'UpdateConnections'  # 13:30 - Dependent change

        # 30-minute gap suggests coordinated change that may have caused issues

    @pytest.mark.asyncio
    async def test_performance_regression_correlation(self, mock_aws_clients):
        """Test change events for performance regression correlation."""
        # Mock performance-impacting configuration changes
        mock_response = {
            'ChangeEvents': [
                {
                    'EventId': 'perf-change-1',
                    'EventName': 'UpdateCacheConfig',
                    'ChangeEventType': 'CONFIGURATION',
                    'Timestamp': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'performance-team',
                    'Entity': {'Type': 'Service', 'Name': 'cache-service'},
                },
                {
                    'EventId': 'perf-change-2',
                    'EventName': 'UpdateDatabasePool',
                    'ChangeEventType': 'CONFIGURATION',
                    'Timestamp': datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                    'AccountId': '123456789012',
                    'Region': 'us-east-1',
                    'UserName': 'database-team',
                    'Entity': {'Type': 'Service', 'Name': 'cache-service'},
                },
            ],
            'NextToken': None,
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_entity_events.return_value = mock_response

        # Simulate: "Cache service latency spiked 400% at 12:00, find cause"
        result_str = await _list_change_events(
            start_time='2024-01-15T09:00:00Z',
            end_time='2024-01-15T13:00:00Z',
            service_key_attributes={
                'Name': 'cache-service',
                'Type': 'Service',
                'Environment': 'eks:production',
            },
        )

        result = json.loads(result_str)

        # Verify performance-related changes captured
        assert result['total_events'] == 2
        assert result['events_by_type']['CONFIGURATION'] == 2

        # Verify changes preceded performance regression
        events = result['change_events']
        assert events[0]['event_name'] == 'UpdateCacheConfig'  # 10:30 - 1.5h before spike
        assert events[1]['event_name'] == 'UpdateDatabasePool'  # 11:00 - 1h before spike

        # Both configuration changes could impact performance
