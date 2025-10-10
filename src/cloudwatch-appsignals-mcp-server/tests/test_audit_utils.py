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
from awslabs.cloudwatch_appsignals_mcp_server.audit_utils import (
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
    def mock_appsignals_client(self):
        """Mock appsignals client."""
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client'
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
        self, mock_appsignals_client, sample_input_obj
    ):
        """Test successful API execution with single batch."""
        mock_response = {
            'AuditFindings': [
                {'FindingId': 'finding-1', 'Severity': 'CRITICAL', 'Description': 'Test finding'}
            ]
        }
        mock_appsignals_client.list_audit_findings.return_value = mock_response

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')

        assert 'Test Banner' in result
        assert 'finding-1' in result
        assert 'CRITICAL' in result
        mock_appsignals_client.list_audit_findings.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_audit_api_multiple_batches(self, mock_appsignals_client):
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
        mock_appsignals_client.list_audit_findings.side_effect = mock_responses

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(input_obj, 'us-east-1', 'Test Banner\n')

        assert 'finding-1' in result
        assert 'finding-2' in result
        assert 'TotalBatches' in result
        assert mock_appsignals_client.list_audit_findings.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_audit_api_no_findings(self, mock_appsignals_client, sample_input_obj):
        """Test API execution with no findings."""
        mock_response = {'AuditFindings': []}
        mock_appsignals_client.list_audit_findings.return_value = mock_response

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')

        assert 'Test Banner' in result
        assert 'TotalFindingsCount": 0' in result

    @pytest.mark.asyncio
    async def test_execute_audit_api_error_handling(
        self, mock_appsignals_client, sample_input_obj
    ):
        """Test API execution with error handling."""
        mock_appsignals_client.list_audit_findings.side_effect = Exception('API Error')

        with patch('builtins.open', mock_open()):
            result = await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')

        assert 'API call failed: API Error' in result
        assert 'BatchErrors' in result

    @pytest.mark.asyncio
    async def test_execute_audit_api_log_path_handling(
        self, mock_appsignals_client, sample_input_obj
    ):
        """Test log path handling with different environment variables."""
        mock_response = {'AuditFindings': []}
        mock_appsignals_client.list_audit_findings.return_value = mock_response

        # Test with custom log path
        with patch.dict(os.environ, {'AUDITOR_LOG_PATH': '/custom/path'}):
            with patch('os.makedirs') as mock_makedirs:
                with patch('builtins.open', mock_open()):
                    await execute_audit_api(sample_input_obj, 'us-east-1', 'Test Banner\n')
                    mock_makedirs.assert_called()

    @pytest.mark.asyncio
    async def test_execute_audit_api_log_path_exception(
        self, mock_appsignals_client, sample_input_obj
    ):
        """Test log path handling when directory creation fails."""
        mock_response = {'AuditFindings': []}
        mock_appsignals_client.list_audit_findings.return_value = mock_response

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


class TestExpandServiceWildcardPatterns:
    """Test expand_service_wildcard_patterns function."""

    @pytest.fixture
    def mock_appsignals_client(self):
        """Mock appsignals client."""
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

    def test_expand_service_wildcard_all_services(self, mock_appsignals_client):
        """Test expanding wildcard for all services."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*'}}}]

        result = expand_service_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 3
        service_names = [t['Data']['Service']['Name'] for t in result]
        assert 'payment-service' in service_names
        assert 'user-service' in service_names
        assert 'payment-gateway' in service_names

    def test_expand_service_wildcard_pattern_match(self, mock_appsignals_client):
        """Test expanding wildcard with pattern matching."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*payment*'}}}
        ]

        result = expand_service_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 2
        service_names = [t['Data']['Service']['Name'] for t in result]
        assert 'payment-service' in service_names
        assert 'payment-gateway' in service_names
        assert 'user-service' not in service_names

    def test_expand_service_no_wildcard(self, mock_appsignals_client):
        """Test with no wildcard patterns."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': 'exact-service'}}}
        ]

        result = expand_service_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 1
        assert result[0]['Data']['Service']['Name'] == 'exact-service'

    def test_expand_service_shorthand_format(self, mock_appsignals_client):
        """Test expanding with shorthand service format."""
        targets = [{'Type': 'service', 'Service': '*payment*'}]

        result = expand_service_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 2
        service_names = [t['Data']['Service']['Name'] for t in result]
        assert 'payment-service' in service_names
        assert 'payment-gateway' in service_names

    def test_expand_service_api_error(self, mock_appsignals_client):
        """Test handling API errors during expansion."""
        mock_appsignals_client.list_services.side_effect = Exception('API Error')

        targets = [{'Type': 'service', 'Data': {'Service': {'Name': '*payment*'}}}]

        with pytest.raises(ValueError, match='Failed to expand service wildcard patterns'):
            expand_service_wildcard_patterns(
                targets, 1640995200, 1641081600, mock_appsignals_client
            )

    def test_expand_service_non_service_targets(self, mock_appsignals_client):
        """Test that non-service targets pass through unchanged."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo'}}}]

        result = expand_service_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 1
        assert result[0]['Type'] == 'slo'

    @patch('awslabs.cloudwatch_appsignals_mcp_server.utils.calculate_name_similarity')
    def test_expand_service_fuzzy_matching(self, mock_similarity, mock_appsignals_client):
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

        result = expand_service_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        # Should find fuzzy matches
        assert len(result) >= 1
        mock_similarity.assert_called()


class TestExpandSloWildcardPatterns:
    """Test expand_slo_wildcard_patterns function."""

    @pytest.fixture
    def mock_appsignals_client(self):
        """Mock appsignals client."""
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

    def test_expand_slo_wildcard_all_slos(self, mock_appsignals_client):
        """Test expanding wildcard for all SLOs."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*'}}}]

        result = expand_slo_wildcard_patterns(targets, mock_appsignals_client)

        assert len(result) == 3
        slo_names = [t['Data']['Slo']['SloName'] for t in result]
        assert 'payment-latency-slo' in slo_names
        assert 'user-availability-slo' in slo_names
        assert 'payment-availability-slo' in slo_names

    def test_expand_slo_wildcard_pattern_match(self, mock_appsignals_client):
        """Test expanding SLO wildcard with pattern matching."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*payment*'}}}]

        result = expand_slo_wildcard_patterns(targets, mock_appsignals_client)

        assert len(result) == 2
        slo_names = [t['Data']['Slo']['SloName'] for t in result]
        assert 'payment-latency-slo' in slo_names
        assert 'payment-availability-slo' in slo_names
        assert 'user-availability-slo' not in slo_names

    def test_expand_slo_no_wildcard(self, mock_appsignals_client):
        """Test with no SLO wildcard patterns."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'exact-slo'}}}]

        result = expand_slo_wildcard_patterns(targets, mock_appsignals_client)

        assert len(result) == 1
        assert result[0]['Data']['Slo']['SloName'] == 'exact-slo'

    def test_expand_slo_invalid_format_string(self, mock_appsignals_client):
        """Test handling invalid SLO format (string instead of dict)."""
        targets = [{'Type': 'slo', 'Data': {'Slo': 'invalid-string-format'}}]

        with pytest.raises(ValueError, match='Invalid SLO target format'):
            expand_slo_wildcard_patterns(targets, mock_appsignals_client)

    def test_expand_slo_invalid_format_other_type(self, mock_appsignals_client):
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
            expand_slo_wildcard_patterns(targets, mock_appsignals_client)

    def test_expand_slo_api_error(self, mock_appsignals_client):
        """Test handling API errors during SLO expansion."""
        mock_appsignals_client.list_service_level_objectives.side_effect = Exception('API Error')

        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': '*payment*'}}}]

        with pytest.raises(ValueError, match='Failed to expand SLO wildcard patterns'):
            expand_slo_wildcard_patterns(targets, mock_appsignals_client)


class TestExpandServiceOperationWildcardPatterns:
    """Test expand_service_operation_wildcard_patterns function."""

    @pytest.fixture
    def mock_appsignals_client(self):
        """Mock appsignals client."""
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

    def test_expand_service_operation_wildcard_all(self, mock_appsignals_client):
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

        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 2  # Both operations have Latency metric
        operation_names = [t['Data']['ServiceOperation']['Operation'] for t in result]
        assert 'GET /payments' in operation_names
        assert 'POST /payments' in operation_names

    def test_expand_service_operation_specific_operation(self, mock_appsignals_client):
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

        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 1
        assert result[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'

    def test_expand_service_operation_metric_type_filter(self, mock_appsignals_client):
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

        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 1  # Only GET /payments has Availability metric
        assert result[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'

    def test_expand_service_operation_no_wildcard(self, mock_appsignals_client):
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

        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 1
        assert result[0]['Data']['ServiceOperation']['Service']['Name'] == 'exact-service'
        assert result[0]['Data']['ServiceOperation']['Operation'] == 'exact-operation'

    def test_expand_service_operation_api_error(self, mock_appsignals_client):
        """Test handling API errors during expansion."""
        mock_appsignals_client.list_services.side_effect = Exception('API Error')

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
                targets, 1640995200, 1641081600, mock_appsignals_client
            )

    def test_expand_service_operation_operations_api_error(self, mock_appsignals_client):
        """Test handling operations API errors during expansion."""
        mock_appsignals_client.list_service_operations.side_effect = Exception(
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
        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        # Should still return empty result since operations couldn't be fetched
        assert len(result) == 0

    def test_expand_service_operation_non_service_operation_targets(self, mock_appsignals_client):
        """Test that non-service-operation targets pass through unchanged."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Name': 'test-service'}}}]

        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        assert len(result) == 1
        assert result[0]['Type'] == 'service'

    def test_expand_service_operation_fault_to_availability_conversion(
        self, mock_appsignals_client
    ):
        """Test that operations with Fault metrics match when looking for Availability."""
        # Mock an operation that only has Fault metric but we're looking for Availability
        mock_appsignals_client.list_service_operations.return_value = {
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

        result = expand_service_operation_wildcard_patterns(
            targets, 1640995200, 1641081600, mock_appsignals_client
        )

        # Should find the GET operation because it has Fault metric which matches Availability
        assert len(result) == 1
        assert result[0]['Data']['ServiceOperation']['Operation'] == 'GET /payments'
        assert result[0]['Data']['ServiceOperation']['MetricType'] == 'Availability'
