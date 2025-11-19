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

"""Tests for audit_utils module."""

import os
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.audit_utils import (
    _fetch_instrumented_services_with_pagination,
    _filter_instrumented_services,
    execute_audit_api,
    expand_service_operation_wildcard_patterns,
    expand_service_wildcard_patterns,
    expand_slo_wildcard_patterns,
    parse_auditors,
)
from unittest.mock import Mock, mock_open, patch


class TestExecuteAuditApi:
    """Test execute_audit_api function."""

    @pytest.fixture
    def mock_applicationsignals_client(self):
        """Mock applicationsignals client."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.applicationsignals_client'
        ) as mock_client:
            yield mock_client

    @pytest.fixture
    def sample_input_obj(self):
        """Sample input object for testing."""
        return {
            'StartTime': 1640995200,  # 2022-01-01 00:00:00 UTC
            'EndTime': 1641081600,  # 2022-01-02 00:00:00 UTC
            'AuditTargets': [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
                }
            ],
            'Auditors': ['slo', 'operation_metric'],
        }

    @pytest.mark.asyncio
    async def test_execute_audit_api_success_single_batch(
        self, mock_applicationsignals_client, sample_input_obj
    ):
        """Test successful API execution with single batch."""
        mock_response = {
            'AuditFindings': [
                {'FindingId': 'finding-1', 'Severity': 'CRITICAL', 'Description': 'Test finding'}
            ]
        }
        mock_applicationsignals_client.list_audit_findings.return_value = mock_response

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')

        assert 'Test Banner' in result
        assert 'finding-1' in result
        assert 'CRITICAL' in result
        mock_applicationsignals_client.list_audit_findings.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_audit_api_multiple_batches(self, mock_applicationsignals_client):
        """Test API execution with multiple batches."""
        # Create input with more than 5 targets to trigger batching
        input_obj = {
            'StartTime': 1640995200,
            'EndTime': 1641081600,
            'AuditTargets': [
                {'Type': 'service', 'Data': {'Service': {'Name': f'service-{i}'}}}
                for i in range(7)  # 7 targets = 2 batches
            ],
        }

        mock_responses = [
            {'AuditFindings': [{'FindingId': 'finding-1'}]},
            {'AuditFindings': [{'FindingId': 'finding-2'}]},
        ]
        mock_applicationsignals_client.list_audit_findings.side_effect = mock_responses

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(input_obj, 'us-east-1', 'Test Banner\n')

        assert 'finding-1' in result
        assert 'finding-2' in result
        # The actual implementation returns aggregated AuditFindings, not TotalBatches
        assert '"AuditFindings"' in result
        assert mock_applicationsignals_client.list_audit_findings.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_audit_api_no_findings(
        self, mock_applicationsignals_client, sample_input_obj
    ):
        """Test API execution with no findings."""
        mock_response = {'AuditFindings': []}
        mock_applicationsignals_client.list_audit_findings.return_value = mock_response

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')

        assert 'Test Banner' in result
        # The actual implementation returns empty AuditFindings array, not TotalFindingsCount
        assert '"AuditFindings": []' in result

    @pytest.mark.asyncio
    async def test_execute_audit_api_error_handling(
        self, mock_applicationsignals_client, sample_input_obj
    ):
        """Test API execution with error handling."""
        mock_applicationsignals_client.list_audit_findings.side_effect = Exception('API Error')

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')

        assert 'API call failed: API Error' in result
        assert 'ListAuditFindingsErrors' in result

    @pytest.mark.asyncio
    async def test_execute_audit_api_log_path_handling(
        self, mock_applicationsignals_client, sample_input_obj
    ):
        """Test log path handling with different environment variables."""
        mock_response = {'AuditFindings': []}
        mock_applicationsignals_client.list_audit_findings.return_value = mock_response

        # Test with custom log path
        with patch.dict(os.environ, {'AUDITOR_LOG_PATH': '/custom/path'}):
            with patch('os.makedirs') as mock_makedirs:
                with patch('builtins.open', mock_open()):
                    await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')
                    mock_makedirs.assert_called()

    @pytest.mark.asyncio
    async def test_execute_audit_api_batch_errors_aggregation(
        self, mock_applicationsignals_client
    ):
        """Test that failed batch errors are properly aggregated in ListAuditFindingsErorrs."""
        # Create input with multiple batches where some fail
        input_obj = {
            'StartTime': 1640995200,
            'EndTime': 1641081600,
            'AuditTargets': [
                {'Type': 'service', 'Data': {'Service': {'Name': f'service-{i}'}}}
                for i in range(7)  # 7 targets = 2 batches
            ],
        }

        # First batch succeeds, second batch fails
        mock_applicationsignals_client.list_audit_findings.side_effect = [
            {'AuditFindings': [{'FindingId': 'finding-1'}]},
            Exception('API Error for batch 2'),
        ]

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(input_obj, 'us-east-1', 'Test Banner\n')

        # Verify ListAuditFindingsErrors is present and contains error details
        assert 'ListAuditFindingsErrors' in result
        assert 'API call failed: API Error for batch 2' in result
        assert 'finding-1' in result  # Successful batch findings still included

    @pytest.mark.asyncio
    async def test_execute_audit_api_log_path_exception(
        self, mock_applicationsignals_client, sample_input_obj
    ):
        """Test log path handling when directory creation fails."""
        mock_response = {'AuditFindings': []}
        mock_applicationsignals_client.list_audit_findings.return_value = mock_response

        with patch.dict(os.environ, {'AUDITOR_LOG_PATH': '/invalid/path'}):
            # Mock os.makedirs to fail on first call but succeed on second (temp dir)
            makedirs_calls = []

            def mock_makedirs(*args, **kwargs):
                makedirs_calls.append(args)
                if len(makedirs_calls) == 1:
                    raise Exception('Permission denied')
                # Second call (temp dir) succeeds
                return None

            with patch('os.makedirs', side_effect=mock_makedirs):
                with patch('tempfile.gettempdir', return_value='/tmp'):
                    with patch('builtins.open', mock_open()):
                        result = await execute_audit_api(
                            sample_input_obj, 'us-east-1', 'Test Banner\n'
                        )
                        # Should fallback to temp directory
                        assert result is not None
                        assert len(makedirs_calls) == 2  # First failed, second succeeded


class TestParseAuditors:
    """Test parse_auditors function."""

    def test_parse_auditors_none_default(self):
        """Test parsing None with default auditors."""
        result = parse_auditors(None, ['slo', 'operation_metric'])
        assert result == ['slo', 'operation_metric']

    def test_parse_auditors_none_root_cause_prompt(self):
        """Test parsing None with root cause in user prompt."""
        with patch.dict(os.environ, {'MCP_USER_PROMPT': 'Please do root cause analysis'}):
            result = parse_auditors(None, ['slo'])
            assert result == []  # Empty list means all auditors

    def test_parse_auditors_all_string(self):
        """Test parsing 'all' string."""
        result = parse_auditors('all', ['slo'])
        assert result == []  # Empty list means all auditors

    def test_parse_auditors_comma_separated(self):
        """Test parsing comma-separated auditors."""
        result = parse_auditors('slo,trace,log', [])
        assert result == ['slo', 'trace', 'log']

    def test_parse_auditors_with_spaces(self):
        """Test parsing auditors with spaces."""
        result = parse_auditors('slo, trace , log', [])
        assert result == ['slo', 'trace', 'log']

    def test_parse_auditors_invalid_auditor(self):
        """Test parsing with invalid auditor."""
        with pytest.raises(ValueError, match='Invalid auditor'):
            parse_auditors('slo,invalid_auditor', [])

    def test_parse_auditors_pydantic_field_object(self):
        """Test parsing Pydantic Field object."""
        mock_field = Mock()
        mock_field.default = 'slo,trace'
        mock_field.description = 'Test field'

        result = parse_auditors(mock_field, [])
        assert result == ['slo', 'trace']

    def test_parse_auditors_empty_string(self):
        """Test parsing empty string."""
        result = parse_auditors('', ['default'])
        assert result == []

    def test_parse_auditors_valid_auditors(self):
        """Test all valid auditors."""
        valid_auditors = (
            'slo,operation_metric,trace,log,dependency_metric,top_contributor,service_quota'
        )
        result = parse_auditors(valid_auditors, [])
        expected = [
            'slo',
            'operation_metric',
            'trace',
            'log',
            'dependency_metric',
            'top_contributor',
            'service_quota',
        ]
        assert result == expected


class TestFetchInstrumentedServicesWithPagination:
    """Test _fetch_instrumented_services_with_pagination function."""

    @pytest.fixture
    def mock_applicationsignals_client(self):
        """Mock applicationsignals client."""
        return Mock()

    def test_fetch_instrumented_services_basic_functionality(self, mock_applicationsignals_client):
        """Test basic functionality with instrumented services."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'instrumented-service-1',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'instrumented-service-2',
                        'Type': 'Service',
                        'Environment': 'staging',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                },
            ]
        }

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        assert len(instrumented_services) == 2
        assert next_token is None
        assert len(all_service_names) == 2
        assert 'instrumented-service-1' in all_service_names
        assert 'instrumented-service-2' in all_service_names
        assert filtering_stats['total_services'] == 2
        assert filtering_stats['instrumented_services'] == 2
        assert filtering_stats['filtered_out'] == 0

    def test_fetch_instrumented_services_empty_response(self, mock_applicationsignals_client):
        """Test behavior with empty service response."""
        mock_applicationsignals_client.list_services.return_value = {'ServiceSummaries': []}

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        assert len(instrumented_services) == 0
        assert next_token is None
        assert len(all_service_names) == 0
        assert filtering_stats['total_services'] == 0
        assert filtering_stats['instrumented_services'] == 0
        assert filtering_stats['filtered_out'] == 0

    def test_fetch_instrumented_services_all_filtered_out(self, mock_applicationsignals_client):
        """Test behavior when all services are filtered out."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'uninstrumented-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'aws-native-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
                },
            ]
        }

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        assert len(instrumented_services) == 0
        assert next_token is None
        assert len(all_service_names) == 2
        assert 'uninstrumented-service' in all_service_names
        assert 'aws-native-service' in all_service_names
        assert filtering_stats['total_services'] == 2
        assert filtering_stats['instrumented_services'] == 0
        assert filtering_stats['filtered_out'] == 2

    def test_fetch_instrumented_services_pagination_continuation(
        self, mock_applicationsignals_client
    ):
        """Test automatic pagination continuation when no instrumented services in first batch."""
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    }
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    }
                ]
            },
        ]

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        assert len(instrumented_services) == 1
        assert instrumented_services[0]['KeyAttributes']['Name'] == 'instrumented-service'
        assert next_token is None
        assert len(all_service_names) == 2
        assert 'uninstrumented-service' in all_service_names
        assert 'instrumented-service' in all_service_names
        assert filtering_stats['total_services'] == 2
        assert filtering_stats['instrumented_services'] == 1
        assert filtering_stats['filtered_out'] == 1

        # Verify both API calls were made
        assert mock_applicationsignals_client.list_services.call_count == 2

    def test_fetch_instrumented_services_pagination_with_next_token_stops(
        self, mock_applicationsignals_client
    ):
        """Test pagination stops and returns NextToken when instrumented services found."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'instrumented-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                }
            ],
            'NextToken': 'next-token-456',
        }

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        assert len(instrumented_services) == 1
        assert next_token == 'next-token-456'
        assert len(all_service_names) == 1
        assert filtering_stats['total_services'] == 1
        assert filtering_stats['instrumented_services'] == 1
        assert filtering_stats['filtered_out'] == 0

        # Should only make one API call since instrumented services were found
        assert mock_applicationsignals_client.list_services.call_count == 1

    def test_fetch_instrumented_services_exhausts_pagination(self, mock_applicationsignals_client):
        """Test behavior when pagination is exhausted without finding instrumented services."""
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-1',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    }
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-2',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
                    }
                ],
                # No NextToken - end of pagination
            },
        ]

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        assert len(instrumented_services) == 0
        assert next_token is None
        assert len(all_service_names) == 2
        assert filtering_stats['total_services'] == 2
        assert filtering_stats['instrumented_services'] == 0
        assert filtering_stats['filtered_out'] == 2

        # Should make both API calls
        assert mock_applicationsignals_client.list_services.call_count == 2

    def test_fetch_instrumented_services_with_input_next_token(
        self, mock_applicationsignals_client
    ):
        """Test function accepts and passes through next_token input parameter."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'instrumented-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                }
            ]
        }

        _fetch_instrumented_services_with_pagination(
            1640995200,
            1641081600,
            next_token='input-token-789',
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify that input NextToken was passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['NextToken'] == 'input-token-789'

    def test_fetch_instrumented_services_max_results_parameter(
        self, mock_applicationsignals_client
    ):
        """Test that max_results parameter is passed to list_services API."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'instrumented-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                }
            ]
        }

        _fetch_instrumented_services_with_pagination(
            1640995200,
            1641081600,
            max_results=20,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify that MaxResults was passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['MaxResults'] == 20

    def test_fetch_instrumented_services_time_parameters(self, mock_applicationsignals_client):
        """Test that start and end time parameters are correctly converted and passed."""
        mock_applicationsignals_client.list_services.return_value = {'ServiceSummaries': []}

        start_time = 1640995200  # 2022-01-01 00:00:00 UTC
        end_time = 1641081600  # 2022-01-02 00:00:00 UTC

        _fetch_instrumented_services_with_pagination(
            start_time, end_time, applicationsignals_client=mock_applicationsignals_client
        )

        # Verify that StartTime and EndTime were converted and passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['StartTime'].timestamp() == start_time
        assert call_args['EndTime'].timestamp() == end_time

    def test_fetch_instrumented_services_statistics_accuracy_across_batches(
        self, mock_applicationsignals_client
    ):
        """Test that filtering statistics are accurately accumulated across multiple batches."""
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-1',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    },
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-2',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
                    },
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service-1',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    },
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service-2',
                            'Type': 'Service',
                            'Environment': 'staging',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    },
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-3',
                            'Type': 'Service',
                            'Environment': 'dev',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    },
                ],
                # No NextToken - end of pagination
            },
        ]

        instrumented_services, next_token, all_service_names, filtering_stats = (
            _fetch_instrumented_services_with_pagination(
                1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
            )
        )

        # Verify accurate statistics across both batches
        assert filtering_stats['total_services'] == 5  # 2 + 3 from both batches
        assert filtering_stats['instrumented_services'] == 2  # Only from second batch
        assert filtering_stats['filtered_out'] == 3  # 2 from first + 1 from second

        assert len(instrumented_services) == 2
        assert len(all_service_names) == 5
        assert next_token is None

    @patch('awslabs.cloudwatch_applicationsignals_mcp_server.audit_utils.logger')
    def test_fetch_instrumented_services_logging(
        self, mock_logger, mock_applicationsignals_client
    ):
        """Test that function logs appropriate messages during pagination."""
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    }
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    }
                ]
            },
        ]

        _fetch_instrumented_services_with_pagination(
            1640995200, 1641081600, applicationsignals_client=mock_applicationsignals_client
        )

        # Verify logging calls
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Should log fetching batch
        assert any('Fetching batch' in call for call in info_calls)

        # Should log batch results
        assert any('Fetch instrumented services batch results:' in call for call in info_calls)

        # Should log cumulative results
        assert any('Fetch instrumented services cumulative:' in call for call in info_calls)

        # Should log when instrumented services are found
        assert any(
            'Found' in call and 'instrumented services, proceeding with expansion' in call
            for call in info_calls
        )


class TestFilterInstrumentedServices:
    """Test _filter_instrumented_services function."""

    def test_filter_instrumented_services_all_instrumented(self):
        """Test filtering when all services are instrumented."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'payment-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED', 'Platform': 'EKS'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'user-service',
                    'Type': 'Service',
                    'Environment': 'staging',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED', 'Platform': 'Lambda'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        assert len(result) == 2
        service_names = [s['KeyAttributes']['Name'] for s in result]
        assert 'payment-service' in service_names
        assert 'user-service' in service_names

    def test_filter_instrumented_services_mixed_instrumentation(self):
        """Test filtering with mix of instrumented and uninstrumented services."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'instrumented-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED', 'Platform': 'EKS'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'uninstrumented-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED', 'Platform': 'EKS'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'aws-native-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE', 'Platform': 'Lambda'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'instrumented-service'

    def test_filter_instrumented_services_no_instrumentation_type(self):
        """Test filtering when services have no InstrumentationType."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-without-instrumentation',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'Platform': 'EKS'}  # No InstrumentationType
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'service-with-instrumentation',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED', 'Platform': 'EKS'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Services without InstrumentationType should be considered instrumented
        assert len(result) == 2
        service_names = [s['KeyAttributes']['Name'] for s in result]
        assert 'service-without-instrumentation' in service_names
        assert 'service-with-instrumentation' in service_names

    def test_filter_instrumented_services_empty_attribute_maps(self):
        """Test filtering when services have empty AttributeMaps."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-empty-attrs',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [],  # Empty list
            },
            {
                'KeyAttributes': {
                    'Name': 'service-no-attrs',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                # No AttributeMaps key
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Services without AttributeMaps should be considered instrumented
        assert len(result) == 2
        service_names = [s['KeyAttributes']['Name'] for s in result]
        assert 'service-empty-attrs' in service_names
        assert 'service-no-attrs' in service_names

    def test_filter_instrumented_services_invalid_service_name(self):
        """Test filtering services with invalid names."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': '',  # Empty name
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'Unknown',  # Invalid name
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Type': 'Service',  # Missing Name
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'valid-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Only the valid service should be included
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'valid-service'

    def test_filter_instrumented_services_invalid_service_type(self):
        """Test filtering services with invalid types."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-wrong-type',
                    'Type': 'NotService',  # Wrong type
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'service-no-type',
                    'Environment': 'prod',
                    # Missing Type
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'valid-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Only the service with correct type should be included
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'valid-service'

    def test_filter_instrumented_services_multiple_attribute_maps(self):
        """Test filtering with multiple AttributeMaps per service."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-multiple-attrs',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'Platform': 'EKS'},  # No InstrumentationType
                    {'InstrumentationType': 'UNINSTRUMENTED'},  # This should filter it out
                    {'Other': 'value'},
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'service-instrumented-only',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'InstrumentationType': 'INSTRUMENTED'},  # This should keep it
                    {'Platform': 'EKS'},  # No InstrumentationType in this one
                ],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # First service should be filtered out due to UNINSTRUMENTED
        # Second service should be kept (only has INSTRUMENTED)
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'service-instrumented-only'

    def test_filter_instrumented_services_non_dict_attribute_map(self):
        """Test filtering with non-dict AttributeMap entries."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-with-non-dict-attr',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    'not-a-dict',  # Non-dict entry
                    {'InstrumentationType': 'INSTRUMENTED'},
                ],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Should handle non-dict entries gracefully and include the service
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'service-with-non-dict-attr'

    def test_filter_instrumented_services_empty_input(self):
        """Test filtering with empty input."""
        result = _filter_instrumented_services([])
        assert len(result) == 0

    def test_filter_instrumented_services_missing_key_attributes(self):
        """Test filtering services without KeyAttributes."""
        all_services = [
            {
                # Missing KeyAttributes
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {},  # Empty KeyAttributes
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'valid-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Only the service with valid KeyAttributes should be included
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'valid-service'

    @patch('awslabs.cloudwatch_applicationsignals_mcp_server.audit_utils.logger')
    def test_filter_instrumented_services_logging(self, mock_logger):
        """Test that filtering logs appropriate debug messages."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'instrumented-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'uninstrumented-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
            },
            {
                'KeyAttributes': {
                    'Name': '',  # Invalid name
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Verify logging calls
        assert mock_logger.debug.call_count >= 3  # At least one call per service
        assert mock_logger.info.call_count == 1  # Summary log

        # Check that the summary log includes correct counts
        summary_call = mock_logger.info.call_args[0][0]
        assert '1 instrumented out of 3 total services' in summary_call

        # Verify result
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'instrumented-service'

    def test_filter_instrumented_services_case_sensitivity(self):
        """Test that InstrumentationType filtering is case-sensitive."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-lowercase',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'InstrumentationType': 'uninstrumented'}  # lowercase
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'service-uppercase',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'InstrumentationType': 'UNINSTRUMENTED'}  # uppercase
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'service-mixed-case',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'InstrumentationType': 'Uninstrumented'}  # mixed case
                ],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Only exact case matches should be filtered out
        # lowercase and mixed case should be kept (not exact matches)
        assert len(result) == 2
        service_names = [s['KeyAttributes']['Name'] for s in result]
        assert 'service-lowercase' in service_names
        assert 'service-mixed-case' in service_names
        assert 'service-uppercase' not in service_names

    def test_filter_instrumented_services_aws_native_filtering(self):
        """Test that AWS_NATIVE services are filtered out."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'aws-native-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
            },
            {
                'KeyAttributes': {
                    'Name': 'regular-service',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # AWS_NATIVE should be filtered out
        assert len(result) == 1
        assert result[0]['KeyAttributes']['Name'] == 'regular-service'

    def test_filter_instrumented_services_break_on_first_uninstrumented(self):
        """Test that filtering breaks on first UNINSTRUMENTED/AWS_NATIVE found."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'service-with-mixed-attrs',
                    'Type': 'Service',
                    'Environment': 'prod',
                },
                'AttributeMaps': [
                    {'Platform': 'EKS'},  # No InstrumentationType
                    {'InstrumentationType': 'UNINSTRUMENTED'},  # This should cause filtering
                    {'InstrumentationType': 'INSTRUMENTED'},  # This should be ignored
                ],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Service should be filtered out due to UNINSTRUMENTED (breaks on first match)
        assert len(result) == 0

    def test_filter_instrumented_services_real_world_scenario(self):
        """Test filtering with realistic service data."""
        all_services = [
            {
                'KeyAttributes': {
                    'Name': 'payment-gateway',
                    'Type': 'Service',
                    'Environment': 'eks:production/default',
                },
                'AttributeMaps': [
                    {
                        'InstrumentationType': 'INSTRUMENTED',
                        'Platform': 'EKS',
                        'Application': 'payment-app',
                    }
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'user-auth-lambda',
                    'Type': 'Service',
                    'Environment': 'lambda',
                },
                'AttributeMaps': [
                    {
                        'InstrumentationType': 'INSTRUMENTED',
                        'Platform': 'Lambda',
                        'Runtime': 'nodejs18.x',
                    }
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'legacy-service',
                    'Type': 'Service',
                    'Environment': 'ec2:legacy',
                },
                'AttributeMaps': [
                    {
                        'InstrumentationType': 'UNINSTRUMENTED',
                        'Platform': 'EC2',
                        'Reason': 'Legacy system without instrumentation',
                    }
                ],
            },
            {
                'KeyAttributes': {
                    'Name': 'aws-s3-service',
                    'Type': 'Service',
                    'Environment': 'aws:s3',
                },
                'AttributeMaps': [
                    {
                        'InstrumentationType': 'AWS_NATIVE',
                        'Platform': 'AWS',
                        'ServiceType': 'S3',
                    }
                ],
            },
        ]

        result = _filter_instrumented_services(all_services)

        # Only instrumented services should remain
        assert len(result) == 2
        service_names = [s['KeyAttributes']['Name'] for s in result]
        assert 'payment-gateway' in service_names
        assert 'user-auth-lambda' in service_names
        assert 'legacy-service' not in service_names
        assert 'aws-s3-service' not in service_names


class TestExpandServiceWildcardPatterns:
    """Test expand_service_wildcard_patterns function."""

    @pytest.fixture
    def mock_applicationsignals_client(self):
        """Mock applicationsignals client."""
        mock_client = Mock()
        mock_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'payment-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'user-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'payment-gateway',
                        'Type': 'Service',
                        'Environment': 'staging',
                    }
                },
            ]
        }
        return mock_client

    def test_expand_service_wildcard_all_services(self, mock_applicationsignals_client):
        """Test expanding wildcard for all services."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 3
        service_names = [t['Data']['Service']['Name'] for t in expanded_targets]
        assert 'payment-service' in service_names
        assert 'user-service' in service_names
        assert 'payment-gateway' in service_names
        assert next_token is None  # No pagination token in mock response
        assert len(service_names_in_batch) == 3
        assert 'payment-service' in service_names_in_batch
        assert 'user-service' in service_names_in_batch
        assert 'payment-gateway' in service_names_in_batch

        # Check filtering stats
        assert filtering_stats['total_services'] == 3
        assert filtering_stats['instrumented_services'] == 3
        assert filtering_stats['filtered_out'] == 0

    def test_expand_service_wildcard_pattern_match(self, mock_applicationsignals_client):
        """Test expanding wildcard with pattern matching."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*payment*'}}}
        ]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 2
        service_names = [t['Data']['Service']['Name'] for t in expanded_targets]
        assert 'payment-service' in service_names
        assert 'payment-gateway' in service_names
        assert 'user-service' not in service_names
        assert next_token is None
        assert len(service_names_in_batch) == 3  # All services are collected in batch

        # Check filtering stats - shows all services from API call, not just pattern matches
        assert filtering_stats['total_services'] == 3
        assert filtering_stats['instrumented_services'] == 3
        assert filtering_stats['filtered_out'] == 0

    def test_expand_service_no_wildcard(self, mock_applicationsignals_client):
        """Test with no wildcard patterns."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': 'exact-service'}}}
        ]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Non-wildcard service names are treated as fuzzy matches, so the original target is kept
        # when no fuzzy matches are found
        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['Service']['Name'] == 'exact-service'
        assert next_token is None
        # API call is made for fuzzy matching, so service names are collected
        assert len(service_names_in_batch) == 3
        assert 'payment-service' in service_names_in_batch
        assert 'user-service' in service_names_in_batch
        assert 'payment-gateway' in service_names_in_batch

        # Check filtering stats - fuzzy matching still calls API and calculates stats
        assert filtering_stats['total_services'] == 3
        assert filtering_stats['instrumented_services'] == 3
        assert filtering_stats['filtered_out'] == 0

    def test_expand_service_shorthand_format(self, mock_applicationsignals_client):
        """Test expanding with shorthand service format."""
        targets = [{'Type': 'service', 'Service': '*payment*'}]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 2
        service_names = [t['Data']['Service']['Name'] for t in expanded_targets]
        assert 'payment-service' in service_names
        assert 'payment-gateway' in service_names
        assert next_token is None
        assert len(service_names_in_batch) == 3

        # Check filtering stats - shows all services from API call, not just pattern matches
        assert filtering_stats['total_services'] == 3
        assert filtering_stats['instrumented_services'] == 3
        assert filtering_stats['filtered_out'] == 0

    def test_expand_service_api_error(self, mock_applicationsignals_client):
        """Test handling API errors during expansion."""
        mock_applicationsignals_client.list_services.side_effect = Exception('API Error')

        targets = [{'Type': 'service', 'Data': {'Service': {'Name': '*payment*'}}}]

        with pytest.raises(ValueError, match='Failed to expand service wildcard patterns'):
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )

    def test_expand_service_non_service_targets(self, mock_applicationsignals_client):
        """Test that non-service targets pass through unchanged."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo'}}}]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Type'] == 'slo'
        assert next_token is None
        assert len(service_names_in_batch) == 0

        # Check filtering stats - no service targets means no filtering occurred
        assert filtering_stats['total_services'] == 0
        assert filtering_stats['instrumented_services'] == 0
        assert filtering_stats['filtered_out'] == 0

    @patch('awslabs.cloudwatch_applicationsignals_mcp_server.utils.calculate_name_similarity')
    def test_expand_service_fuzzy_matching(self, mock_similarity, mock_applicationsignals_client):
        """Test fuzzy matching for inexact service names."""
        mock_similarity.return_value = 90  # High similarity score

        targets = [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Name': 'payment-svc'  # Similar to 'payment-service'
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Should find fuzzy matches
        assert len(expanded_targets) >= 1
        mock_similarity.assert_called()
        assert next_token is None
        assert len(service_names_in_batch) == 3

    def test_expand_service_wildcard_with_pagination(self, mock_applicationsignals_client):
        """Test expanding wildcard patterns with pagination support."""
        # Mock response with NextToken
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'payment-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
            ],
            'NextToken': 'next-page-token-123',
        }

        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, next_token, service_names_in_batch, _ = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            max_results=1,
            applicationsignals_client=mock_applicationsignals_client,
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['Service']['Name'] == 'payment-service'
        assert next_token == 'next-page-token-123'
        assert len(service_names_in_batch) == 1
        assert 'payment-service' in service_names_in_batch

    def test_expand_service_wildcard_with_next_token_input(self, mock_applicationsignals_client):
        """Test expanding wildcard patterns with next_token input parameter."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, next_token, service_names_in_batch, _ = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            next_token='input-token-456',
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify that NextToken was passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['NextToken'] == 'input-token-456'

        assert len(expanded_targets) == 3
        assert next_token is None  # No NextToken in mock response
        assert len(service_names_in_batch) == 3

    def test_expand_service_wildcard_max_results_parameter(self, mock_applicationsignals_client):
        """Test that max_results parameter is passed to list_services API."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            max_results=10,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify that MaxResults was passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['MaxResults'] == 10

    def test_expand_service_wildcard_service_names_collection(
        self, mock_applicationsignals_client
    ):
        """Test that all service names are collected in batch regardless of filtering."""
        # Mock response with services that don't match the pattern
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'unrelated-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'another-service',
                        'Type': 'Service',
                        'Environment': 'staging',
                    }
                },
            ]
        }

        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*payment*'}}}
        ]

        expanded_targets, _, service_names_in_batch, _ = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # No services match the *payment* pattern
        assert len(expanded_targets) == 0

        # But all service names should still be collected in the batch
        assert len(service_names_in_batch) == 2
        assert 'unrelated-service' in service_names_in_batch
        assert 'another-service' in service_names_in_batch

    def test_expand_service_wildcard_filters_unknown_services(
        self, mock_applicationsignals_client
    ):
        """Test that services with Unknown names or non-Service types are filtered out."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'Unknown',  # Should be filtered out
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'valid-service',
                        'Type': 'NotService',  # Should be filtered out
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'good-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
            ]
        }

        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, _, service_names_in_batch, _ = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Only the good service should be included in expanded targets
        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['Service']['Name'] == 'good-service'

        # But all service names should still be collected in the batch (including filtered ones)
        assert len(service_names_in_batch) == 3
        assert 'Unknown' in service_names_in_batch
        assert 'valid-service' in service_names_in_batch
        assert 'good-service' in service_names_in_batch

    def test_expand_service_wildcard_auto_continue_to_next_batch(
        self, mock_applicationsignals_client
    ):
        """Test automatic continuation when first batch has no instrumented services."""
        # Mock two API calls: first with no instrumented services, second with instrumented services
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    }
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    }
                ]
            },
        ]

        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should find the instrumented service from the second batch
        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['Service']['Name'] == 'instrumented-service'
        assert next_token is None  # No more pages after second batch

        # Should collect service names from both batches
        assert len(service_names_in_batch) == 2
        assert 'uninstrumented-service' in service_names_in_batch
        assert 'instrumented-service' in service_names_in_batch

        # Check filtering stats across both batches
        assert filtering_stats['total_services'] == 2
        assert filtering_stats['instrumented_services'] == 1
        assert filtering_stats['filtered_out'] == 1

        # Verify both API calls were made
        assert mock_applicationsignals_client.list_services.call_count == 2

    def test_expand_service_wildcard_no_instrumented_services_anywhere(
        self, mock_applicationsignals_client
    ):
        """Test behavior when no instrumented services exist across all pages."""
        # Mock multiple API calls with no instrumented services and eventual end of pagination
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-1',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    }
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'aws-native-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
                    }
                ],
                # No NextToken - end of pagination
            },
        ]

        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should find no instrumented services
        assert len(expanded_targets) == 0
        assert next_token is None

        # Should collect service names from both batches
        assert len(service_names_in_batch) == 2
        assert 'uninstrumented-service-1' in service_names_in_batch
        assert 'aws-native-service' in service_names_in_batch

        # Check filtering stats - all services filtered out
        assert filtering_stats['total_services'] == 2
        assert filtering_stats['instrumented_services'] == 0
        assert filtering_stats['filtered_out'] == 2

        # Verify both API calls were made
        assert mock_applicationsignals_client.list_services.call_count == 2

    def test_expand_service_wildcard_filtering_stats_across_batches(
        self, mock_applicationsignals_client
    ):
        """Test that filtering statistics are properly accumulated across multiple batches."""
        # Mock three API calls with mixed instrumentation types
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service-1',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    },
                    {
                        'KeyAttributes': {
                            'Name': 'aws-native-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
                    },
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service-1',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    },
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service-2',
                            'Type': 'Service',
                            'Environment': 'staging',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    },
                ],
                # No NextToken - end of pagination
            },
        ]

        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expanded_targets, next_token, service_names_in_batch, filtering_stats = (
            expand_service_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should find the instrumented services from the second batch
        assert len(expanded_targets) == 2
        service_names = [t['Data']['Service']['Name'] for t in expanded_targets]
        assert 'instrumented-service-1' in service_names
        assert 'instrumented-service-2' in service_names
        assert next_token is None

        # Should collect service names from both batches
        assert len(service_names_in_batch) == 4
        assert 'uninstrumented-service-1' in service_names_in_batch
        assert 'aws-native-service' in service_names_in_batch
        assert 'instrumented-service-1' in service_names_in_batch
        assert 'instrumented-service-2' in service_names_in_batch

        # Check cumulative filtering stats across both batches
        assert filtering_stats['total_services'] == 4
        assert filtering_stats['instrumented_services'] == 2
        assert filtering_stats['filtered_out'] == 2

        # Verify both API calls were made
        assert mock_applicationsignals_client.list_services.call_count == 2

    @patch('awslabs.cloudwatch_applicationsignals_mcp_server.audit_utils.logger')
    def test_expand_service_wildcard_pagination_logging(
        self, mock_logger, mock_applicationsignals_client
    ):
        """Test that pagination loop logs appropriate messages."""
        # Mock two API calls: first with no instrumented services, second with instrumented services
        mock_applicationsignals_client.list_services.side_effect = [
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'uninstrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                    }
                ],
                'NextToken': 'token-123',
            },
            {
                'ServiceSummaries': [
                    {
                        'KeyAttributes': {
                            'Name': 'instrumented-service',
                            'Type': 'Service',
                            'Environment': 'prod',
                        },
                        'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                    }
                ]
            },
        ]

        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify logging calls for pagination behavior
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Should log fetching services batch (updated message format)
        assert any('Fetching batch' in call for call in info_calls)

        # Should log batch results (updated message format)
        assert any('Fetch instrumented services batch results:' in call for call in info_calls)

        # Should log cumulative results (updated message format)
        assert any('Fetch instrumented services cumulative:' in call for call in info_calls)

        # Should log continuation to next page
        assert any(
            'No instrumented services in this batch, continuing to next page' in call
            for call in info_calls
        )

        # Should log when instrumented services are found
        assert any(
            'Found' in call and 'instrumented services, proceeding with expansion' in call
            for call in info_calls
        )


class TestExpandSloWildcardPatterns:
    """Test expand_slo_wildcard_patterns function."""

    @pytest.fixture
    def mock_applicationsignals_client(self):
        """Mock applicationsignals client."""
        mock_client = Mock()
        mock_client.list_service_level_objectives.return_value = {
            'SloSummaries': [
                {
                    'Name': 'payment-latency-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-latency-slo',
                },
                {
                    'Name': 'user-availability-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/user-availability-slo',
                },
                {
                    'Name': 'payment-availability-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-availability-slo',
                },
            ]
        }
        return mock_client

    def test_expand_slo_wildcard_all_slos(self, mock_applicationsignals_client):
        """Test expanding wildcard for all SLOs."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets, applicationsignals_client=mock_applicationsignals_client
        )

        assert len(expanded_targets) == 3
        slo_names = [t['Data']['Slo']['SloName'] for t in expanded_targets]
        assert 'payment-latency-slo' in slo_names
        assert 'user-availability-slo' in slo_names
        assert 'payment-availability-slo' in slo_names
        assert next_token is None
        assert len(slo_names_in_batch) == 3

    def test_expand_slo_wildcard_pattern_match(self, mock_applicationsignals_client):
        """Test expanding SLO wildcard with pattern matching."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*payment*'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets, applicationsignals_client=mock_applicationsignals_client
        )

        assert len(expanded_targets) == 2
        slo_names = [t['Data']['Slo']['SloName'] for t in expanded_targets]
        assert 'payment-latency-slo' in slo_names
        assert 'payment-availability-slo' in slo_names
        assert 'user-availability-slo' not in slo_names
        assert next_token is None
        assert len(slo_names_in_batch) == 3

    def test_expand_slo_no_wildcard(self, mock_applicationsignals_client):
        """Test with no SLO wildcard patterns."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'exact-slo'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets, applicationsignals_client=mock_applicationsignals_client
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['Slo']['SloName'] == 'exact-slo'
        assert next_token is None
        assert len(slo_names_in_batch) == 0  # No API call made for non-wildcard

    def test_expand_slo_invalid_format_string(self, mock_applicationsignals_client):
        """Test handling invalid SLO format (string instead of dict)."""
        targets = [{'Type': 'slo', 'Data': {'Slo': 'invalid-string-format'}}]

        with pytest.raises(ValueError, match='Invalid SLO target format'):
            expand_slo_wildcard_patterns(targets, mock_applicationsignals_client)

    def test_expand_slo_invalid_format_other_type(self, mock_applicationsignals_client):
        """Test handling invalid SLO format (other types)."""
        targets = [
            {
                'Type': 'slo',
                'Data': {
                    'Slo': 123  # Invalid type
                },
            }
        ]

        with pytest.raises(ValueError, match='Invalid SLO target format'):
            expand_slo_wildcard_patterns(targets, mock_applicationsignals_client)

    def test_expand_slo_api_error(self, mock_applicationsignals_client):
        """Test handling API errors during SLO expansion."""
        mock_applicationsignals_client.list_service_level_objectives.side_effect = Exception(
            'API Error'
        )

        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*payment*'}}}]

        with pytest.raises(ValueError, match='Failed to expand SLO wildcard patterns'):
            expand_slo_wildcard_patterns(targets, mock_applicationsignals_client)

    def test_expand_slo_wildcard_with_pagination(self, mock_applicationsignals_client):
        """Test expanding SLO wildcard patterns with pagination support."""
        # Mock response with NextToken
        mock_applicationsignals_client.list_service_level_objectives.return_value = {
            'SloSummaries': [
                {
                    'Name': 'payment-latency-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-latency-slo',
                },
            ],
            'NextToken': 'next-slo-token-123',
        }

        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets, max_results=1, applicationsignals_client=mock_applicationsignals_client
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['Slo']['SloName'] == 'payment-latency-slo'
        assert next_token == 'next-slo-token-123'
        assert len(slo_names_in_batch) == 1
        assert 'payment-latency-slo' in slo_names_in_batch

    def test_expand_slo_wildcard_with_next_token_input(self, mock_applicationsignals_client):
        """Test expanding SLO wildcard patterns with next_token input parameter."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets,
            next_token='input-slo-token-456',
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify that NextToken was passed to list_service_level_objectives
        mock_applicationsignals_client.list_service_level_objectives.assert_called_once()
        call_args = mock_applicationsignals_client.list_service_level_objectives.call_args[1]
        assert call_args['NextToken'] == 'input-slo-token-456'

        assert len(expanded_targets) == 3
        assert next_token is None  # No NextToken in mock response
        assert len(slo_names_in_batch) == 3

    def test_expand_slo_wildcard_max_results_parameter(self, mock_applicationsignals_client):
        """Test that max_results parameter is passed to list_service_level_objectives API."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        expand_slo_wildcard_patterns(
            targets, max_results=10, applicationsignals_client=mock_applicationsignals_client
        )

        # Verify that MaxResults was passed to list_service_level_objectives
        mock_applicationsignals_client.list_service_level_objectives.assert_called_once()
        call_args = mock_applicationsignals_client.list_service_level_objectives.call_args[1]
        assert call_args['MaxResults'] == 10

    def test_expand_slo_wildcard_slo_names_collection(self, mock_applicationsignals_client):
        """Test that all SLO names are collected in batch regardless of filtering."""
        # Mock response with SLOs that don't match the pattern
        mock_applicationsignals_client.list_service_level_objectives.return_value = {
            'SloSummaries': [
                {
                    'Name': 'unrelated-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/unrelated-slo',
                },
                {
                    'Name': 'another-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/another-slo',
                },
            ]
        }

        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*payment*'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets, applicationsignals_client=mock_applicationsignals_client
        )

        # No SLOs match the *payment* pattern
        assert len(expanded_targets) == 0

        # But all SLO names should still be collected in the batch
        assert len(slo_names_in_batch) == 2
        assert 'unrelated-slo' in slo_names_in_batch
        assert 'another-slo' in slo_names_in_batch

    def test_expand_slo_wildcard_include_linked_accounts_parameter(
        self, mock_applicationsignals_client
    ):
        """Test that IncludeLinkedAccounts parameter is always set to True."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        expand_slo_wildcard_patterns(
            targets, applicationsignals_client=mock_applicationsignals_client
        )

        # Verify that IncludeLinkedAccounts was passed to list_service_level_objectives
        mock_applicationsignals_client.list_service_level_objectives.assert_called_once()
        call_args = mock_applicationsignals_client.list_service_level_objectives.call_args[1]
        assert call_args['IncludeLinkedAccounts'] is True

    def test_expand_slo_wildcard_empty_slo_names_collection(self, mock_applicationsignals_client):
        """Test SLO name collection when SLO summaries have empty names."""
        # Mock response with SLOs that have empty or missing names
        mock_applicationsignals_client.list_service_level_objectives.return_value = {
            'SloSummaries': [
                {
                    'Name': '',  # Empty name
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/empty-name',
                },
                {
                    # Missing Name field entirely
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/no-name',
                },
                {
                    'Name': 'valid-slo',
                    'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/valid-slo',
                },
            ]
        }

        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        expanded_targets, next_token, slo_names_in_batch = expand_slo_wildcard_patterns(
            targets, applicationsignals_client=mock_applicationsignals_client
        )

        # The '*' pattern matches all SLOs, including those with empty names
        assert len(expanded_targets) == 3
        slo_names = [t['Data']['Slo']['SloName'] for t in expanded_targets]
        assert '' in slo_names  # Empty name
        assert '' in slo_names  # Missing name becomes empty string
        assert 'valid-slo' in slo_names

        # All SLO names should be collected, including empty ones
        assert len(slo_names_in_batch) == 3
        assert '' in slo_names_in_batch  # Empty name
        assert '' in slo_names_in_batch  # Missing name becomes empty string
        assert 'valid-slo' in slo_names_in_batch


class TestExpandServiceOperationWildcardPatterns:
    """Test expand_service_operation_wildcard_patterns function."""

    @pytest.fixture
    def mock_applicationsignals_client(self):
        """Mock applicationsignals client."""
        mock_client = Mock()
        mock_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'payment-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                }
            ]
        }
        mock_client.list_service_operations.return_value = {
            'Operations': [
                {
                    'Name': 'GET /payments',
                    'MetricReferences': [
                        {'MetricType': 'Latency'},
                        {'MetricType': 'Availability'},
                    ],
                },
                {'Name': 'POST /payments', 'MetricReferences': [{'MetricType': 'Latency'}]},
            ]
        }
        return mock_client

    def test_expand_service_operation_wildcard_all(self, mock_applicationsignals_client):
        """Test expanding wildcard for all service operations."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Type': 'Service', 'Name': '*payment*', 'Environment': 'prod'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 2  # Both operations have Latency metric
        operation_names = [t['Data']['ServiceOperation']['Operation'] for t in expanded_targets]
        assert 'GET /payments' in operation_names
        assert 'POST /payments' in operation_names
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_specific_operation(self, mock_applicationsignals_client):
        """Test expanding with specific operation pattern."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'payment-service'},
                        'Operation': '*GET*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_metric_type_filter(self, mock_applicationsignals_client):
        """Test filtering by metric type availability."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'payment-service'},
                        'Operation': '*',
                        'MetricType': 'Availability',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 1  # Only GET /payments has Availability metric
        assert expanded_targets[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_no_wildcard(self, mock_applicationsignals_client):
        """Test with no wildcard patterns."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'exact-service'},
                        'Operation': 'exact-operation',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 1
        assert (
            expanded_targets[0]['Data']['ServiceOperation']['Service']['Name'] == 'exact-service'
        )
        assert expanded_targets[0]['Data']['ServiceOperation']['Operation'] == 'exact-operation'
        assert next_token is None
        assert len(service_names_in_batch) == 0  # No API call made for non-wildcard

    def test_expand_service_operation_api_error(self, mock_applicationsignals_client):
        """Test handling API errors during expansion."""
        mock_applicationsignals_client.list_services.side_effect = Exception('API Error')

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        with pytest.raises(
            ValueError, match='Failed to expand service operation wildcard patterns'
        ):
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )

    def test_expand_service_operation_operations_api_error(self, mock_applicationsignals_client):
        """Test handling operations API errors during expansion."""
        mock_applicationsignals_client.list_service_operations.side_effect = Exception(
            'Operations API Error'
        )

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        # Should not raise exception, but log warning and continue
        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should still return empty result since operations couldn't be fetched
        assert len(expanded_targets) == 0
        assert next_token is None
        assert len(service_names_in_batch) == 1  # Service names are still collected

    def test_expand_service_operation_non_service_operation_targets(
        self, mock_applicationsignals_client
    ):
        """Test that non-service-operation targets pass through unchanged."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Name': 'test-service'}}}]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Type'] == 'service'
        assert next_token is None
        assert len(service_names_in_batch) == 0

    def test_expand_service_operation_fault_to_availability_conversion(
        self, mock_applicationsignals_client
    ):
        """Test that operations with Fault metrics match when looking for Availability."""
        # Mock an operation that only has Fault metric but we're looking for Availability
        mock_applicationsignals_client.list_service_operations.return_value = {
            'Operations': [
                {
                    'Name': 'GET /payments',
                    'MetricReferences': [
                        {'MetricType': 'Fault'},  # Only has Fault, not Availability
                        {'MetricType': 'Latency'},
                    ],
                },
                {
                    'Name': 'POST /payments',
                    'MetricReferences': [
                        {'MetricType': 'Latency'},  # No Fault or Availability
                    ],
                },
            ]
        }

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'payment-service'},
                        'Operation': '*',
                        'MetricType': 'Availability',  # Looking for Availability
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should find the GET operation because it has Fault metric which matches Availability
        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'
        assert expanded_targets[0]['Data']['ServiceOperation']['MetricType'] == 'Availability'
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_wildcard_with_pagination(
        self, mock_applicationsignals_client
    ):
        """Test expanding service operation wildcard patterns with pagination support."""
        # Mock response with NextToken
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'payment-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
            ],
            'NextToken': 'next-service-op-token-123',
        }

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                max_results=1,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        assert len(expanded_targets) == 2  # Both operations have Latency metric
        assert next_token == 'next-service-op-token-123'
        assert len(service_names_in_batch) == 1
        assert 'payment-service' in service_names_in_batch

    def test_expand_service_operation_wildcard_with_next_token_input(
        self, mock_applicationsignals_client
    ):
        """Test expanding service operation wildcard patterns with next_token input parameter."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                next_token='input-service-op-token-456',
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Verify that NextToken was passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['NextToken'] == 'input-service-op-token-456'

        assert len(expanded_targets) == 2
        assert next_token is None  # No NextToken in mock response
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_wildcard_max_results_parameter(
        self, mock_applicationsignals_client
    ):
        """Test that max_results parameter is passed to list_services API."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expand_service_operation_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            max_results=15,
            applicationsignals_client=mock_applicationsignals_client,
        )

        # Verify that MaxResults was passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['MaxResults'] == 15

    def test_expand_service_operation_wildcard_service_names_collection(
        self, mock_applicationsignals_client
    ):
        """Test that all service names are collected in batch regardless of filtering."""
        # Mock response with services that don't match the operation pattern
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'unrelated-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'another-service',
                        'Type': 'Service',
                        'Environment': 'staging',
                    }
                },
            ]
        }

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, _, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # No services match the *payment* pattern
        assert len(expanded_targets) == 0

        # But all service names should still be collected in the batch
        assert len(service_names_in_batch) == 2
        assert 'unrelated-service' in service_names_in_batch
        assert 'another-service' in service_names_in_batch

    def test_expand_service_operation_wildcard_filters_unknown_services(
        self, mock_applicationsignals_client
    ):
        """Test that services with Unknown names or non-Service types are filtered out."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'Unknown',  # Should be filtered out
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'valid-service',
                        'Type': 'NotService',  # Should be filtered out
                        'Environment': 'prod',
                    }
                },
                {
                    'KeyAttributes': {
                        'Name': 'good-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    }
                },
            ]
        }

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Only the good service should be processed for operations
        # (Unknown and NotService types are filtered out during expansion)
        assert len(expanded_targets) == 2  # good-service has 2 operations
        service_names = [
            t['Data']['ServiceOperation']['Service']['Name'] for t in expanded_targets
        ]
        assert all(name == 'good-service' for name in service_names)

        # But all service names should still be collected in the batch (including filtered ones)
        assert len(service_names_in_batch) == 3
        assert 'Unknown' in service_names_in_batch
        assert 'valid-service' in service_names_in_batch
        assert 'good-service' in service_names_in_batch

    def test_expand_service_operation_wildcard_exact_service_match(
        self, mock_applicationsignals_client
    ):
        """Test expanding with exact service name (no wildcard in service name)."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'payment-service'},  # Exact match, no wildcard
                        'Operation': '*GET*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should find the exact service and expand its operations
        assert len(expanded_targets) == 1
        assert (
            expanded_targets[0]['Data']['ServiceOperation']['Service']['Name'] == 'payment-service'
        )
        assert expanded_targets[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_wildcard_exact_operation_match(
        self, mock_applicationsignals_client
    ):
        """Test expanding with exact operation name (no wildcard in operation name)."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': 'GET /payments',  # Exact match, no wildcard
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # Should find services matching pattern and exact operation
        assert len(expanded_targets) == 1
        assert (
            expanded_targets[0]['Data']['ServiceOperation']['Service']['Name'] == 'payment-service'
        )
        assert expanded_targets[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_wildcard_no_matching_operations(
        self, mock_applicationsignals_client
    ):
        """Test expanding when no operations match the pattern."""
        # Mock operations that don't match the search pattern
        mock_applicationsignals_client.list_service_operations.return_value = {
            'Operations': [
                {
                    'Name': 'DELETE /payments',  # Doesn't match *GET* pattern
                    'MetricReferences': [{'MetricType': 'Latency'}],
                },
                {
                    'Name': 'PUT /payments',  # Doesn't match *GET* pattern
                    'MetricReferences': [{'MetricType': 'Latency'}],
                },
            ]
        }

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'payment-service'},
                        'Operation': '*GET*',  # No operations match this pattern
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # No operations should match the *GET* pattern
        assert len(expanded_targets) == 0
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_wildcard_no_matching_metric_type(
        self, mock_applicationsignals_client
    ):
        """Test expanding when operations don't have the required metric type."""
        # Mock operations that don't have the required metric type
        mock_applicationsignals_client.list_service_operations.return_value = {
            'Operations': [
                {
                    'Name': 'GET /payments',
                    'MetricReferences': [
                        {'MetricType': 'Error'},  # Only has Error, not Latency
                        {'MetricType': 'Fault'},
                    ],
                },
                {
                    'Name': 'POST /payments',
                    'MetricReferences': [
                        {'MetricType': 'Error'},  # Only has Error, not Latency
                    ],
                },
            ]
        }

        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': 'payment-service'},
                        'Operation': '*',
                        'MetricType': 'Latency',  # Looking for Latency but operations don't have it
                    }
                },
            }
        ]

        expanded_targets, next_token, service_names_in_batch, _ = (
            expand_service_operation_wildcard_patterns(
                targets,
                1640995200,
                1641081600,
                applicationsignals_client=mock_applicationsignals_client,
            )
        )

        # No operations should be included because they don't have Latency metric
        assert len(expanded_targets) == 0
        assert next_token is None
        assert len(service_names_in_batch) == 1

    def test_expand_service_operation_wildcard_time_parameters_passed(
        self, mock_applicationsignals_client
    ):
        """Test that start and end time parameters are correctly passed to APIs."""
        targets = [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Name': '*payment*'},
                        'Operation': '*',
                        'MetricType': 'Latency',
                    }
                },
            }
        ]

        start_time = 1640995200  # 2022-01-01 00:00:00 UTC
        end_time = 1641081600  # 2022-01-02 00:00:00 UTC

        expand_service_operation_wildcard_patterns(
            targets, start_time, end_time, applicationsignals_client=mock_applicationsignals_client
        )

        # Verify that StartTime and EndTime were passed to list_services
        mock_applicationsignals_client.list_services.assert_called_once()
        call_args = mock_applicationsignals_client.list_services.call_args[1]
        assert call_args['StartTime'].timestamp() == start_time
        assert call_args['EndTime'].timestamp() == end_time

        # Verify that StartTime and EndTime were passed to list_service_operations
        mock_applicationsignals_client.list_service_operations.assert_called_once()
        operations_call_args = mock_applicationsignals_client.list_service_operations.call_args[1]
        assert operations_call_args['StartTime'].timestamp() == start_time
        assert operations_call_args['EndTime'].timestamp() == end_time
