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

"""Tests for service_audit_utils module."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.service_audit_utils import (
    _ci_get,
    _need,
    coerce_service_target,
    normalize_service_entity,
    normalize_service_target,
    normalize_service_targets,
    validate_and_enrich_service_targets,
)
from unittest.mock import Mock, patch


class TestCiGet:
    """Test _ci_get function."""

    def test_ci_get_exact_match(self):
        """Test exact key match."""
        data = {'Name': 'test-service', 'Type': 'Service'}
        result = _ci_get(data, 'Name')
        assert result == 'test-service'

    def test_ci_get_case_insensitive_match(self):
        """Test case insensitive key match."""
        data = {'name': 'test-service', 'TYPE': 'Service'}
        result = _ci_get(data, 'Name')
        assert result == 'test-service'

    def test_ci_get_multiple_names(self):
        """Test with multiple possible names."""
        data = {'service_name': 'test-service'}
        result = _ci_get(data, 'Name', 'service_name')
        assert result == 'test-service'

    def test_ci_get_not_found(self):
        """Test when key is not found."""
        data = {'other_key': 'value'}
        result = _ci_get(data, 'Name')
        assert result is None

    def test_ci_get_empty_dict(self):
        """Test with empty dictionary."""
        result = _ci_get({}, 'Name')
        assert result is None


class TestNeed:
    """Test _need function."""

    def test_need_found(self):
        """Test when required field is found."""
        data = {'Name': 'test-service'}
        result = _need(data, 'Name')
        assert result == 'test-service'

    def test_need_not_found(self):
        """Test when required field is not found."""
        data = {'other_key': 'value'}
        with pytest.raises(ValueError, match='Missing required field: one of Name'):
            _need(data, 'Name')

    def test_need_multiple_names(self):
        """Test with multiple possible names."""
        data = {'service_name': 'test-service'}
        result = _need(data, 'Name', 'service_name')
        assert result == 'test-service'


class TestCoerceServiceTarget:
    """Test coerce_service_target function."""

    def test_coerce_shorthand_service_string(self):
        """Test coercing shorthand service string."""
        target = {'Type': 'service', 'Service': 'test-service'}
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
        }
        assert result == expected

    def test_coerce_data_service_string(self):
        """Test coercing data service string."""
        target = {'Type': 'service', 'Data': {'Service': 'test-service'}}
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
        }
        assert result == expected

    def test_coerce_service_dict(self):
        """Test coercing service dictionary."""
        target = {
            'Type': 'service',
            'Data': {'Service': {'Name': 'test-service', 'Environment': 'prod'}},
        }
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {
                'Service': {'Type': 'Service', 'Name': 'test-service', 'Environment': 'prod'}
            },
        }
        assert result == expected

    def test_coerce_with_aws_account_id(self):
        """Test coercing with AWS account ID."""
        target = {
            'Type': 'service',
            'Service': {'Name': 'test-service', 'AwsAccountId': '123456789012'},
        }
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {
                'Service': {
                    'Type': 'Service',
                    'Name': 'test-service',
                    'AwsAccountId': '123456789012',
                }
            },
        }
        assert result == expected

    def test_coerce_case_insensitive_type(self):
        """Test coercing with case insensitive type."""
        target = {'type': 'SERVICE', 'service': 'test-service'}
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
        }
        assert result == expected

    def test_coerce_target_type_field(self):
        """Test coercing with target_type field."""
        target = {'target_type': 'service', 'service': 'test-service'}
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
        }
        assert result == expected

    def test_coerce_data_name_fallback(self):
        """Test coercing with data name fallback."""
        target = {'Type': 'service', 'Data': {'Name': 'test-service'}}
        result = coerce_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
        }
        assert result == expected

    def test_coerce_non_service_type(self):
        """Test coercing non-service type raises error."""
        target = {'Type': 'slo', 'Service': 'test-service'}
        with pytest.raises(ValueError, match='not a service target'):
            coerce_service_target(target)

    def test_coerce_missing_service(self):
        """Test coercing without service raises error."""
        target = {'Type': 'service'}
        with pytest.raises(ValueError, match="service target missing 'Service' payload"):
            coerce_service_target(target)


class TestNormalizeServiceEntity:
    """Test normalize_service_entity function."""

    def test_normalize_basic_entity(self):
        """Test normalizing basic service entity."""
        entity = {'Name': 'test-service', 'Environment': 'prod'}
        result = normalize_service_entity(entity)

        expected = {'Type': 'Service', 'Name': 'test-service', 'Environment': 'prod'}
        assert result == expected

    def test_normalize_with_aws_account_id(self):
        """Test normalizing with AWS account ID."""
        entity = {'Name': 'test-service', 'Environment': 'prod', 'AwsAccountId': '123456789012'}
        result = normalize_service_entity(entity)

        expected = {
            'Type': 'Service',
            'Name': 'test-service',
            'Environment': 'prod',
            'AwsAccountId': '123456789012',
        }
        assert result == expected

    def test_normalize_case_insensitive(self):
        """Test normalizing with case insensitive fields."""
        entity = {'name': 'test-service', 'environment': 'prod', 'type': 'CustomService'}
        result = normalize_service_entity(entity)

        expected = {'Type': 'CustomService', 'Name': 'test-service', 'Environment': 'prod'}
        assert result == expected

    def test_normalize_missing_name(self):
        """Test normalizing without required name."""
        entity = {'Environment': 'prod'}
        with pytest.raises(ValueError, match='Missing required field: one of Name, name'):
            normalize_service_entity(entity)

    def test_normalize_no_environment(self):
        """Test normalizing without environment."""
        entity = {'Name': 'test-service'}
        result = normalize_service_entity(entity)

        expected = {'Type': 'Service', 'Name': 'test-service', 'Environment': None}
        assert result == expected


class TestNormalizeServiceTarget:
    """Test normalize_service_target function."""

    def test_normalize_target_with_service_dict(self):
        """Test normalizing target with service dictionary."""
        target = {
            'Type': 'service',
            'Data': {'Service': {'Name': 'test-service', 'Environment': 'prod'}},
        }
        result = normalize_service_target(target)

        expected = {
            'Type': 'service',
            'Data': {
                'Service': {'Type': 'Service', 'Name': 'test-service', 'Environment': 'prod'}
            },
        }
        assert result == expected

    def test_normalize_target_missing_data(self):
        """Test normalizing target without data."""
        target = {'Type': 'service'}
        with pytest.raises(ValueError, match='Missing required field: one of Data, data'):
            normalize_service_target(target)


class TestNormalizeServiceTargets:
    """Test normalize_service_targets function."""

    def test_normalize_valid_targets(self):
        """Test normalizing valid service targets."""
        targets = [
            {'Type': 'service', 'Service': 'test-service-1'},
            {
                'Type': 'service',
                'Data': {'Service': {'Name': 'test-service-2', 'Environment': 'prod'}},
            },
        ]
        result = normalize_service_targets(targets)

        assert len(result) == 2
        assert result[0]['Data']['Service']['Name'] == 'test-service-1'
        assert result[1]['Data']['Service']['Name'] == 'test-service-2'

    def test_normalize_not_list(self):
        """Test normalizing non-list input."""
        with pytest.raises(ValueError, match='`service_targets` must be a JSON array'):
            normalize_service_targets({'Type': 'service'})  # type: ignore

    def test_normalize_empty_list(self):
        """Test normalizing empty list."""
        with pytest.raises(ValueError, match='`service_targets` must contain at least 1 item'):
            normalize_service_targets([])

    def test_normalize_non_dict_item(self):
        """Test normalizing with non-dictionary item."""
        with pytest.raises(ValueError, match='service_targets\\[1\\] must be an object'):
            normalize_service_targets(['invalid'])  # type: ignore

    def test_normalize_invalid_service_target(self):
        """Test normalizing invalid service target."""
        targets = [{'Type': 'service'}]  # Missing service data
        with pytest.raises(ValueError, match='service_targets\\[1\\] invalid service target'):
            normalize_service_targets(targets)

    def test_normalize_non_service_type(self):
        """Test normalizing non-service type."""
        targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo'}}}]
        with pytest.raises(ValueError, match="service_targets\\[1\\].type must be 'service'"):
            normalize_service_targets(targets)


class TestValidateAndEnrichServiceTargets:
    """Test validate_and_enrich_service_targets function."""

    @pytest.fixture
    def mock_applicationsignals_client(self):
        """Mock applicationsignals client."""
        client = Mock()
        client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'test-service',
                        'Type': 'Service',
                        'Environment': 'eks:test-cluster/default',
                    }
                }
            ]
        }
        return client

    def test_validate_with_environment(self, mock_applicationsignals_client):
        """Test validating targets that already have environment."""
        targets = [
            {
                'Type': 'service',
                'Data': {'Service': {'Name': 'test-service', 'Environment': 'prod'}},
            }
        ]

        result = validate_and_enrich_service_targets(
            targets, mock_applicationsignals_client, 1640995200, 1641081600
        )

        assert len(result) == 1
        assert result[0]['Data']['Service']['Environment'] == 'prod'
        mock_applicationsignals_client.list_services.assert_not_called()

    def test_validate_enrich_missing_environment(self, mock_applicationsignals_client):
        """Test enriching targets missing environment."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Name': 'test-service'}}}]

        result = validate_and_enrich_service_targets(
            targets, mock_applicationsignals_client, 1640995200, 1641081600
        )

        assert len(result) == 1
        assert result[0]['Data']['Service']['Environment'] == 'eks:test-cluster/default'
        mock_applicationsignals_client.list_services.assert_called_once()

    def test_validate_wildcard_pattern_error(self, mock_applicationsignals_client):
        """Test error when wildcard pattern found in validation."""
        targets = [{'Type': 'service', 'Data': {'Service': {'Name': '*test*'}}}]

        with pytest.raises(ValueError, match='Wildcard pattern.*found in validation phase'):
            validate_and_enrich_service_targets(
                targets, mock_applicationsignals_client, 1640995200, 1641081600
            )

    def test_validate_service_not_found(self, mock_applicationsignals_client):
        """Test error when service not found in API."""
        mock_applicationsignals_client.list_services.return_value = {'ServiceSummaries': []}

        targets = [{'Type': 'service', 'Data': {'Service': {'Name': 'nonexistent-service'}}}]

        with pytest.raises(ValueError, match="Service 'nonexistent-service' not found"):
            validate_and_enrich_service_targets(
                targets, mock_applicationsignals_client, 1640995200, 1641081600
            )

    def test_validate_service_no_environment(self, mock_applicationsignals_client):
        """Test error when service found but has no environment."""
        mock_applicationsignals_client.list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'test-service',
                        'Type': 'Service',
                        # No Environment
                    }
                }
            ]
        }

        targets = [{'Type': 'service', 'Data': {'Service': {'Name': 'test-service'}}}]

        with pytest.raises(ValueError, match='found but has no Environment'):
            validate_and_enrich_service_targets(
                targets, mock_applicationsignals_client, 1640995200, 1641081600
            )

    def test_validate_api_error(self, mock_applicationsignals_client):
        """Test handling API errors."""
        mock_applicationsignals_client.list_services.side_effect = Exception('API Error')

        targets = [{'Type': 'service', 'Data': {'Service': {'Name': 'test-service'}}}]

        with pytest.raises(ValueError, match='Environment is required.*API error: API Error'):
            validate_and_enrich_service_targets(
                targets, mock_applicationsignals_client, 1640995200, 1641081600
            )

    def test_validate_missing_environment_no_name(self, mock_applicationsignals_client):
        """Test error when environment missing and no service name."""
        targets = [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service'
                        # No Name or Environment
                    }
                },
            }
        ]

        with pytest.raises(ValueError, match='Environment is required'):
            validate_and_enrich_service_targets(
                targets, mock_applicationsignals_client, 1640995200, 1641081600
            )

    @patch('awslabs.cloudwatch_applicationsignals_mcp_server.service_audit_utils.logger')
    def test_validate_non_service_target_warning(
        self, mock_logger, mock_applicationsignals_client
    ):
        """Test warning for non-service targets."""
        targets = [
            {
                'Type': 'slo',  # Non-service type
                'Data': {'Slo': {'SloName': 'test-slo'}},
            }
        ]

        result = validate_and_enrich_service_targets(
            targets, mock_applicationsignals_client, 1640995200, 1641081600
        )

        assert len(result) == 1
        mock_logger.warning.assert_called_once()
