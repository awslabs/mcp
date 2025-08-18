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


# Test the main compute_optimizer function and the individual operation functions


# TestComputeOptimizer class removed since we can't directly test a FastMCP tool function
# Instead we'll focus on testing the individual recommendation functions that it calls


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
        mock_co_client.get_rds_instance_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_rds_instance_recommendations.call_args[1]
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
            mock_co_client.get_rds_instance_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_rds_instance_recommendations.call_args[1]

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

    # For FastMCP, we can simply verify that the object exists
    # and has the expected name and instructions
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
        """Test real compute_optimizer resource not enrolled error with identity decorator."""
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
            mock_create_client.return_value = mock_client

            res = await real_fn(mock_context, operation='get_ec2_instance_recommendations')
            assert res['status'] == 'error'
            assert res['data']['error_type'] == 'resource_not_enrolled'
            assert 'EC2 instances are not enrolled' in res['message']

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
