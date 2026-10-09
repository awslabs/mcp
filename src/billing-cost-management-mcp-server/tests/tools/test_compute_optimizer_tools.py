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
    get_ecs_service_recommendations,
    get_idle_recommendations,
    get_lambda_function_recommendations,
    get_rds_recommendations,
)
from datetime import datetime, timedelta, timezone
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
                'idle': 'False',
                'instanceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abcdef1234567890',
                'instanceName': 'test-instance',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'instanceType': 't2.nano',
                        'performanceRisk': 'LOW',
                        'rank': 1,
                        'projectedUtilizationMetrics': [
                            {'name': 'CPU', 'statistic': 'MAXIMUM', 'value': 45.0}
                        ],
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 30.0,
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
                'currentConfiguration': {
                    'instanceType': 't3.medium',
                },
                'finding': 'NOT_OPTIMIZED',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationOptions': [
                    {
                        'configuration': {
                            'instanceType': 't3.small',
                        },
                        'performanceRisk': 'MEDIUM',
                        'rank': 1,
                        'projectedUtilizationMetrics': [
                            {'name': 'CPU', 'statistic': 'MAXIMUM', 'value': 60.0}
                        ],
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 25.0,
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
                'volumeRecommendationOptions': [
                    {
                        'configuration': {
                            'volumeType': 'gp3',
                            'volumeSize': 50,
                            'volumeBaselineIOPS': 3000,
                        },
                        'performanceRisk': 'LOW',
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 40.0,
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
                'functionVersion': '$LATEST',
                'finding': 'OVER_PROVISIONED',
                'currentMemorySize': 1024,
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'memorySizeRecommendationOptions': [
                    {
                        'memorySize': 512,
                        'rank': 1,
                        'projectedUtilizationMetrics': [
                            {'name': 'Duration', 'statistic': 'Average', 'value': 60.0}
                        ],
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 50.0,
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
                'resourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                'engine': 'mysql',
                'engineVersion': '8.0.45',
                'currentDBInstanceClass': 'db.r5.large',
                'idle': 'False',
                'instanceFinding': 'OVER_PROVISIONED',
                'storageFinding': 'Optimized',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'instanceRecommendationOptions': [
                    {
                        'dbInstanceClass': 'db.r5.medium',
                        'performanceRisk': 'LOW',
                        'rank': 1,
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 35.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 25.80,
                            },
                        },
                    }
                ],
                'effectiveRecommendationPreferences': {
                    'lookBackPeriod': 'DAYS_14',
                    'savingsEstimationMode': {'source': 'CostOptimizationHub'},
                },
                'lookbackPeriodInDays': 14.0,
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
                            'savingsOpportunityPercentage': 35.0,
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

    mock_client.get_idle_recommendations.return_value = {
        'idleRecommendations': [
            {
                'accountId': '123456789012',
                'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:volume/vol-0abcdef1234567890',
                'resourceId': 'vol-0abcdef1234567890',
                'resourceType': 'EBSVolume',
                'finding': 'Unattached',
                'findingDescription': 'EBS Volume is unattached.',
                'lookBackPeriodInDays': 14.0,
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'savingsOpportunity': {
                    'savingsOpportunityPercentage': 100.0,
                    'estimatedMonthlySavings': {
                        'currency': 'USD',
                        'value': 12.50,
                    },
                },
                'savingsOpportunityAfterDiscounts': {
                    'savingsOpportunityPercentage': 90.0,
                    'estimatedMonthlySavings': {
                        'currency': 'USD',
                        'value': 11.25,
                    },
                },
                'utilizationMetrics': [
                    {
                        'name': 'VolumeReadOpsPerSecond',
                        'statistic': 'Maximum',
                        'value': 0.0,
                        'dimensions': [{'key': 'GlobalSecondaryIndexName', 'values': ['gsi-1']}],
                    }
                ],
                'tags': [{'key': 'env', 'value': 'test'}],
            }
        ],
        'errors': [],
        'nextToken': 'next-token-idle',
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
        # Keys, name, and value casing are folded onto what the API accepts.
        assert call_kwargs['filters'] == [{'name': 'Finding', 'values': ['Overprovisioned']}]
        assert call_kwargs['accountIds'] == json.loads(account_ids)
        assert call_kwargs['nextToken'] == next_token

        # Check result format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']
        assert len(result['data']['recommendations']) == 1
        assert result['data']['next_token'] == 'next-token-123'

        recommendation = result['data']['recommendations'][0]
        assert recommendation['current_instance']['instance_type'] == 't3.micro'
        assert recommendation['current_instance']['idle'] == 'False'

        option = recommendation['recommendation_options'][0]
        assert option['instance_type'] == 't2.nano'
        assert option['projected_utilization_metrics'][0]['value'] == 45.0
        assert option['savings_opportunity']['savings_percentage'] == 30.0


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

        option = recommendation['recommendation_options'][0]
        assert option['instance_type'] == 't3.small'
        assert option['projected_utilization_metrics'][0]['value'] == 60.0
        assert option['savings_opportunity']['savings_percentage'] == 25.0

    async def test_with_filters(self, mock_context, mock_co_client):
        """Test get_auto_scaling_group_recommendations with filters, account IDs, and next token."""
        filters = '[{"Name":"Finding","Values":["NOT_OPTIMIZED"]}]'
        account_ids = '["123456789012"]'

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            mock_parse_json.side_effect = [
                [{'Name': 'Finding', 'Values': ['NOT_OPTIMIZED']}],  # filters
                ['123456789012'],  # account_ids
            ]

            await get_auto_scaling_group_recommendations(
                mock_context,
                mock_co_client,
                max_results=10,
                filters=filters,
                account_ids=account_ids,
                next_token='next-page',
            )

            mock_co_client.get_auto_scaling_group_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_auto_scaling_group_recommendations.call_args[1]
            assert 'filters' in call_kwargs
            assert 'accountIds' in call_kwargs
            assert call_kwargs['nextToken'] == 'next-page'


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

        # Verify the recommendation options are parsed
        recommendation = result['data']['recommendations'][0]
        assert len(recommendation['recommendation_options']) == 1
        option = recommendation['recommendation_options'][0]
        assert option['volume_type'] == 'gp3'
        assert option['volume_size'] == 50
        assert option['volume_baseline_iops'] == 3000
        assert option['performance_risk'] == 'LOW'
        assert option['savings_opportunity']['savings_percentage'] == 40.0

    async def test_with_filters(self, mock_context, mock_co_client):
        """Test get_ebs_volume_recommendations with filters, account IDs, and next token."""
        filters = '[{"Name":"Finding","Values":["OVERPROVISIONED"]}]'
        account_ids = '["123456789012"]'

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            mock_parse_json.side_effect = [
                [{'Name': 'Finding', 'Values': ['OVERPROVISIONED']}],  # filters
                ['123456789012'],  # account_ids
            ]

            await get_ebs_volume_recommendations(
                mock_context,
                mock_co_client,
                max_results=10,
                filters=filters,
                account_ids=account_ids,
                next_token='next-page',
            )

            mock_co_client.get_ebs_volume_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_ebs_volume_recommendations.call_args[1]
            assert 'filters' in call_kwargs
            assert 'accountIds' in call_kwargs
            assert call_kwargs['nextToken'] == 'next-page'


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
        # function_name is derived from the ARN (no functionName field in the API)
        assert recommendation['function_name'] == 'test-function'
        assert recommendation['account_id'] == '123456789012'
        assert recommendation['current_configuration']['memory_size'] == 1024
        assert recommendation['current_configuration']['finding'] == 'OVER_PROVISIONED'

        # Verify the recommendation options
        assert len(recommendation['recommendation_options']) == 1
        option = recommendation['recommendation_options'][0]
        assert option['memory_size'] == 512
        assert option['projected_utilization_metrics'][0]['value'] == 60.0
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

    async def test_function_name_derived_from_arn(self, mock_context, mock_co_client):
        """function_name is derived from the ARN, handling version/alias suffixes."""
        mock_co_client.get_lambda_function_recommendations.return_value = {
            'lambdaFunctionRecommendations': [
                {
                    'accountId': '123456789012',
                    # ARN carries a trailing :version — name must still be the function segment
                    'functionArn': 'arn:aws:lambda:us-east-1:123456789012:function:my-fn:PROD',
                    'currentMemorySize': 512,
                    'finding': 'OPTIMIZED',
                    'memorySizeRecommendationOptions': [],
                },
                {
                    # No ARN at all -> name should be None, not an error
                    'accountId': '123456789012',
                    'currentMemorySize': 256,
                    'finding': 'OPTIMIZED',
                    'memorySizeRecommendationOptions': [],
                },
            ],
        }

        result = await get_lambda_function_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        recs = result['data']['recommendations']
        assert recs[0]['function_name'] == 'my-fn'
        assert recs[1]['function_name'] is None


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
        assert recommendation['current_configuration']['instance_finding'] == 'OVER_PROVISIONED'

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
        filters = '[{"Name":"InstanceFinding","Values":["Overprovisioned"]}]'
        account_ids = '["123456789012"]'

        # Use patch to handle the parse_json calls
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            # Set up mock return values for parse_json calls
            mock_parse_json.side_effect = [
                [{'Name': 'InstanceFinding', 'Values': ['Overprovisioned']}],  # filters
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


@pytest.mark.asyncio
class TestGetIdleRecommendations:
    """Tests for get_idle_recommendations function."""

    async def test_basic_call(self, mock_context, mock_co_client):
        """Test basic call to get_idle_recommendations."""
        result = await get_idle_recommendations(
            mock_context,
            mock_co_client,
            max_results=10,
            filters=None,
            account_ids=None,
            next_token=None,
        )

        # Verify the client was called correctly
        mock_co_client.get_idle_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_idle_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10

        # Verify response format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']
        assert result['data']['errors'] == []
        assert result['data']['next_token'] == 'next-token-idle'

        recommendations = result['data']['recommendations']
        assert len(recommendations) == 1
        recommendation = recommendations[0]

        assert (
            recommendation['resource_arn']
            == 'arn:aws:ec2:us-east-1:123456789012:volume/vol-0abcdef1234567890'
        )
        assert recommendation['resource_id'] == 'vol-0abcdef1234567890'
        assert recommendation['resource_type'] == 'EBSVolume'
        assert recommendation['account_id'] == '123456789012'
        assert recommendation['finding'] == 'Unattached'
        assert recommendation['finding_description'] == 'EBS Volume is unattached.'
        assert recommendation['lookback_period_in_days'] == 14.0
        assert recommendation['tags'] == [{'key': 'env', 'value': 'test'}]

        assert recommendation['savings_opportunity']['savings_percentage'] == 100.0
        assert (
            recommendation['savings_opportunity']['estimated_monthly_savings']['currency'] == 'USD'
        )
        assert recommendation['savings_opportunity']['estimated_monthly_savings']['value'] == 12.50
        assert recommendation['savings_opportunity_after_discounts']['savings_percentage'] == 90.0

        assert len(recommendation['utilization_metrics']) == 1
        metric = recommendation['utilization_metrics'][0]
        assert metric['name'] == 'VolumeReadOpsPerSecond'
        assert metric['statistic'] == 'Maximum'
        assert metric['value'] == 0.0
        assert metric['dimensions'] == [{'key': 'GlobalSecondaryIndexName', 'values': ['gsi-1']}]

    async def test_with_filters(self, mock_context, mock_co_client):
        """Test get_idle_recommendations with filters, account IDs, and next token."""
        filters = '[{"name":"Finding","values":["Unattached"]}]'
        account_ids = '["123456789012"]'

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools.parse_json'
        ) as mock_parse_json:
            mock_parse_json.side_effect = [
                [{'name': 'Finding', 'values': ['Unattached']}],  # filters
                ['123456789012'],  # account_ids
            ]

            await get_idle_recommendations(
                mock_context,
                mock_co_client,
                max_results=10,
                filters=filters,
                account_ids=account_ids,
                next_token='next-page-idle',
            )

            mock_co_client.get_idle_recommendations.assert_called_once()
            call_kwargs = mock_co_client.get_idle_recommendations.call_args[1]
            assert call_kwargs['filters'] == [{'name': 'Finding', 'values': ['Unattached']}]
            assert call_kwargs['accountIds'] == ['123456789012']
            assert call_kwargs['nextToken'] == 'next-page-idle'

    async def test_resource_type_filter_normalized_to_idle_casing(
        self, mock_context, mock_co_client
    ):
        """Passed ResourceType and Finding values are normalized to the idle enum spelling."""
        filters = json.dumps(
            [
                {'name': 'ResourceType', 'values': ['EbsVolume', 'ec2instance', 'NatGateway']},
                {'name': 'Finding', 'values': ['unattached', 'IDLE', 'Unused']},
            ]
        )

        result = await get_idle_recommendations(
            mock_context,
            mock_co_client,
            max_results=None,
            filters=filters,
            account_ids=None,
            next_token=None,
        )

        expected = [
            {'name': 'ResourceType', 'values': ['EBSVolume', 'EC2Instance', 'NatGateway']},
            {'name': 'Finding', 'values': ['Unattached', 'Idle', 'Unused']},
        ]
        call_kwargs = mock_co_client.get_idle_recommendations.call_args[1]
        assert call_kwargs['filters'] == expected
        assert result['status'] == 'success'
        assert result['data']['applied_filters'] == expected

    async def test_unknown_resource_type_passed_through(self, mock_context, mock_co_client):
        """Values the installed model doesn't know (or non-strings) are forwarded unchanged."""
        filters = json.dumps([{'name': 'ResourceType', 'values': ['SomeFutureType', 42]}])

        await get_idle_recommendations(mock_context, mock_co_client, None, filters, None, None)

        call_kwargs = mock_co_client.get_idle_recommendations.call_args[1]
        assert call_kwargs['filters'] == [
            {'name': 'ResourceType', 'values': ['SomeFutureType', 42]}
        ]

    async def test_unrelated_filter_names_passed_through(self, mock_context, mock_co_client):
        """Filters without a known enum (other names, non-dict entries) are left untouched."""
        filters = json.dumps([{'name': 'SomethingElse', 'values': ['ebsvolume']}, 'raw'])

        await get_idle_recommendations(mock_context, mock_co_client, None, filters, None, None)

        call_kwargs = mock_co_client.get_idle_recommendations.call_args[1]
        assert call_kwargs['filters'] == [
            {'name': 'SomethingElse', 'values': ['ebsvolume']},
            'raw',
        ]

    async def test_invalid_parameter_value_returns_valid_enum(self, mock_context, mock_co_client):
        """InvalidParameterValueException is returned with the valid ResourceType/Finding sets."""
        from botocore.exceptions import ClientError

        mock_co_client.get_idle_recommendations.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidParameterValueException',
                    'Message': 'Invalid filter value',
                }
            },
            'GetIdleRecommendations',
        )
        filters = json.dumps([{'name': 'ResourceType', 'values': ['LambdaFunction']}])

        result = await get_idle_recommendations(
            mock_context, mock_co_client, None, filters, None, None
        )

        assert result['status'] == 'error'
        assert result['service'] == 'Compute Optimizer'
        assert result['operation'] == 'get_idle_recommendations'
        assert result['error_type'] == 'InvalidParameterValueException'
        assert result['data']['submitted_filters'] == [
            {'name': 'ResourceType', 'values': ['LambdaFunction']}
        ]
        valid = result['data']['valid_filters']['ResourceType']
        assert 'EBSVolume' in valid
        assert 'LambdaFunction' not in valid
        assert result['data']['valid_filters']['Finding'] == ['Idle', 'Unattached', 'Unused']
        # Pre-existing idle error keys are kept for backward compatibility.
        assert result['data']['error_type'] == 'invalid_parameter_value'
        assert result['data']['operation'] == 'get_idle_recommendations'
        assert result['data']['filters'] == [
            {'name': 'ResourceType', 'values': ['LambdaFunction']}
        ]
        legacy_valid = result['data']['valid_resource_type_values']
        assert 'EBSVolume' in legacy_valid
        assert 'LambdaFunction' not in legacy_valid
        assert result['data']['valid_finding_values'] == ['Idle', 'Unattached', 'Unused']

    async def test_other_client_errors_propagate(self, mock_context, mock_co_client):
        """Non-InvalidParameterValue errors still reach the dispatcher's error ladder."""
        from botocore.exceptions import ClientError

        mock_co_client.get_idle_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'slow down'}},
            'GetIdleRecommendations',
        )

        with pytest.raises(ClientError):
            await get_idle_recommendations(mock_context, mock_co_client, None, None, None, None)


class TestIdleEnumCanonicalMap:
    """Tests for the model-driven idle ResourceType/Finding normalization maps."""

    def test_values_come_from_service_model(self):
        """Canonical values are read from the installed botocore model, not a literal."""
        import botocore.session

        mod = importlib.import_module(
            'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools'
        )
        model_enum = (
            botocore.session.get_session()
            .get_service_model('compute-optimizer')
            .shape_for('IdleRecommendationResourceType')
            .enum
        )

        mod._idle_enum_canonical_map.cache_clear()
        mapping = mod._idle_enum_canonical_map('IdleRecommendationResourceType')

        assert sorted(mapping.values()) == sorted(model_enum)
        assert mapping['ebsvolume'] == 'EBSVolume'
        assert mapping['rdsdbinstance'] == 'RDSDBInstance'
        # Case-folding must be collision-free for the fold to be deterministic.
        assert len(mapping) == len(model_enum)
        mod._idle_enum_canonical_map.cache_clear()

    def test_finding_values_come_from_service_model(self):
        """The Finding map is read from the model's IdleFinding enum."""
        mod = importlib.import_module(
            'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools'
        )

        mod._idle_enum_canonical_map.cache_clear()
        mapping = mod._idle_enum_canonical_map(mod._IDLE_FILTER_ENUM_SHAPES['Finding'])

        assert mapping == {'idle': 'Idle', 'unattached': 'Unattached', 'unused': 'Unused'}
        mod._idle_enum_canonical_map.cache_clear()

    def test_model_load_failure_skips_normalization(self):
        """A model load failure yields an empty map and filters pass through untouched."""
        mod = importlib.import_module(
            'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools'
        )
        filters = [{'name': 'ResourceType', 'values': ['EbsVolume']}]

        mod._idle_enum_canonical_map.cache_clear()
        with patch('botocore.session.Session.get_service_model', side_effect=RuntimeError('boom')):
            assert mod._idle_enum_canonical_map('IdleRecommendationResourceType') == {}
            assert mod._normalize_idle_filters(filters) == filters
        mod._idle_enum_canonical_map.cache_clear()

    def test_model_without_enum_skips_normalization(self):
        """A shape with no enum yields an empty map rather than raising."""
        mod = importlib.import_module(
            'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools'
        )
        service_model = MagicMock()
        service_model.shape_for.return_value.enum = None

        mod._idle_enum_canonical_map.cache_clear()
        with patch('botocore.session.Session.get_service_model', return_value=service_model):
            assert mod._idle_enum_canonical_map('IdleFinding') == {}
        mod._idle_enum_canonical_map.cache_clear()


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_format_savings_opportunity(self):
        """Test format_savings_opportunity function."""
        # Test with complete data
        savings = {
            'savingsOpportunityPercentage': 50.0,
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

    def test_format_timestamp_normalizes_aware_datetime_to_utc(self):
        """Test format_timestamp converts timezone-aware input to UTC."""
        aware = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        assert format_timestamp(aware) == '2023-01-01T17:00:00'

    def test_format_timestamp_accepts_epoch_seconds(self):
        """Test format_timestamp accepts epoch seconds."""
        assert format_timestamp(1672574400) == '2023-01-01T12:00:00'

    def test_format_timestamp_preserves_epoch_zero(self):
        """Test format_timestamp treats epoch 0 as a value, not as absent."""
        assert format_timestamp(0) == '1970-01-01T00:00:00'


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

    async def test_co_real_get_ebs_volume_recommendations_reload_identity_decorator(
        self, mock_context
    ):
        """Test real compute_optimizer get_ebs_volume_recommendations dispatch."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_ebs_volume_recommendations', new_callable=AsyncMock
            ) as mock_impl,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ebsVolume'],
            }
            mock_create_client.return_value = mock_client
            mock_impl.return_value = {'status': 'success', 'data': {'recommendations': []}}

            res = await real_fn(
                mock_context, operation='get_ebs_volume_recommendations', max_results=50
            )
            assert res['status'] == 'success'
            mock_impl.assert_awaited_once()

    async def test_co_real_get_lambda_function_recommendations_reload_identity_decorator(
        self, mock_context
    ):
        """Test real compute_optimizer get_lambda_function_recommendations dispatch."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_lambda_function_recommendations', new_callable=AsyncMock
            ) as mock_impl,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['lambdaFunction'],
            }
            mock_create_client.return_value = mock_client
            mock_impl.return_value = {'status': 'success', 'data': {'recommendations': []}}

            res = await real_fn(
                mock_context, operation='get_lambda_function_recommendations', max_results=50
            )
            assert res['status'] == 'success'
            mock_impl.assert_awaited_once()

    async def test_co_real_get_rds_recommendations_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer get_rds_recommendations dispatch."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(co_mod, 'get_rds_recommendations', new_callable=AsyncMock) as mock_impl,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['rdsDBInstance'],
            }
            mock_create_client.return_value = mock_client
            mock_impl.return_value = {'status': 'success', 'data': {'recommendations': []}}

            res = await real_fn(mock_context, operation='get_rds_recommendations', max_results=50)
            assert res['status'] == 'success'
            mock_impl.assert_awaited_once()

    async def test_co_real_get_idle_recommendations_reload_identity_decorator(self, mock_context):
        """Test real compute_optimizer get_idle_recommendations dispatch."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(co_mod, 'get_idle_recommendations', new_callable=AsyncMock) as mock_impl,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ebsVolume'],
            }
            mock_create_client.return_value = mock_client
            mock_impl.return_value = {'status': 'success', 'data': {'recommendations': []}}

            res = await real_fn(mock_context, operation='get_idle_recommendations', max_results=50)
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

    async def test_co_region_parameter_passed_to_client(self, mock_context):
        """Test that the region parameter is passed to create_aws_client."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        real_fn = co_mod.compute_optimizer

        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_ec2_instance_recommendations', new_callable=AsyncMock
            ) as mock_get,
        ):
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {
                'status': 'ACTIVE',
                'resourceTypes': ['ec2Instance'],
            }
            mock_create_client.return_value = mock_client
            mock_get.return_value = {'status': 'success', 'data': {'recommendations': []}}

            await real_fn(
                mock_context,
                operation='get_ec2_instance_recommendations',
                region='eu-west-1',
            )
            mock_create_client.assert_called_once_with(
                'compute-optimizer', region_name='eu-west-1'
            )


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
                    'resourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                    'accountId': '123456789012',
                    'engine': 'mysql',
                    'engineVersion': '8.0.45',
                    'currentDBInstanceClass': 'db.r5.large',
                    'idle': 'False',
                    'instanceFinding': 'OVER_PROVISIONED',
                    'storageFinding': 'Optimized',
                    'lastRefreshTimestamp': None,
                    'instanceRecommendationOptions': [
                        {
                            'dbInstanceClass': 'db.r5.medium',
                            'performanceRisk': 'LOW',
                            'rank': 1,
                            'savingsOpportunity': {
                                'savingsOpportunityPercentage': 35.0,
                                'estimatedMonthlySavings': {
                                    'currency': 'USD',
                                    'value': 25.80,
                                },
                            },
                        }
                    ],
                    'storageRecommendationOptions': [
                        {
                            'storageConfiguration': {
                                'storageType': 'gp3',
                                'allocatedStorage': 100,
                            },
                            'rank': 1,
                            'savingsOpportunity': {
                                'savingsOpportunityPercentage': 20.0,
                                'estimatedMonthlySavings': {
                                    'currency': 'USD',
                                    'value': 12.50,
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

            # Verify the storage recommendation options are parsed
            recommendation = result['data']['recommendations'][0]
            storage_options = recommendation['storage_recommendation_options']
            assert len(storage_options) == 1
            assert storage_options[0]['storage_configuration']['storageType'] == 'gp3'
            assert storage_options[0]['rank'] == 1
            assert storage_options[0]['savings_opportunity']['savings_percentage'] == 20.0


@pytest.mark.asyncio
class TestComputeOptimizerNoMaxResults:
    """Verify the functions handle a falsy max_results (no maxResults sent)."""

    async def test_recommendations_without_max_results(self, mock_context, mock_co_client):
        """Each recommendation function omits maxResults when max_results is None."""
        funcs = [
            (
                get_auto_scaling_group_recommendations,
                mock_co_client.get_auto_scaling_group_recommendations,
            ),
            (get_ebs_volume_recommendations, mock_co_client.get_ebs_volume_recommendations),
            (
                get_lambda_function_recommendations,
                mock_co_client.get_lambda_function_recommendations,
            ),
            (get_rds_recommendations, mock_co_client.get_rds_database_recommendations),
        ]
        for func, client_method in funcs:
            client_method.reset_mock()
            result = await func(
                mock_context,
                mock_co_client,
                max_results=None,
                filters=None,
                account_ids=None,
                next_token=None,
            )
            assert result['status'] == 'success'
            # maxResults must NOT be sent when max_results is falsy
            assert 'maxResults' not in client_method.call_args[1]


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
                        'autoScalingConfiguration': 'TargetTrackingScalingCpu',
                        'taskDefinitionArn': 'arn:aws:ecs:us-east-1:558889323918:task-definition/ECSFargateDemo:2',
                    },
                    'finding': 'Overprovisioned',
                    'currentPerformanceRisk': 'Low',
                    'utilizationMetrics': [
                        {'name': 'Cpu', 'statistic': 'Maximum', 'value': 0.26},
                        {'name': 'Memory', 'statistic': 'Maximum', 'value': 3.0},
                    ],
                    'lookbackPeriodInDays': 14.0,
                    'launchType': 'Fargate',
                    'serviceRecommendationOptions': [
                        {
                            'memory': 512,
                            'cpu': 256,
                            'containerRecommendations': [
                                {'containerName': 'demo1', 'memorySizeConfiguration': {}, 'cpu': 0}
                            ],
                            'projectedUtilizationMetrics': [
                                {
                                    'name': 'Cpu',
                                    'statistic': 'Maximum',
                                    'lowerBoundValue': 0.5,
                                    'upperBoundValue': 0.8,
                                }
                            ],
                            'savingsOpportunity': {
                                'savingsOpportunityPercentage': None,
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
        current_config = recommendation['current_service_configuration']
        assert current_config['memory'] == 3072
        assert current_config['cpu'] == 1024
        assert current_config['auto_scaling_configuration'] == 'TargetTrackingScalingCpu'
        assert current_config['finding'] == 'Overprovisioned'
        assert current_config['current_performance_risk'] == 'Low'
        assert recommendation['launch_type'] == 'Fargate'

        # Verify utilization metrics are included
        assert 'utilization_metrics' in recommendation

        # Verify the recommendation options are parsed
        assert len(recommendation['recommendation_options']) == 1
        option = recommendation['recommendation_options'][0]
        assert option['memory'] == 512
        assert option['cpu'] == 256
        assert option['projected_utilization_metrics'][0]['name'] == 'Cpu'
        assert option['projected_utilization_metrics'][0]['upperBoundValue'] == 0.8
        assert option['savings_opportunity']['estimated_monthly_savings']['value'] == 30.275

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


@pytest.mark.asyncio
class TestComputeOptimizerResourceArns:
    """Tests for querying recommendations by resource ARN."""

    EC2_ARN = 'arn:aws:ec2:us-west-2:123456789012:instance/i-0abcdef1234567890'

    @pytest.mark.parametrize(
        'func_name,client_method,arn_key',
        [
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                'instanceArns',
            ),
            (
                'get_auto_scaling_group_recommendations',
                'get_auto_scaling_group_recommendations',
                'autoScalingGroupArns',
            ),
            ('get_ebs_volume_recommendations', 'get_ebs_volume_recommendations', 'volumeArns'),
            (
                'get_lambda_function_recommendations',
                'get_lambda_function_recommendations',
                'functionArns',
            ),
            ('get_rds_recommendations', 'get_rds_database_recommendations', 'resourceArns'),
            ('get_ecs_service_recommendations', 'get_ecs_service_recommendations', 'serviceArns'),
            ('get_idle_recommendations', 'get_idle_recommendations', 'resourceArns'),
        ],
    )
    async def test_arns_sent_as_operation_parameter(
        self, mock_context, func_name, client_method, arn_key
    ):
        """Each operation sends the ARNs under its own AWS parameter name."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        client = MagicMock()
        getattr(client, client_method).return_value = {}
        func = getattr(compute_optimizer_tools, func_name)

        await func(mock_context, client, None, None, None, None, [self.EC2_ARN])

        assert getattr(client, client_method).call_args[1][arn_key] == [self.EC2_ARN]

    async def test_arns_omitted_when_not_provided(self, mock_context, mock_co_client):
        """No ARN parameter is sent when resource_arns is not given."""
        await get_ec2_instance_recommendations(
            mock_context, mock_co_client, None, None, None, None
        )

        assert 'instanceArns' not in mock_co_client.get_ec2_instance_recommendations.call_args[1]

    async def _call_tool(self, mock_context, **kwargs):
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(
                co_mod, 'get_ec2_instance_recommendations', new_callable=AsyncMock
            ) as mock_get,
        ):
            mock_get_logger.return_value = AsyncMock()
            mock_client = MagicMock()
            mock_client.get_enrollment_status.return_value = {'status': 'ACTIVE'}
            mock_create_client.return_value = mock_client
            mock_get.return_value = {'status': 'success', 'data': {}}

            result = await co_mod.compute_optimizer(
                mock_context, operation='get_ec2_instance_recommendations', **kwargs
            )
            return result, mock_create_client, mock_get

    async def test_tool_parses_arns_and_infers_region(self, mock_context):
        """The ARN list is passed through and the region is taken from the ARNs."""
        result, mock_create_client, mock_get = await self._call_tool(
            mock_context, resource_arns=json.dumps([self.EC2_ARN])
        )

        assert result['status'] == 'success'
        mock_create_client.assert_called_once_with('compute-optimizer', region_name='us-west-2')
        assert mock_get.call_args[0][-1] == [self.EC2_ARN]

    async def test_tool_accepts_bare_arn(self, mock_context):
        """A single unwrapped ARN is treated as a one-element list."""
        _, _, mock_get = await self._call_tool(mock_context, resource_arns=self.EC2_ARN)

        assert mock_get.call_args[0][-1] == [self.EC2_ARN]

    async def test_tool_keeps_matching_explicit_region(self, mock_context):
        """An explicit region that matches the ARNs is used as-is."""
        _, mock_create_client, _ = await self._call_tool(
            mock_context, region='us-west-2', resource_arns=json.dumps([self.EC2_ARN])
        )

        mock_create_client.assert_called_once_with('compute-optimizer', region_name='us-west-2')

    async def test_tool_rejects_region_mismatch(self, mock_context):
        """An explicit region that differs from the ARNs' region is rejected."""
        result, mock_create_client, _ = await self._call_tool(
            mock_context, region='us-east-1', resource_arns=json.dumps([self.EC2_ARN])
        )

        assert result['error_type'] == 'validation_error'
        assert 'us-west-2' in result['message']
        mock_create_client.assert_not_called()

    async def test_tool_rejects_multiple_regions(self, mock_context):
        """ARNs from more than one region are rejected."""
        other = 'arn:aws:ec2:eu-west-1:123456789012:instance/i-0fedcba9876543210'
        result, _, _ = await self._call_tool(
            mock_context, resource_arns=json.dumps([self.EC2_ARN, other])
        )

        assert result['error_type'] == 'validation_error'
        assert 'multiple regions' in result['message']

    @pytest.mark.parametrize('bad', ['{"arn": "x"}', '["not-an-arn"]', '[1]', 'not json'])
    async def test_tool_rejects_invalid_arns(self, mock_context, bad):
        """Non-list or non-ARN values are rejected."""
        result, _, _ = await self._call_tool(mock_context, resource_arns=bad)

        assert result['error_type'] == 'validation_error'


@pytest.mark.asyncio
class TestComputeOptimizerFilterNormalization:
    """Filter casing, structured errors, and local validation across all operations."""

    OPS = [
        ('get_ec2_instance_recommendations', 'get_ec2_instance_recommendations'),
        ('get_auto_scaling_group_recommendations', 'get_auto_scaling_group_recommendations'),
        ('get_ebs_volume_recommendations', 'get_ebs_volume_recommendations'),
        ('get_lambda_function_recommendations', 'get_lambda_function_recommendations'),
        ('get_rds_recommendations', 'get_rds_database_recommendations'),
        ('get_ecs_service_recommendations', 'get_ecs_service_recommendations'),
        ('get_idle_recommendations', 'get_idle_recommendations'),
    ]

    async def _call(self, mock_context, func_name, client_method, **kwargs):
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        client = MagicMock()
        getattr(client, client_method).return_value = {}
        args = {'max_results': None, 'filters': None, 'account_ids': None, 'next_token': None}
        args.update(kwargs)
        result = await getattr(compute_optimizer_tools, func_name)(mock_context, client, **args)
        return result, getattr(client, client_method)

    @pytest.mark.parametrize(
        'func_name,client_method,submitted,expected',
        [
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                [{'Name': 'finding', 'Values': ['overprovisioned', 'OPTIMIZED']}],
                [{'name': 'Finding', 'values': ['Overprovisioned', 'Optimized']}],
            ),
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                [{'name': 'findingreasoncode', 'values': ['cpuoverprovisioned']}],
                [{'name': 'FindingReasonCodes', 'values': ['CPUOverprovisioned']}],
            ),
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                [
                    {
                        'name': 'FindingReasonCodes',
                        'values': ['gpuoverprovisioned', 'GPU_MEMORY_UNDERPROVISIONED'],
                    }
                ],
                [
                    {
                        'name': 'FindingReasonCodes',
                        'values': ['GPUOverprovisioned', 'GPUMemoryUnderprovisioned'],
                    }
                ],
            ),
            (
                'get_auto_scaling_group_recommendations',
                'get_auto_scaling_group_recommendations',
                [{'name': 'Finding', 'values': ['notoptimized']}],
                [{'name': 'Finding', 'values': ['NotOptimized']}],
            ),
            (
                'get_ebs_volume_recommendations',
                'get_ebs_volume_recommendations',
                [{'name': 'FINDING', 'values': ['optimized']}],
                [{'name': 'Finding', 'values': ['Optimized']}],
            ),
            (
                'get_lambda_function_recommendations',
                'get_lambda_function_recommendations',
                [{'name': 'FindingReasonCodes', 'values': ['memoryoverprovisioned']}],
                [{'name': 'FindingReasonCode', 'values': ['MemoryOverprovisioned']}],
            ),
            (
                'get_rds_recommendations',
                'get_rds_database_recommendations',
                [{'name': 'storagefinding', 'values': ['notoptimized']}],
                [{'name': 'StorageFinding', 'values': ['NotOptimized']}],
            ),
            (
                'get_ecs_service_recommendations',
                'get_ecs_service_recommendations',
                [{'name': 'finding', 'values': ['UNDERPROVISIONED']}],
                [{'name': 'Finding', 'values': ['Underprovisioned']}],
            ),
            (
                'get_idle_recommendations',
                'get_idle_recommendations',
                [{'name': 'resourcetype', 'values': ['ebsvolume']}],
                [{'name': 'ResourceType', 'values': ['EBSVolume']}],
            ),
        ],
    )
    async def test_casing_is_folded_and_echoed(
        self, mock_context, func_name, client_method, submitted, expected
    ):
        """Names, values, and Name/Values keys are folded and echoed as applied_filters."""
        result, method = await self._call(
            mock_context, func_name, client_method, filters=json.dumps(submitted)
        )

        assert method.call_args[1]['filters'] == expected
        assert result['status'] == 'success'
        assert result['data']['applied_filters'] == expected

    async def test_unmatched_values_and_tag_filters_pass_through(self, mock_context):
        """Unknown values and tag filters are not rewritten."""
        submitted = [
            {'name': 'Finding', 'values': ['SomeFutureFinding']},
            {'name': 'Tag:Owner', 'values': ['TeamA']},
            {'name': 'TAG-KEY', 'values': ['CostCenter']},
        ]
        _, method = await self._call(
            mock_context,
            'get_ec2_instance_recommendations',
            'get_ec2_instance_recommendations',
            filters=json.dumps(submitted),
        )

        assert method.call_args[1]['filters'] == [
            {'name': 'Finding', 'values': ['SomeFutureFinding']},
            {'name': 'tag:Owner', 'values': ['TeamA']},
            {'name': 'tag-key', 'values': ['CostCenter']},
        ]

    @pytest.mark.parametrize('name', ['Finding', 'findingReasonCodes'])
    async def test_rds_ambiguous_finding_name_is_rejected(self, mock_context, name):
        """RDS has no plain Finding filter; the error names the instance/storage choices."""
        result, method = await self._call(
            mock_context,
            'get_rds_recommendations',
            'get_rds_database_recommendations',
            filters=json.dumps([{'name': name, 'values': ['Overprovisioned']}]),
        )

        method.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'get_rds_recommendations'
        assert len(result['data']['filter_name_choices']) == 2
        assert 'InstanceFinding' in result['data']['valid_filters']

    @pytest.mark.parametrize('func_name,client_method', OPS)
    async def test_invalid_parameter_value_lists_valid_filters(
        self, mock_context, func_name, client_method
    ):
        """InvalidParameterValueException comes back with the valid names and values."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools
        from botocore.exceptions import ClientError

        client = MagicMock()
        getattr(client, client_method).side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidParameterValueException',
                    'Message': 'Invalid filter value.',
                }
            },
            'Get',
        )
        submitted = [{'name': 'tag:Owner', 'values': ['x']}]

        result = await getattr(compute_optimizer_tools, func_name)(
            mock_context, client, None, json.dumps(submitted), None, None
        )

        assert result['status'] == 'error'
        assert result['service'] == 'Compute Optimizer'
        assert result['operation'] == func_name
        assert result['error_type'] == 'InvalidParameterValueException'
        assert 'Invalid filter value.' in result['message']
        assert result['data']['submitted_filters'] == submitted
        valid = result['data']['valid_filters']
        assert valid == compute_optimizer_tools._valid_filter_values(func_name)
        assert all(values for values in valid.values())

    async def test_invalid_parameter_without_filters_omits_filter_guidance(self, mock_context):
        """A non-filter InvalidParameterValue (e.g. a bad ARN) does not point at filters."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_ec2_instance_recommendations.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidParameterValueException',
                    'Message': 'Invalid instance arn.',
                }
            },
            'GetEC2InstanceRecommendations',
        )

        result = await get_ec2_instance_recommendations(
            mock_context, client, None, None, None, None, ['arn:aws:ec2:us-east-1:1:volume/v']
        )

        assert result['error_type'] == 'InvalidParameterValueException'
        assert 'Invalid instance arn.' in result['message']
        assert 'valid_filters' not in result['data']

    async def test_non_filter_error_with_filters_omits_filter_guidance(self, mock_context):
        """Filters were sent but the service blamed something else (e.g. next_token)."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_ec2_instance_recommendations.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidParameterValueException',
                    'Message': 'The pagination token is not valid or is expired.',
                }
            },
            'GetEC2InstanceRecommendations',
        )

        result = await get_ec2_instance_recommendations(
            mock_context,
            client,
            None,
            json.dumps([{'name': 'Finding', 'values': ['Optimized']}]),
            None,
            'bogus-token',
        )

        assert result['error_type'] == 'InvalidParameterValueException'
        assert 'pagination token' in result['message']
        assert 'valid_filters' not in result['data']
        assert 'compare submitted_filters' not in result['message']

    async def test_other_client_errors_still_raise(self, mock_context):
        """Errors other than InvalidParameterValue reach the dispatcher's handling."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_ebs_volume_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'GetEBSVolumeRecommendations',
        )

        with pytest.raises(ClientError):
            await get_ebs_volume_recommendations(mock_context, client, None, None, None, None)

    async def test_more_than_one_account_id_is_rejected(self, mock_context):
        """The API accepts one account ID per request."""
        result, method = await self._call(
            mock_context,
            'get_lambda_function_recommendations',
            'get_lambda_function_recommendations',
            account_ids=json.dumps(['111111111111', '222222222222']),
        )

        method.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['data']['provided_account_ids'] == ['111111111111', '222222222222']

    @pytest.mark.parametrize(
        'func_name,client_method,ok,too_many',
        [
            ('get_ec2_instance_recommendations', 'get_ec2_instance_recommendations', 1000, 1001),
            ('get_idle_recommendations', 'get_idle_recommendations', 100, 101),
        ],
    )
    async def test_max_results_limit(self, mock_context, func_name, client_method, ok, too_many):
        """max_results is capped at 1000, or 100 for idle."""
        result, method = await self._call(mock_context, func_name, client_method, max_results=ok)
        assert result['status'] == 'success'
        assert method.call_args[1]['maxResults'] == ok

        method.reset_mock()
        result, method = await self._call(
            mock_context, func_name, client_method, max_results=too_many
        )
        method.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['data']['max_allowed'] == ok


def _populated_response(api_name):
    """Build a response with every output-shape field populated, from the botocore model."""
    import botocore.session
    import datetime
    import itertools

    model = botocore.session.get_session().get_service_model('compute-optimizer')
    counter = itertools.count(1000)
    markers = {}

    def gen(shape, path, depth=0):
        kind = shape.type_name
        if kind == 'structure':
            if depth >= 8:
                return {}
            return {k: gen(v, f'{path}.{k}', depth + 1) for k, v in shape.members.items()}
        if kind == 'list':
            return [gen(shape.member, path + '[]', depth + 1)]
        if kind == 'string':
            if shape.enum:
                return shape.enum[0]
            value = f'M{next(counter)}'
            markers[value] = path
            return value
        if kind in ('integer', 'long'):
            value = next(counter)
            markers[str(value)] = path
            return value
        if kind in ('double', 'float'):
            value = next(counter) + 0.25
            markers[str(value)] = path
            return value
        if kind == 'boolean':
            return True
        if kind == 'timestamp':
            return datetime.datetime(2026, 1, 1)
        return {}

    return gen(model.operation_model(api_name).output_shape, ''), markers


@pytest.mark.asyncio
class TestComputeOptimizerResponseFields:
    """Every non-enum field the API returns reaches the formatted output."""

    # Fields intentionally not surfaced: recommendationSources, and tags (which can be large).
    ALLOWED_DROPS = (
        'recommendationSources',
        'tags',
    )

    @pytest.mark.parametrize(
        'func_name,client_method,api_name',
        [
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                'GetEC2InstanceRecommendations',
            ),
            (
                'get_auto_scaling_group_recommendations',
                'get_auto_scaling_group_recommendations',
                'GetAutoScalingGroupRecommendations',
            ),
            (
                'get_ebs_volume_recommendations',
                'get_ebs_volume_recommendations',
                'GetEBSVolumeRecommendations',
            ),
            (
                'get_lambda_function_recommendations',
                'get_lambda_function_recommendations',
                'GetLambdaFunctionRecommendations',
            ),
            (
                'get_rds_recommendations',
                'get_rds_database_recommendations',
                'GetRDSDatabaseRecommendations',
            ),
            (
                'get_ecs_service_recommendations',
                'get_ecs_service_recommendations',
                'GetECSServiceRecommendations',
            ),
            ('get_idle_recommendations', 'get_idle_recommendations', 'GetIdleRecommendations'),
        ],
    )
    async def test_no_fields_dropped(self, mock_context, func_name, client_method, api_name):
        """Populate the full output shape and check each value appears in the result."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        response, markers = _populated_response(api_name)
        client = MagicMock()
        getattr(client, client_method).return_value = response

        result = await getattr(compute_optimizer_tools, func_name)(
            mock_context, client, None, None, None, None
        )
        output = json.dumps(result, default=str)

        dropped = sorted(
            path
            for marker, path in markers.items()
            if marker not in output and not any(a in path for a in self.ALLOWED_DROPS)
        )
        assert dropped == []

    async def test_enum_valued_fields_are_surfaced(self, mock_context):
        """Enum-valued fields (not covered by the marker check) are mapped explicitly."""
        client = MagicMock()
        client.get_ec2_instance_recommendations.return_value = {
            'instanceRecommendations': [
                {
                    'instanceState': 'running',
                    'findingReasonCodes': ['CPUOverprovisioned'],
                    'recommendationOptions': [
                        {'migrationEffort': 'Low', 'platformDifferences': ['Hypervisor']}
                    ],
                }
            ]
        }

        result = await get_ec2_instance_recommendations(
            mock_context, client, None, None, None, None
        )

        rec = result['data']['recommendations'][0]
        assert rec['current_instance']['instance_state'] == 'running'
        assert rec['current_instance']['finding_reason_codes'] == ['CPUOverprovisioned']
        assert rec['recommendation_options'][0]['migration_effort'] == 'Low'
        assert rec['recommendation_options'][0]['platform_differences'] == ['Hypervisor']


@pytest.mark.asyncio
class TestComputeOptimizerReviewFixes:
    """Regression tests for issues found in review."""

    OPS = TestComputeOptimizerFilterNormalization.OPS
    API_NAMES = {
        'get_ec2_instance_recommendations': 'GetEC2InstanceRecommendations',
        'get_auto_scaling_group_recommendations': 'GetAutoScalingGroupRecommendations',
        'get_ebs_volume_recommendations': 'GetEBSVolumeRecommendations',
        'get_lambda_function_recommendations': 'GetLambdaFunctionRecommendations',
        'get_rds_recommendations': 'GetRDSDatabaseRecommendations',
        'get_ecs_service_recommendations': 'GetECSServiceRecommendations',
        'get_idle_recommendations': 'GetIdleRecommendations',
    }

    @pytest.mark.parametrize(
        'func_name,client_method,submitted,expected',
        [
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                'OVER_PROVISIONED',
                'Overprovisioned',
            ),
            (
                'get_auto_scaling_group_recommendations',
                'get_auto_scaling_group_recommendations',
                'NOT_OPTIMIZED',
                'NotOptimized',
            ),
            (
                'get_ebs_volume_recommendations',
                'get_ebs_volume_recommendations',
                'not_optimized',
                'NotOptimized',
            ),
        ],
    )
    async def test_underscored_values_are_folded(
        self, mock_context, func_name, client_method, submitted, expected
    ):
        """The UPPER_SNAKE spelling EC2 returns can be passed back as a filter value."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        client = MagicMock()
        getattr(client, client_method).return_value = {}
        filters = json.dumps([{'name': 'Finding', 'values': [submitted]}])

        await getattr(compute_optimizer_tools, func_name)(
            mock_context, client, None, filters, None, None
        )

        assert getattr(client, client_method).call_args[1]['filters'] == [
            {'name': 'Finding', 'values': [expected]}
        ]

    async def test_asg_finding_reason_codes_not_advertised(self, mock_context):
        """The ASG API rejects FindingReasonCodes, so the error must not suggest it."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_auto_scaling_group_recommendations.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidParameterValueException',
                    'Message': 'Invalid filter value.',
                }
            },
            'GetAutoScalingGroupRecommendations',
        )

        result = await get_auto_scaling_group_recommendations(
            mock_context,
            client,
            None,
            json.dumps([{'name': 'FindingReasonCodes', 'values': ['CPUOverprovisioned']}]),
            None,
            None,
        )

        assert 'FindingReasonCodes' not in result['data']['valid_filters']

    async def test_error_keeps_request_metadata(self, mock_context):
        """request_id and http_status survive, as handle_aws_error returned them."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_ecs_service_recommendations.side_effect = ClientError(
            {
                'Error': {'Code': 'InvalidParameterValueException', 'Message': 'Invalid filter.'},
                'ResponseMetadata': {'RequestId': 'rid-123', 'HTTPStatusCode': 400},
            },
            'GetECSServiceRecommendations',
        )

        result = await get_ecs_service_recommendations(
            mock_context, client, None, None, None, None
        )

        assert result['request_id'] == 'rid-123'
        assert result['http_status'] == 400

    @pytest.mark.parametrize(
        'error_body',
        [
            {'Code': 'InvalidParameterValueException'},
            {'Code': 'InvalidParameterValueException', 'Message': None},
        ],
    )
    async def test_missing_error_message_still_structured(self, mock_context, error_body):
        """A ClientError without a message (sent with filters) still yields the structured error."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_ec2_instance_recommendations.side_effect = ClientError(
            {'Error': error_body}, 'GetEC2InstanceRecommendations'
        )

        result = await get_ec2_instance_recommendations(
            mock_context,
            client,
            None,
            json.dumps([{'name': 'Finding', 'values': ['Optimized']}]),
            None,
            None,
        )

        assert result['error_type'] == 'InvalidParameterValueException'
        assert result['operation'] == 'get_ec2_instance_recommendations'

    @pytest.mark.parametrize('func_name,client_method', OPS)
    async def test_max_results_limit_every_operation(self, mock_context, func_name, client_method):
        """Each operation rejects one over its documented page limit."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        limit = 100 if func_name == 'get_idle_recommendations' else 1000
        client = MagicMock()
        getattr(client, client_method).return_value = {}
        func = getattr(compute_optimizer_tools, func_name)

        ok = await func(mock_context, client, limit, None, None, None)
        assert ok['status'] == 'success'
        too_many = await func(mock_context, client, limit + 1, None, None, None)
        assert too_many['error_type'] == 'validation_error'
        assert too_many['data']['max_allowed'] == limit

    @pytest.mark.parametrize(
        'operation,helper',
        [
            ('get_ec2_instance_recommendations', 'get_ec2_instance_recommendations'),
            (
                'get_auto_scaling_group_recommendations',
                'get_auto_scaling_group_recommendations',
            ),
            ('get_ebs_volume_recommendations', 'get_ebs_volume_recommendations'),
            ('get_lambda_function_recommendations', 'get_lambda_function_recommendations'),
            ('get_rds_recommendations', 'get_rds_recommendations'),
            ('get_ecs_service_recommendations', 'get_ecs_service_recommendations'),
            ('get_idle_recommendations', 'get_idle_recommendations'),
        ],
    )
    async def test_dispatcher_passes_resource_arns_to_every_operation(
        self, mock_context, operation, helper
    ):
        """The dispatcher forwards the parsed ARN list for each operation."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        arn = 'arn:aws:ec2:us-west-2:123456789012:instance/i-0abc'
        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
            patch.object(co_mod, helper, new_callable=AsyncMock) as mock_helper,
        ):
            mock_get_logger.return_value = AsyncMock()
            client = MagicMock()
            client.get_enrollment_status.return_value = {'status': 'ACTIVE'}
            mock_create_client.return_value = client
            mock_helper.return_value = {'status': 'success', 'data': {}}

            await co_mod.compute_optimizer(
                mock_context, operation=operation, resource_arns=json.dumps([arn])
            )

        assert mock_helper.call_args[0][-1] == [arn]
        mock_create_client.assert_called_once_with('compute-optimizer', region_name='us-west-2')

    @pytest.mark.parametrize(
        'func_name,client_method,list_key,keeps_tags',
        [
            (
                'get_ecs_service_recommendations',
                'get_ecs_service_recommendations',
                'ecsServiceRecommendations',
                True,
            ),
            ('get_idle_recommendations', 'get_idle_recommendations', 'idleRecommendations', True),
            (
                'get_ec2_instance_recommendations',
                'get_ec2_instance_recommendations',
                'instanceRecommendations',
                False,
            ),
            (
                'get_ebs_volume_recommendations',
                'get_ebs_volume_recommendations',
                'volumeRecommendations',
                False,
            ),
            (
                'get_lambda_function_recommendations',
                'get_lambda_function_recommendations',
                'lambdaFunctionRecommendations',
                False,
            ),
            (
                'get_rds_recommendations',
                'get_rds_database_recommendations',
                'rdsDBRecommendations',
                False,
            ),
        ],
    )
    async def test_tags_only_where_previously_returned(
        self, mock_context, func_name, client_method, list_key, keeps_tags
    ):
        """ECS and idle keep tags (returned before); the others do not add them."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        client = MagicMock()
        getattr(client, client_method).return_value = {
            list_key: [{'tags': [{'key': 'k', 'value': 'v'}]}]
        }

        result = await getattr(compute_optimizer_tools, func_name)(
            mock_context, client, None, None, None, None
        )

        rec = result['data']['recommendations'][0]
        if keeps_tags:
            assert rec['tags'] == [{'key': 'k', 'value': 'v'}]
        else:
            assert 'tags' not in rec

    async def test_lambda_response_has_no_errors_key(self, mock_context):
        """Lambda's API has no errors member, so the output must not claim an empty list."""
        client = MagicMock()
        client.get_lambda_function_recommendations.return_value = {
            'lambdaFunctionRecommendations': []
        }

        result = await get_lambda_function_recommendations(
            mock_context, client, None, None, None, None
        )

        assert 'errors' not in result['data']
        assert 'next_token' in result['data']

    @pytest.mark.parametrize(
        'func_name,client_method',
        [
            ('get_ec2_instance_recommendations', 'get_ec2_instance_recommendations'),
            ('get_auto_scaling_group_recommendations', 'get_auto_scaling_group_recommendations'),
            ('get_ebs_volume_recommendations', 'get_ebs_volume_recommendations'),
            ('get_rds_recommendations', 'get_rds_database_recommendations'),
            ('get_ecs_service_recommendations', 'get_ecs_service_recommendations'),
            ('get_idle_recommendations', 'get_idle_recommendations'),
        ],
    )
    async def test_errors_key_on_operations_that_return_it(
        self, mock_context, func_name, client_method
    ):
        """Operations whose API returns errors pass the list through."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        client = MagicMock()
        err = {'identifier': 'id-1', 'code': 'InsufficientData', 'message': 'm'}
        getattr(client, client_method).return_value = {'errors': [err]}

        result = await getattr(compute_optimizer_tools, func_name)(
            mock_context, client, None, None, None, None
        )

        assert result['data']['errors'] == [err]

    async def test_enum_valued_fields_outside_ec2(self, mock_context):
        """Enum-valued fields added for ASG, Lambda, RDS, and ECS are surfaced."""
        client = MagicMock()
        client.get_auto_scaling_group_recommendations.return_value = {
            'autoScalingGroupRecommendations': [
                {'recommendationOptions': [{'migrationEffort': 'Medium'}]}
            ]
        }
        client.get_lambda_function_recommendations.return_value = {
            'lambdaFunctionRecommendations': [
                {'findingReasonCodes': ['MemoryOverprovisioned'], 'currentPerformanceRisk': 'Low'}
            ]
        }
        client.get_rds_database_recommendations.return_value = {
            'rdsDBRecommendations': [
                {
                    'instanceFindingReasonCodes': ['CPUOverprovisioned'],
                    'storageFindingReasonCodes': ['EBSVolumeIOPSOverprovisioned'],
                    'currentStorageEstimatedMonthlyVolumeIOPsCostVariation': 'High',
                    'storageRecommendationOptions': [
                        {'estimatedMonthlyVolumeIOPsCostVariation': 'Low'}
                    ],
                }
            ]
        }
        client.get_ecs_service_recommendations.return_value = {
            'ecsServiceRecommendations': [{'findingReasonCodes': ['CPUUnderprovisioned']}]
        }

        asg = await get_auto_scaling_group_recommendations(
            mock_context, client, None, None, None, None
        )
        lam = await get_lambda_function_recommendations(
            mock_context, client, None, None, None, None
        )
        rds = await get_rds_recommendations(mock_context, client, None, None, None, None)
        ecs = await get_ecs_service_recommendations(mock_context, client, None, None, None, None)

        assert (
            asg['data']['recommendations'][0]['recommendation_options'][0]['migration_effort']
            == 'Medium'
        )
        lam_current = lam['data']['recommendations'][0]['current_configuration']
        assert lam_current['finding_reason_codes'] == ['MemoryOverprovisioned']
        assert lam_current['current_performance_risk'] == 'Low'
        rds_current = rds['data']['recommendations'][0]['current_configuration']
        assert rds_current['instance_finding_reason_codes'] == ['CPUOverprovisioned']
        assert rds_current['storage_finding_reason_codes'] == ['EBSVolumeIOPSOverprovisioned']
        assert (
            rds_current['current_storage_estimated_monthly_volume_iops_cost_variation'] == 'High'
        )
        assert (
            rds['data']['recommendations'][0]['storage_recommendation_options'][0][
                'estimated_monthly_volume_iops_cost_variation'
            ]
            == 'Low'
        )
        assert ecs['data']['recommendations'][0]['current_service_configuration'][
            'finding_reason_codes'
        ] == ['CPUUnderprovisioned']


class TestComputeOptimizerSpecTables:
    """Synchronous checks of the filter tables and region matching."""

    API_NAMES = TestComputeOptimizerReviewFixes.API_NAMES

    @pytest.mark.parametrize('func_name', list(API_NAMES))
    def test_filter_specs_match_service_model(self, func_name):
        """Every spec filter name exists in the operation's botocore filter-name enum."""
        import botocore.session
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        model: Any = botocore.session.get_session().get_service_model('compute-optimizer')
        filter_shape = model.operation_model(self.API_NAMES[func_name]).input_shape.members[
            'filters'
        ]
        model_names = set(filter_shape.member.members['name'].enum)
        spec_names = set(compute_optimizer_tools._FILTER_SPECS[func_name])

        assert spec_names <= model_names
        # The only model names left out are ones the live API rejects.
        excluded = {'get_auto_scaling_group_recommendations': {'FindingReasonCodes'}}
        assert model_names - spec_names == excluded.get(func_name, set())

    def test_specs_resolve_to_known_values(self):
        """Pin values the live API was verified to accept, so table edits are caught."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        valid = compute_optimizer_tools._valid_filter_values
        assert valid('get_ec2_instance_recommendations')['Finding'] == [
            'Underprovisioned',
            'Overprovisioned',
            'Optimized',
        ]
        assert valid('get_auto_scaling_group_recommendations')['Finding'] == [
            'Optimized',
            'NotOptimized',
        ]
        assert valid('get_ec2_instance_recommendations')['RecommendationSourceType'] == [
            'Ec2Instance',
            'AutoScalingGroup',
        ]
        assert valid('get_rds_recommendations')['Idle'] == ['False', 'True']
        ec2_reason_codes = valid('get_ec2_instance_recommendations')['FindingReasonCodes']
        assert 'CPUOverprovisioned' in ec2_reason_codes
        # GPU codes are accepted by the filter, so they are advertised too.
        assert {
            'GPUUnderprovisioned',
            'GPUOverprovisioned',
            'GPUMemoryUnderprovisioned',
            'GPUMemoryOverprovisioned',
        } <= set(ec2_reason_codes)

    def test_region_match_is_case_insensitive(self):
        """An explicit region in a different case still matches the ARN region."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        arn = 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc'
        assert compute_optimizer_tools._resolve_region_for_arns([arn], 'US-EAST-1') == 'us-east-1'


@pytest.mark.asyncio
class TestIdleDefaultOrder:
    """Idle results are sorted by savings after discounts, highest first."""

    @pytest.mark.parametrize('next_token', [None, 'page-2-token'])
    async def test_order_by_sent_on_every_page(self, mock_context, next_token):
        """The sort is sent on the first page and on next_token follow-ups."""
        client = MagicMock()
        client.get_idle_recommendations.return_value = {}

        await get_idle_recommendations(mock_context, client, None, None, None, next_token)

        assert client.get_idle_recommendations.call_args[1]['orderBy'] == {
            'dimension': 'SavingsValueAfterDiscount',
            'order': 'Desc',
        }

    @pytest.mark.parametrize(
        'order_by,expected',
        [
            (
                '{"dimension": "SavingsValue", "order": "Asc"}',
                {'dimension': 'SavingsValue', 'order': 'Asc'},
            ),
            (
                '{"Dimension": "savings_value", "Order": "asc"}',
                {'dimension': 'SavingsValue', 'order': 'Asc'},
            ),
            ('{"order": "asc"}', {'dimension': 'SavingsValueAfterDiscount', 'order': 'Asc'}),
            ('{"dimension": "savingsvalue"}', {'dimension': 'SavingsValue', 'order': 'Desc'}),
            ('{}', {'dimension': 'SavingsValueAfterDiscount', 'order': 'Desc'}),
        ],
    )
    async def test_order_by_is_folded_and_defaulted(self, mock_context, order_by, expected):
        """Custom order_by is folded onto the API spelling; missing parts take the default."""
        client = MagicMock()
        client.get_idle_recommendations.return_value = {}

        result = await get_idle_recommendations(
            mock_context, client, None, None, None, None, order_by=order_by
        )

        assert result['status'] == 'success'
        assert client.get_idle_recommendations.call_args[1]['orderBy'] == expected

    @pytest.mark.parametrize(
        'order_by',
        [
            '{"dimension": "Cost"}',
            '{"order": "Sideways"}',
            '{"sortBy": "SavingsValue"}',
            '["SavingsValue"]',
            '{"dimension": 5}',
        ],
    )
    async def test_invalid_order_by_is_rejected(self, mock_context, order_by):
        """Invalid order_by returns a structured error listing the valid values; no call."""
        client = MagicMock()

        result = await get_idle_recommendations(
            mock_context, client, None, None, None, None, order_by=order_by
        )

        client.get_idle_recommendations.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'get_idle_recommendations'
        assert result['data']['valid_order_by'] == {
            'dimension': ['SavingsValue', 'SavingsValueAfterDiscount'],
            'order': ['Asc', 'Desc'],
        }

    async def test_dispatcher_passes_order_by_to_idle(self, mock_context):
        """The dispatcher forwards order_by to the idle helper."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_get_logger.return_value = AsyncMock()
            client = MagicMock()
            client.get_enrollment_status.return_value = {'status': 'ACTIVE'}
            client.get_idle_recommendations.return_value = {}
            mock_create_client.return_value = client

            await co_mod.compute_optimizer(
                mock_context,
                operation='get_idle_recommendations',
                order_by='{"dimension": "SavingsValue", "order": "Asc"}',
            )

        assert client.get_idle_recommendations.call_args[1]['orderBy'] == {
            'dimension': 'SavingsValue',
            'order': 'Asc',
        }

    @pytest.mark.parametrize(
        'operation',
        [
            'get_ec2_instance_recommendations',
            'get_auto_scaling_group_recommendations',
            'get_ebs_volume_recommendations',
            'get_lambda_function_recommendations',
            'get_rds_recommendations',
            'get_ecs_service_recommendations',
        ],
    )
    async def test_order_by_rejected_on_rightsizing_operations(self, mock_context, operation):
        """Rightsizing APIs cannot sort, so order_by gets an error instead of being ignored."""
        co_mod = _reload_compute_optimizer_with_identity_decorator()
        with (
            patch.object(co_mod, 'create_aws_client') as mock_create_client,
            patch.object(co_mod, 'get_context_logger') as mock_get_logger,
        ):
            mock_get_logger.return_value = AsyncMock()

            result = await co_mod.compute_optimizer(
                mock_context, operation=operation, order_by='{"order": "Asc"}'
            )

        mock_create_client.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == operation

    async def test_order_by_not_sent_on_rightsizing_operations(self, mock_context):
        """Only the idle API has orderBy; rightsizing calls must not send it."""
        client = MagicMock()
        client.get_ec2_instance_recommendations.return_value = {}

        await get_ec2_instance_recommendations(mock_context, client, None, None, None, None)

        assert 'orderBy' not in client.get_ec2_instance_recommendations.call_args[1]

    async def test_order_by_values_are_valid_in_model(self):
        """The default dimension and order exist in the service model."""
        import botocore.session

        model: Any = botocore.session.get_session().get_service_model('compute-optimizer')
        order_by = model.operation_model('GetIdleRecommendations').input_shape.members['orderBy']
        assert 'SavingsValueAfterDiscount' in order_by.members['dimension'].enum
        assert 'Desc' in order_by.members['order'].enum


_CPU_ARCH_HELPERS = [
    (get_ec2_instance_recommendations, 'get_ec2_instance_recommendations'),
    (get_auto_scaling_group_recommendations, 'get_auto_scaling_group_recommendations'),
    (get_rds_recommendations, 'get_rds_database_recommendations'),
]


def _dispatch_with_cpu_architectures(mock_context, operation, cpu_vendor_architectures):
    """Run the dispatcher with an ACTIVE, empty-result client; return (coroutine, client)."""
    co_mod = _reload_compute_optimizer_with_identity_decorator()
    client = MagicMock()
    client.get_enrollment_status.return_value = {'status': 'ACTIVE'}
    for method in co_mod._API_METHODS.values():
        getattr(client, method).return_value = {}

    async def run():
        with (
            patch.object(co_mod, 'create_aws_client', return_value=client),
            patch.object(co_mod, 'get_context_logger', return_value=AsyncMock()),
        ):
            return await co_mod.compute_optimizer(
                mock_context,
                operation=operation,
                cpu_vendor_architectures=cpu_vendor_architectures,
            )

    return run(), client


@pytest.mark.asyncio
class TestCpuVendorArchitectures:
    """EC2, ASG, and RDS accept a per-request CPU architecture preference."""

    @pytest.mark.parametrize('helper,method', _CPU_ARCH_HELPERS)
    async def test_preference_sent_and_echoed(self, mock_context, helper, method):
        """The resolved list is sent as recommendationPreferences and echoed back."""
        client = MagicMock()
        getattr(client, method).return_value = {}

        result = await helper(
            mock_context,
            client,
            None,
            None,
            None,
            None,
            cpu_vendor_architectures=['AWS_ARM64'],
        )

        preferences = {'cpuVendorArchitectures': ['AWS_ARM64']}
        assert getattr(client, method).call_args[1]['recommendationPreferences'] == preferences
        assert result['data']['applied_recommendation_preferences'] == preferences

    @pytest.mark.parametrize('helper,method', _CPU_ARCH_HELPERS)
    async def test_preference_omitted_by_default(self, mock_context, helper, method):
        """Without the parameter nothing is sent, so the API default (CURRENT) applies."""
        client = MagicMock()
        getattr(client, method).return_value = {}

        result = await helper(mock_context, client, None, None, None, None)

        assert 'recommendationPreferences' not in getattr(client, method).call_args[1]
        assert 'applied_recommendation_preferences' not in result['data']

    @pytest.mark.parametrize(
        'value,expected',
        [
            ('["AWS_ARM64"]', ['AWS_ARM64']),
            ('["aws_arm64"]', ['AWS_ARM64']),
            ('["awsarm64", "current"]', ['AWS_ARM64', 'CURRENT']),
            ('["CURRENT", "current", "AWS_ARM64"]', ['CURRENT', 'AWS_ARM64']),
            ('AWS_ARM64', ['AWS_ARM64']),
        ],
    )
    async def test_values_are_folded(self, mock_context, value, expected):
        """Values fold case and underscores onto the API enum; duplicates are dropped."""
        run, client = _dispatch_with_cpu_architectures(
            mock_context, 'get_ec2_instance_recommendations', value
        )

        result = await run

        assert result['status'] == 'success'
        assert client.get_ec2_instance_recommendations.call_args[1][
            'recommendationPreferences'
        ] == {'cpuVendorArchitectures': expected}

    @pytest.mark.parametrize(
        'value', ['["X86"]', '["ARM64"]', '[]', '[5]', '{"cpu": "AWS_ARM64"}']
    )
    async def test_invalid_values_are_rejected(self, mock_context, value):
        """An invalid value returns a structured error listing the valid values; no call."""
        run, client = _dispatch_with_cpu_architectures(
            mock_context, 'get_rds_recommendations', value
        )

        result = await run

        client.get_rds_database_recommendations.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'get_rds_recommendations'
        assert result['data']['valid_values'] == ['CURRENT', 'AWS_ARM64']

    @pytest.mark.parametrize(
        'operation',
        [
            'get_ebs_volume_recommendations',
            'get_lambda_function_recommendations',
            'get_ecs_service_recommendations',
            'get_idle_recommendations',
        ],
    )
    async def test_rejected_on_unsupported_operations(self, mock_context, operation):
        """Operations without recommendationPreferences get an error instead of a silent drop."""
        run, client = _dispatch_with_cpu_architectures(mock_context, operation, '["AWS_ARM64"]')

        result = await run

        client.get_enrollment_status.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == operation

    @pytest.mark.parametrize('helper,method', _CPU_ARCH_HELPERS)
    async def test_preference_kept_with_arns_and_next_token(self, mock_context, helper, method):
        """The preference rides along with ARN lookups and pagination."""
        client = MagicMock()
        getattr(client, method).return_value = {}

        await helper(
            mock_context,
            client,
            None,
            None,
            None,
            'page-2-token',
            ['arn:aws:ec2:us-east-1:123456789012:instance/i-0abc'],
            cpu_vendor_architectures=['CURRENT', 'AWS_ARM64'],
        )

        kwargs = getattr(client, method).call_args[1]
        assert kwargs['nextToken'] == 'page-2-token'
        assert kwargs['recommendationPreferences'] == {
            'cpuVendorArchitectures': ['CURRENT', 'AWS_ARM64']
        }


class TestCpuVendorArchitectureModel:
    """The supported operations and values match the service model."""

    def test_operations_and_values_match_model(self):
        """Exactly these operations take the preference, with exactly these values."""
        import botocore.session
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        client: Any = botocore.session.get_session().create_client(
            'compute-optimizer', region_name='us-east-1'
        )
        for operation, method in compute_optimizer_tools._API_METHODS.items():
            api_name = client.meta.method_to_api_mapping[method]
            members = client.meta.service_model.operation_model(api_name).input_shape.members
            supported = operation in compute_optimizer_tools._CPU_VENDOR_ARCHITECTURE_OPERATIONS
            assert ('recommendationPreferences' in members) == supported, operation
            if supported:
                enum = (
                    members['recommendationPreferences']
                    .members['cpuVendorArchitectures']
                    .member.enum
                )
                assert sorted(enum) == sorted(compute_optimizer_tools._CPU_VENDOR_ARCHITECTURES)


class TestComputeOptimizerHelperEdgeCases:
    """Edge cases of the ARN-region and filter-normalization helpers."""

    def test_arns_without_region_fall_back_to_given_region(self):
        """ARNs whose region field is empty leave the caller's region unchanged."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        arns = ['arn:aws:ec2::123456789012:instance/i-0abc']
        assert compute_optimizer_tools._resolve_region_for_arns(arns, 'us-west-2') == 'us-west-2'
        assert compute_optimizer_tools._resolve_region_for_arns(arns, None) is None

    def test_non_list_filters_pass_through(self):
        """Filters that are not a JSON array are returned unchanged for the API to judge."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        filters = {'name': 'Finding', 'values': ['overprovisioned']}
        assert compute_optimizer_tools._normalize_filters(
            'get_ec2_instance_recommendations', filters
        ) == (filters, None)

    def test_filter_without_string_name_passes_through(self):
        """A filter with no string name keeps its (key-folded) entry as given."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        normalized, error = compute_optimizer_tools._normalize_filters(
            'get_ec2_instance_recommendations', [{'Values': ['overprovisioned']}, {'name': 5}]
        )
        assert error is None
        assert normalized == [{'values': ['overprovisioned']}, {'name': 5}]

    def test_ambiguous_filter_names_derived_from_model(self):
        """RDS splits Finding/FindingReasonCode into instance and storage variants."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        compute_optimizer_tools._model_filter_names.cache_clear()
        assert compute_optimizer_tools._ambiguous_filter_names('get_rds_recommendations') == {
            'finding': ['InstanceFinding', 'StorageFinding'],
            'findingreasoncode': ['InstanceFindingReasonCode', 'StorageFindingReasonCode'],
        }
        for operation in compute_optimizer_tools._API_METHODS:
            if operation != 'get_rds_recommendations':
                assert compute_optimizer_tools._ambiguous_filter_names(operation) == {}

    def test_model_load_failure_disables_ambiguity_check(self):
        """If the service model cannot be loaded, no filter name is treated as ambiguous."""
        from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools

        compute_optimizer_tools._model_filter_names.cache_clear()
        try:
            with patch(
                'botocore.session.Session.get_service_model', side_effect=RuntimeError('boom')
            ):
                assert compute_optimizer_tools._model_filter_names() == {}
                assert (
                    compute_optimizer_tools._ambiguous_filter_names('get_rds_recommendations')
                    == {}
                )
        finally:
            compute_optimizer_tools._model_filter_names.cache_clear()
