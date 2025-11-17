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
        assert 'TotalBatches' in result
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
        assert 'TotalFindingsCount": 0' in result
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
        assert 'BatchErrors' in result

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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
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

    def test_expand_service_wildcard_pattern_match(self, mock_applicationsignals_client):
        """Test expanding wildcard with pattern matching."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': '*payment*'}}}
        ]

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        assert len(expanded_targets) == 2
        service_names = [t['Data']['Service']['Name'] for t in expanded_targets]
        assert 'payment-service' in service_names
        assert 'payment-gateway' in service_names
        assert 'user-service' not in service_names
        assert next_token is None
        assert len(service_names_in_batch) == 3  # All services are collected in batch

    def test_expand_service_no_wildcard(self, mock_applicationsignals_client):
        """Test with no wildcard patterns."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': 'exact-service'}}}
        ]

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
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

    def test_expand_service_shorthand_format(self, mock_applicationsignals_client):
        """Test expanding with shorthand service format."""
        targets = [{'Type': 'service', 'Service': '*payment*'}]

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        assert len(expanded_targets) == 2
        service_names = [t['Data']['Service']['Name'] for t in expanded_targets]
        assert 'payment-service' in service_names
        assert 'payment-gateway' in service_names
        assert next_token is None
        assert len(service_names_in_batch) == 3

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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
            targets,
            1640995200,
            1641081600,
            applicationsignals_client=mock_applicationsignals_client,
        )

        assert len(expanded_targets) == 1
        assert expanded_targets[0]['Type'] == 'slo'
        assert next_token is None
        assert len(service_names_in_batch) == 0

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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
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

        expanded_targets, next_token, service_names_in_batch = expand_service_wildcard_patterns(
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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
        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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

        expanded_targets, next_token, service_names_in_batch = (
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
