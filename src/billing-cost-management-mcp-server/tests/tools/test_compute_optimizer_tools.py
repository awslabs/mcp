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

"""Unit tests for the compute_optimizer_tools module.

These tests verify the functionality of the AWS Compute Optimizer tools, including:
- Retrieving EC2 instance optimization recommendations with performance metrics
- Getting Auto Scaling Group recommendations for instance type optimization
- Fetching EBS volume recommendations for storage optimization
- Getting Lambda function recommendations for memory optimization
- Handling recommendation filters, account scoping, and performance risk assessment
- Error handling for API exceptions and invalid parameters
"""

import fastmcp
import importlib
import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
    compute_optimizer_server,
    format_savings_opportunity,
    format_timestamp,
    get_auto_scaling_group_recommendations,
    get_ebs_volume_recommendations,
    get_ec2_instance_recommendations,
    get_lambda_function_recommendations,
    get_rds_recommendations,
)
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_co_client():
    """Create a mock Compute Optimizer boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_ec2_instance_recommendations.return_value = {
        'instanceRecommendations': [
            {
                'accountId': '123456789012',
                'currentInstanceType': 't3.micro',
                'finding': 'OVERPROVISIONED',
                'instanceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abcdef1234567890',
                'instanceName': 'test-instance',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'instanceType': 't2.nano',
                        'performanceRisk': 'LOW',
                        'projectedUtilization': 45.0,
                        'savingsOpportunity': {
                            'savingsPercentage': 30.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 10.50,
                            },
                        },
                    }
                ],
            }
        ],
        'nextToken': 'next-token-123',
    }

    mock_client.get_auto_scaling_group_recommendations.return_value = {
        'autoScalingGroupRecommendations': [
            {
                'accountId': '123456789012',
                'autoScalingGroupArn': 'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:123',
                'autoScalingGroupName': 'test-asg',
                'currentInstanceType': 't3.medium',
                'finding': 'NOT_OPTIMIZED',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'instanceType': 't3.small',
                        'performanceRisk': 'MEDIUM',
                        'projectedUtilization': 60.0,
                        'savingsOpportunity': {
                            'savingsPercentage': 25.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 15.75,
                            },
                        },
                    }
                ],
            }
        ],
    }

    mock_client.get_ebs_volume_recommendations.return_value = {
        'volumeRecommendations': [
            {
                'accountId': '123456789012',
                'volumeArn': 'arn:aws:ec2:us-east-1:123456789012:volume/vol-0abcdef1234567890',
                'currentConfiguration': {
                    'volumeType': 'gp2',
                    'volumeSize': 100,
                    'volumeBaselineIOPS': 300,
                    'volumeBurstIOPS': 3000,
                },
                'finding': 'OVERPROVISIONED',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'configuration': {
                            'volumeType': 'gp3',
                            'volumeSize': 50,
                            'volumeBaselineIOPS': 3000,
                        },
                        'performanceRisk': 'LOW',
                        'savingsOpportunity': {
                            'savingsPercentage': 40.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 8.20,
                            },
                        },
                    }
                ],
            }
        ],
    }

    mock_client.get_lambda_function_recommendations.return_value = {
        'lambdaFunctionRecommendations': [
            {
                'accountId': '123456789012',
                'functionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
                'functionName': 'test-function',
                'functionVersion': '$LATEST',
                'finding': 'OVER_PROVISIONED',
                'currentMemorySize': 1024,
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'memorySizeRecommendationOptions': [
                    {
                        'memorySize': 512,
                        'rank': 1,
                        'projectedUtilization': 60.0,
                        'savingsOpportunity': {
                            'savingsPercentage': 50.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 5.20,
                            },
                        },
                    }
                ],
            }
        ],
        'nextToken': 'next-token-lambda',
    }

    mock_client.get_rds_database_recommendations.return_value = {
        'rdsDBRecommendations': [
            {
                'accountId': '123456789012',
                'instanceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                'instanceName': 'test-db',
                'currentInstanceClass': 'db.r5.large',
                'finding': 'OVER_PROVISIONED',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'instanceClass': 'db.r5.medium',
                        'performanceRisk': 'LOW',
                        'savingsOpportunity': {
                            'savingsPercentage': 35.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 25.80,
                            },
                        },
                    }
                ],
            }
        ],
        'nextToken': 'next-token-rds',
    }

    mock_client.get_rds_instance_recommendations.return_value = {
        'instanceRecommendations': [
            {
                'accountId': '123456789012',
                'instanceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                'instanceName': 'test-db',
                'currentInstanceClass': 'db.r5.large',
                'finding': 'OVER_PROVISIONED',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'instanceClass': 'db.r5.medium',
                        'performanceRisk': 'LOW',
                        'savingsOpportunity': {
                            'savingsPercentage': 35.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 25.80,
                            },
                        },
                    }
                ],
            }
        ],
        'nextToken': 'next-token-rds',
    }

    return mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.mark.asyncio
class TestGetEC2InstanceRecommendations:
    """Tests for get_ec2_instance_recommendations function."""

    async def test_get_ec2_instance_recommendations_with_filters(
        self, mock_context, mock_co_client
    ):
        """Test get_ec2_instance_recommendations with filters."""
        # Setup
        filters = '[{"Name":"Finding","Values":["OVERPROVISIONED"]}]'
        account_ids = '["123456789012"]'
        max_results = 10
        next_token = 'token-123'

        # Execute
        result = await get_ec2_instance_recommendations(
            mock_context,
            mock_co_client,
            max_results,
            filters,
            account_ids,
            next_token,
        )

        # Assert
        mock_co_client.get_ec2_instance_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_ec2_instance_recommendations.call_args[1]

        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['filters'] == json.loads(filters)
        assert call_kwargs['accountIds'] == json.loads(account_ids)
        assert call_kwargs['nextToken'] == next_token

        # Check result format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']
        assert len(result['data']['recommendations']) == 1
        assert result['data']['next_token'] == 'next-token-123'


@pytest.mark.asyncio
class TestGetAutoScalingGroupRecommendations:
    """Tests for get_auto_scaling_group_recommendations function."""

    async def test_basic_call(self, mock_context, mock_co_client):
        """Test basic call to get_auto_scaling_group_recommendations."""
        result = await get_auto_scaling_group_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        # Verify the client was called correctly
        mock_co_client.get_auto_scaling_group_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_auto_scaling_group_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10

        # Verify response format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']

        # Verify recommendation format
        recommendations = result['data']['recommendations']
        assert len(recommendations) == 1
        recommendation = recommendations[0]

        assert (
            recommendation['auto_scaling_group_arn']
            == 'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:123'
        )
        assert recommendation['auto_scaling_group_name'] == 'test-asg'
        assert recommendation['account_id'] == '123456789012'
        assert recommendation['current_configuration']['instance_type'] == 't3.medium'
        assert recommendation['current_configuration']['finding'] == 'NOT_OPTIMIZED'


@pytest.mark.asyncio
class TestGetEBSVolumeRecommendations:
    """Tests for get_ebs_volume_recommendations function."""

    async def test_basic_call(self, mock_context, mock_co_client):
        """Test basic call to get_ebs_volume_recommendations."""
        result = await get_ebs_volume_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        # Verify the client was called correctly
        mock_co_client.get_ebs_volume_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_ebs_volume_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10

        # Verify response format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']


@pytest.mark.asyncio
class TestGetLambdaFunctionRecommendations:
    """Tests for get_lambda_function_recommendations function."""

    async def test_basic_call(self, mock_context, mock_co_client):
        """Test basic call to get_lambda_function_recommendations."""
        result = await get_lambda_function_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        # Verify the client was called correctly
        mock_co_client.get_lambda_function_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_lambda_function_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10

        # Verify response format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']

        # Verify recommendation format
        recommendations = result['data']['recommendations']
        assert len(recommendations) == 1
        recommendation = recommendations[0]

        assert (
            recommendation['function_arn']
            == 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        )
        assert recommendation['function_name'] == 'test-function'
        assert recommendation['account_id'] == '123456789012'
        assert recommendation['current_configuration']['memory_size'] == 1024
        assert recommendation['current_configuration']['finding'] == 'OVER_PROVISIONED'

        # Verify the recommendation options
        assert len(recommendation['recommendation_options']) == 1
        option = recommendation['recommendation_options'][0]
        assert option['memory_size'] == 512
        assert option['projected_utilization'] == 60.0
        assert option['rank'] == 1
        assert option['savings_opportunity']['savings_percentage'] == 50.0
        assert option['savings_opportunity']['estimated_monthly_savings']['currency'] == 'USD'
        assert option['savings_opportunity']['estimated_monthly_savings']['value'] == 5.20

    async def test_with_filters(self, mock_context, mock_co_client):
        """Test get_lambda_function_recommendations with filters."""
        # Setup
        filters = '[{"Name":"Finding","Values":["OVER_PROVISIONED"]}]'
        account_ids = '["123456789012"]'

        # Use patch to handle the parse_json calls
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            # Set up mock return values for parse_json calls
            mock_parse_json.side_effect = [
                [{'Name': 'Finding', 'Values': ['OVER_PROVISIONED']}],  # filters
                ['123456789012'],  # account_ids
            ]

            # Execute
            await get_lambda_function_recommendations(
                mock_context,
                mock_co_client,
                max_results=10,
                filters=filters,
                account_ids=account_ids,
                next_token='next-page',
            )

            # Assert
            mock_co_client.get_lambda_function_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_lambda_function_recommendations.call_args[1]

            # Verify that the parsed parameters were passed to the client
            assert 'filters' in call_kwargs
            assert 'accountIds' in call_kwargs
            assert call_kwargs['nextToken'] == 'next-page'


@pytest.mark.asyncio
class TestGetRDSRecommendations:
    """Tests for get_rds_recommendations function."""

    async def test_basic_call(self, mock_context, mock_co_client):
        """Test basic call to get_rds_recommendations."""
        result = await get_rds_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        # Verify the client was called correctly
        mock_co_client.get_rds_database_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_rds_database_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10

        # Verify response format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']

        # Verify recommendation format
        recommendations = result['data']['recommendations']
        assert len(recommendations) == 1
        recommendation = recommendations[0]

        assert recommendation['instance_arn'] == 'arn:aws:rds:us-east-1:123456789012:db:test-db'
        assert recommendation['instance_name'] == 'test-db'
        assert recommendation['account_id'] == '123456789012'
        assert recommendation['current_configuration']['instance_class'] == 'db.r5.large'
        assert recommendation['current_configuration']['finding'] == 'OVER_PROVISIONED'

        # Verify the recommendation options
        assert len(recommendation['recommendation_options']) == 1
        option = recommendation['recommendation_options'][0]
        assert option['instance_class'] == 'db.r5.medium'
        assert option['performance_risk'] == 'LOW'
        assert option['savings_opportunity']['savings_percentage'] == 35.0
        assert option['savings_opportunity']['estimated_monthly_savings']['currency'] == 'USD'
        assert option['savings_opportunity']['estimated_monthly_savings']['value'] == 25.80

    async def test_with_filters(self, mock_context, mock_co_client):
        """Test get_rds_recommendations with filters."""
        # Setup
        filters = '[{"Name":"Finding","Values":["OVER_PROVISIONED"]}]'
        account_ids = '["123456789012"]'

        # Use patch to handle the parse_json calls
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            # Set up mock return values for parse_json calls
            mock_parse_json.side_effect = [
                [{'Name': 'Finding', 'Values': ['OVER_PROVISIONED']}],  # filters
                ['123456789012'],  # account_ids
            ]

            # Execute
            await get_rds_recommendations(
                mock_context,
                mock_co_client,
                max_results=10,
                filters=filters,
                account_ids=account_ids,
                next_token='next-page-rds',
            )

            # Assert
            mock_co_client.get_rds_database_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_rds_database_recommendations.call_args[1]

            # Verify that the parsed parameters were passed to the client
            assert 'filters' in call_kwargs
            assert 'accountIds' in call_kwargs
            assert call_kwargs['nextToken'] == 'next-page-rds'


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_format_savings_opportunity(self):
        """Test format_savings_opportunity function."""
        # Test with complete data
        savings = {
            'savingsPercentage': 50.0,
            'estimatedMonthlySavings': {
                'currency': 'USD',
                'value': 100.0,
            },
        }
        result = format_savings_opportunity(savings)
        assert result is not None
        assert result['savings_percentage'] == 50.0
        assert result['estimated_monthly_savings'] is not None
        assert result['estimated_monthly_savings']['currency'] == 'USD'
        assert result['estimated_monthly_savings']['value'] == 100.0
        # Note: No 'formatted' key in the compute_optimizer implementation

        # Test with None
        result = format_savings_opportunity(None)
        assert result is None

    def test_format_timestamp(self):
        """Test format_timestamp function."""
        # Test with datetime object
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = format_timestamp(dt)
        assert result == '2023-01-01T12:00:00'

        # Test with None
        result = format_timestamp(None)
        assert result is None


def test_compute_optimizer_server_initialization():
    """Test that the compute_optimizer_server is properly initialized."""
    # Verify the server name
    assert compute_optimizer_server.name == 'compute-optimizer-tools'

    # Verify the server instructions
    assert compute_optimizer_server.instructions and (
        'Tools for working with AWS Compute Optimizer API' in compute_optimizer_server.instructions
    )

    assert isinstance(compute_optimizer_server, FastMCP)


def _reload_compute_optimizer_with_identity_decorator() -> Any:
    """Reload compute_optimizer_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'compute_optimizer' we can invoke directly to cover routing branches.
    """
    from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools as co_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(co_mod)
        return co_mod


@pytest.mark.asyncio
class TestComputeOptimizerFastMCP:
    """Test the actual FastMCP-wrapped compute_optimizer function directly."""

    async def test_co_real_get_ec2_recommendations_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer get_ec2_instance_recommendations with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn: Callable[..., Any] = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_ec2_instance_recommendations', new_callable=AsyncMock
            ) as mock_get,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }
            mock_create_client.return_value = mock_client
            mock_get.return_value = {'status': 'success', 'data': {'recommendations': []}}

            res = await real_fn(
                mock_context,
                operation='get_ec2_instance_recommendations',
                max_results=100,
                filters='[{"Name":"Finding","Values":["OVERPROVISIONED"]}]',
                account_ids='["123456789012"]',
            )
            assert res['status'] == 'success'
            mock_get.assert_awaited_once()

    async def test_co_real_get_auto_scaling_group_recommendations_reload_identity_decorator(
        self, mock_context
    ):
        """Test real compute_optimizer get_auto_scaling_group_recommendations with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_auto_scaling_group_recommendations', new_callable=AsyncMock
            ) as mock_impl,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['autoScalingGroup'],
            }
            mock_create_client.return_value = mock_client
            mock_impl.return_value = {'status': 'success', 'data': {'recommendations': []}}

            res = await real_fn(
                mock_context, operation='get_auto_scaling_group_recommendations', max_results=50
            )
            assert res['status'] == 'success'
            mock_impl.assert_awaited_once()

    async def test_co_real_invalid_operation_error_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer invalid operation error with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }
            mock_create_client.return_value = mock_client

            res = await real_fn(mock_context, operation='definitely_not_supported')
            assert res['status'] == 'error'
            assert res['data']['error_type'] == 'invalid_operation'
            assert 'Unsupported operation' in res['message']

    async def test_co_real_enrollment_error_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer enrollment error with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'INACTIVE',
                'resourceTypes': [],
            }
            mock_create_client.return_value = mock_client

            res = await real_fn(mock_context, operation='get_ec2_instance_recommendations')
            assert res['status'] == 'error'
            assert res['data']['error_type'] == 'enrollment_error'
            assert 'not active' in res['message']

    async def test_co_real_resource_not_enrolled_error_reload_identity_decorator(
        self, mock_context
    ):
        """Test real compute_optimizer with active enrollment status."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['lambdaFunction'],  # Missing ec2Instance
            }
            mock_client.get_ec2_instance_recommendations.return_value = {
                'instanceRecommendations': [],
                'nextToken': None,
            }
            mock_create_client.return_value = mock_client

            res = await real_fn(mock_context, operation='get_ec2_instance_recommendations')
            assert res['status'] == 'success'

    async def test_co_real_access_denied_error_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer access denied error with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }

            from botocore.exceptions import ClientError

            mock_client.get_ec2_instance_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'},
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 403},
                },
                operation_name='GetEC2InstanceRecommendations',
            )
            mock_create_client.return_value = mock_client

            res = await real_fn(mock_context, operation='get_ec2_instance_recommendations')
            assert res['status'] == 'error'
            assert res['error_type'] == 'access_denied'
            assert 'Access denied' in res['message']

    async def test_co_real_exception_flow_calls_handle_error_reload_identity_decorator(
        self, mock_context
    ):
        """Test real compute_optimizer exception flow calls handle_error with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_ec2_instance_recommendations', new_callable=AsyncMock
            ) as mock_impl,
            patch.object(co_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }
            mock_create_client.return_value = mock_client
            mock_impl.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': 'error', 'message': 'boom'}

            res = await real_fn(mock_context, operation='get_ec2_instance_recommendations')
            assert res['status'] == 'error'
            assert 'boom' in res.get('message', '')
            mock_handle.assert_awaited_once()

    async def test_co_real_value_error_handling_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer ValueError handling with identity decorator."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }
            mock_client.get_ec2_instance_recommendations.side_effect = ValueError(
                'Invalid parameter'
            )
            mock_create_client.return_value = mock_client

            res = await real_fn(mock_context, operation='get_ec2_instance_recommendations')
            assert res['status'] == 'error'
            assert res['error_type'] == 'validation_error'
            assert 'Invalid parameter' in res['message']


@pytest.mark.asyncio
class TestComputeOptimizerCoverageGaps:
    """Tests targeting specific uncovered lines."""

    async def test_enrollment_status_access_denied_warning(self, mock_context):
        """Test enrollment status check with access denied - covers lines 148-158."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            # Make enrollment status check fail with AccessDeniedException
            mock_client.get_enrollment_status.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'AccessDeniedException',
                        'Message': 'Access denied for enrollment',
                    },
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 403},
                },
                operation_name='GetEnrollmentStatus',
            )

            # But make the actual operation succeed so we test the warning path
            mock_client.get_ec2_instance_recommendations.return_value = {
                'instanceRecommendations': [],
                'nextToken': None,
            }
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            # Should succeed despite enrollment check failure
            assert result['status'] == 'success'
            # Should log the access denied warning
            mock_logger_instance.warning.assert_called_with(
                'Access denied for enrollment status check: An error occurred (AccessDeniedException) when calling the GetEnrollmentStatus operation: Access denied for enrollment'
            )

    async def test_enrollment_status_other_error_warning(self, mock_context):
        """Test enrollment status check with other error - covers lines 170, 174."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            # Make enrollment status check fail with a different error
            mock_client.get_enrollment_status.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'ServiceUnavailableException',
                        'Message': 'Service unavailable',
                    },
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 503},
                },
                operation_name='GetEnrollmentStatus',
            )

            # Make the actual operation succeed
            mock_client.get_ec2_instance_recommendations.return_value = {
                'instanceRecommendations': [],
                'nextToken': None,
            }
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            # Should succeed despite enrollment check failure
            assert result['status'] == 'success'
            # Should log the generic enrollment warning
            mock_logger_instance.warning.assert_called_with(
                'Could not check Compute Optimizer enrollment: An error occurred (ServiceUnavailableException) when calling the GetEnrollmentStatus operation: Service unavailable'
            )

    async def test_operation_opt_in_required_error(self, mock_context):
        """Test operation with OptInRequiredException - covers lines 230-280."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }

            # Make the operation fail with OptInRequiredException
            mock_client.get_ec2_instance_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'OptInRequiredException', 'Message': 'Opt-in required'},
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 400},
                },
                operation_name='GetEC2InstanceRecommendations',
            )
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            assert result['status'] == 'error'
            assert result['error_type'] == 'opt_in_required'
            assert 'Compute Optimizer requires opt-in' in result['message']
            assert 'Enable Compute Optimizer in the AWS Console' in result['resolution']
            mock_logger_instance.error.assert_called()

    async def test_operation_validation_exception_error(self, mock_context):
        """Test operation with ValidationException - covers lines 230-280."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }

            # Make the operation fail with ValidationException
            mock_client.get_ec2_instance_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter value'},
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 400},
                },
                operation_name='GetEC2InstanceRecommendations',
            )
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            assert result['status'] == 'error'
            assert result['error_type'] == 'validation_error'
            assert 'Compute Optimizer validation error' in result['message']
            assert 'Check your request parameters' in result['resolution']

    async def test_operation_throttling_exception_error(self, mock_context):
        """Test operation with ThrottlingException - covers lines 230-280."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }

            # Make the operation fail with ThrottlingException
            mock_client.get_ec2_instance_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'},
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 429},
                },
                operation_name='GetEC2InstanceRecommendations',
            )
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            assert result['status'] == 'error'
            assert result['error_type'] == 'throttling_error'
            assert 'API is throttling your requests' in result['message']
            assert 'Implement backoff retry logic' in result['resolution']

    async def test_operation_service_unavailable_exception_error(self, mock_context):
        """Test operation with ServiceUnavailableException - covers lines 230-280."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }

            # Make the operation fail with ServiceUnavailableException
            mock_client.get_ec2_instance_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'ServiceUnavailableException',
                        'Message': 'Service unavailable',
                    },
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 503},
                },
                operation_name='GetEC2InstanceRecommendations',
            )
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            assert result['status'] == 'error'
            assert result['error_type'] == 'service_unavailable'
            assert 'service is temporarily unavailable' in result['message']
            assert 'Retry after a brief wait' in result['resolution']

    async def test_operation_resource_not_found_exception_error(self, mock_context):
        """Test operation with ResourceNotFoundException - covers lines 230-280."""
        from botocore.exceptions import ClientError

        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_get_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }

            # Make the operation fail with ResourceNotFoundException
            mock_client.get_ec2_instance_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': 'Resource not found',
                    },
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 404},
                },
                operation_name='GetEC2InstanceRecommendations',
            )
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ec2_instance_recommendations')

            assert result['status'] == 'error'
            assert result['error_type'] == 'resource_not_found'
            assert 'The requested resource was not found' in result['message']
            assert 'Verify resource identifiers' in result['resolution']

    async def test_rds_recommendations_success_with_data(self, mock_context):
        """Test RDS recommendations success case."""
        mock_co_client = MagicMock()

        # Mock successful response with recommendations
        mock_co_client.get_rds_database_recommendations.return_value = {
            'rdsDBRecommendations': [
                {
                    'instanceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                    'instanceName': 'test-db',
                    'accountId': '123456789012',
                    'currentInstanceClass': 'db.r5.large',
                    'finding': 'OVER_PROVISIONED',
                    'lastRefreshTimestamp': None,
                    'recommendationOptions': [
                        {
                            'instanceClass': 'db.r5.medium',
                            'performanceRisk': 'LOW',
                            'savingsOpportunity': {
                                'savingsPercentage': 35.0,
                                'estimatedMonthlySavings': {
                                    'currency': 'USD',
                                    'value': 25.80,
                                },
                            },
                        }
                    ],
                }
            ],
            'nextToken': None,
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools.get_context_logger'
        ) as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.debug = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger_instance.error = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            result = await get_rds_recommendations(
                mock_context, mock_co_client, 10, None, None, None
            )

            assert result['status'] == 'success'
            assert len(result['data']['recommendations']) == 1


@pytest.mark.asyncio
class TestGetECSServiceRecommendations:
    """Tests for get_ecs_service_recommendations function."""

    async def test_basic_call(self, mock_context, mock_co_client):
        """Test basic call to get_ecs_service_recommendations."""
        from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
            get_ecs_service_recommendations,
        )

        # Mock ECS service recommendations response
        mock_co_client.get_ecs_service_recommendations.return_value = {
            'ecsServiceRecommendations': [
                {
                    'serviceArn': 'arn:aws:ecs:us-east-1:558889323918:service/fargate-test-cluster/FargateDemo',
                    'accountId': '558889323918',
                    'currentServiceConfiguration': {
                        'memory': 3072,
                        'cpu': 1024,
                        'containerConfigurations': [
                            {'containerName': 'demo1', 'memorySizeConfiguration': {}, 'cpu': 0}
                        ],
                        'autoScalingGroupArn': None,
                        'taskDefinitionArn': 'arn:aws:ecs:us-east-1:558889323918:task-definition/ECSFargateDemo:2',
                        'finding': 'Overprovisioned',
                        'currentPerformance': None,
                    },
                    'utilizationMetrics': [
                        {'name': 'Cpu', 'statistic': 'Maximum', 'value': 0.26},
                        {'name': 'Memory', 'statistic': 'Maximum', 'value': 3.0},
                    ],
                    'lookbackPeriodInDays': 14.0,
                    'launchType': 'Fargate',
                    'recommendationOptions': [
                        {
                            'memory': 512,
                            'cpu': 256,
                            'containerRecommendations': [
                                {'containerName': 'demo1', 'memorySizeConfiguration': {}, 'cpu': 0}
                            ],
                            'projectedPerformance': None,
                            'savingsOpportunity': {
                                'savingsPercentage': None,
                                'estimatedMonthlySavings': {'currency': 'USD', 'value': 30.275},
                            },
                        }
                    ],
                    'lastRefreshTimestamp': datetime(2025, 8, 20, 17, 3, 29),
                    'tags': [{'key': 'application', 'value': 'test-app'}],
                }
            ],
            'nextToken': None,
        }

        result = await get_ecs_service_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        # Verify the client was called correctly
        mock_co_client.get_ecs_service_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_ecs_service_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10

        # Verify response format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']

        # Verify recommendation format
        recommendations = result['data']['recommendations']
        assert len(recommendations) == 1
        recommendation = recommendations[0]

        assert (
            recommendation['service_arn']
            == 'arn:aws:ecs:us-east-1:558889323918:service/fargate-test-cluster/FargateDemo'
        )
        assert recommendation['account_id'] == '558889323918'
        assert recommendation['current_service_configuration']['memory'] == 3072
        assert recommendation['current_service_configuration']['cpu'] == 1024
        assert recommendation['launch_type'] == 'Fargate'

        # Verify utilization metrics are included
        assert 'utilization_metrics' in recommendation

        # Verify the recommendation options exist
        assert 'recommendation_options' in recommendation

    async def test_with_filters(self, mock_context, mock_co_client):
        """Test get_ecs_service_recommendations with filters."""
        from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
            get_ecs_service_recommendations,
        )

        # Setup
        filters = '[{"Name":"Finding","Values":["Overprovisioned"]}]'
        account_ids = '["558889323918"]'

        # Mock response
        mock_co_client.get_ecs_service_recommendations.return_value = {
            'ecsServiceRecommendations': [],
            'nextToken': None,
        }

        # Use patch to handle the parse_json calls
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            # Set up mock return values for parse_json calls
            mock_parse_json.side_effect = [
                [{'Name': 'Finding', 'Values': ['Overprovisioned']}],  # filters
                ['558889323918'],  # account_ids
            ]

            # Execute
            await get_ecs_service_recommendations(
                mock_context,
                mock_co_client,
                max_results=10,
                filters=filters,
                account_ids=account_ids,
                next_token='next-token',
            )

            # Assert
            mock_co_client.get_ecs_service_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_ecs_service_recommendations.call_args[1]

            assert 'filters' in call_kwargs
            assert 'accountIds' in call_kwargs
            assert call_kwargs['nextToken'] == 'next-token'


@pytest.mark.asyncio
class TestComputeOptimizerECSIntegration:
    """Integration tests for ECS service recommendations through main compute_optimizer function."""

    async def test_ecs_service_recommendations_success(self, mock_context):
        """Test successful ECS service recommendations operation."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            # Setup mocks
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ecsService'],
            }
            mock_client.get_ecs_service_recommendations.return_value = {
                'ecsServiceRecommendations': [],
                'nextToken': None,
            }
            mock_create_client.return_value = mock_client

            result = await real_fn(mock_context, operation='get_ecs_service_recommendations')
            assert result['status'] == 'success'

    async def test_ecs_service_recommendations_invalid_filter_error(self, mock_context):
        """Test ECS service recommendations with invalid filter."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ecsService'],
            }

            from botocore.exceptions import ClientError

            mock_client.get_ecs_service_recommendations.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'InvalidParameterValueException',
                        'Message': 'Invalid ECS service filter name.',
                    },
                    'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 400},
                },
                operation_name='GetECSServiceRecommendations',
            )
            mock_create_client.return_value = mock_client

            result = await real_fn(
                mock_context,
                operation='get_ecs_service_recommendations',
                filters='[{"Name":"InvalidFilter","Values":["test"]}]',
            )

            assert result['status'] == 'error'
            assert result['error_type'] == 'InvalidParameterValueException'
            assert 'Invalid ECS service filter name' in result['message']
