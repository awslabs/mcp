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

"""Unit tests for the recommendation_details_tools module.

These tests verify the functionality of detailed recommendation processing tools, including:
- Retrieving enhanced recommendation details from Cost Optimization Hub
- Processing recommendations with additional Cost Explorer and Compute Optimizer data
- Formatting recommendation templates for different resource types and action types
- Handling Savings Plans and Reserved Instance purchase recommendations
- Integrating utilization metrics and performance data for comprehensive analysis
- Error handling for missing recommendation IDs and template processing failures
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools import (
    format_base_recommendation,
    format_timestamp,
    get_compute_optimizer_data,
    get_cost_explorer_data,
    get_reserved_instances_recommendation,
    get_savings_plans_recommendation,
    get_template_for_recommendation,
    process_recommendation,
    recommendation_details_server,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_coh_client():
    """Create a mock Cost Optimization Hub boto3 client."""
    mock_client = MagicMock()

    # Set up mock response for get_recommendation
    mock_client.get_recommendation.return_value = {
        'recommendationId': 'rec-12345',
        'accountId': '123456789012',
        'region': 'us-east-1',
        'resourceId': 'i-0abc123def456',
        'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
        'actionType': 'Modify',
        'currentResourceType': 'Ec2Instance',
        'recommendedResourceType': 'Ec2Instance',
        'estimatedMonthlySavings': 25.0,
        'estimatedSavingsPercentage': 30.0,
        'estimatedMonthlyCost': 75.0,
        'currencyCode': 'USD',
        'implementationEffort': 'MEDIUM',
        'lastRefreshTimestamp': 1632825600000,
        'recommendationLookbackPeriodInDays': 14,
        'costCalculationLookbackPeriodInDays': 14,
        'estimatedSavingsOverCostCalculationLookbackPeriod': 12.5,
        'currentResourceDetails': {
            'ec2ResourceDetails': {
                'instanceType': 't3.large',
            }
        },
        'recommendedResourceDetails': {
            'ec2ResourceDetails': {
                'instanceType': 't3.medium',
            }
        },
    }

    return mock_client


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    # Set up mock response for get_savings_plans_purchase_recommendation
    mock_client.get_savings_plans_purchase_recommendation.return_value = {
        'SavingsPlansPurchaseRecommendation': {
            'AccountScope': 'PAYER',
            'SavingsPlansType': 'COMPUTE_SP',
            'TermInYears': 'ONE_YEAR',
            'PaymentOption': 'ALL_UPFRONT',
            'SavingsPlansRecommendationSummary': {
                'EstimatedROI': '20.0',
                'EstimatedTotalCost': '10000.0',
                'EstimatedSavingsAmount': '2000.0',
                'EstimatedSavingsPercentage': '20.0',
            },
            'SavingsPlansPurchaseRecommendationDetails': [
                {
                    'SavingsPlansDetails': {
                        'Region': 'us-east-1',
                        'InstanceFamily': 'Standard',
                        'OfferingId': 'offering-123',
                    },
                    'AccountId': '123456789012',
                    'UpfrontCost': '8000.0',
                    'EstimatedROI': '20.0',
                    'EstimatedSavingsAmount': '2000.0',
                    'EstimatedSavingsPercentage': '20.0',
                    'EstimatedMonthlySavingsAmount': '166.67',
                    'EstimatedOnDemandCost': '10000.0',
                    'EstimatedBreakEvenInMonths': '10.0',
                }
            ],
        }
    }

    # Set up mock response for get_reservation_purchase_recommendation
    mock_client.get_reservation_purchase_recommendation.return_value = {
        'Recommendations': [
            {
                'AccountScope': 'PAYER',
                'LookbackPeriodInDays': 'THIRTY_DAYS',
                'TermInYears': 'ONE_YEAR',
                'PaymentOption': 'ALL_UPFRONT',
                'RecommendationSummary': {
                    'EstimatedTotalCost': '10000.0',
                    'EstimatedSavingsAmount': '2000.0',
                    'EstimatedSavingsPercentage': '20.0',
                },
                'RecommendationDetails': [
                    {
                        'AccountId': '123456789012',
                        'InstanceDetails': {
                            'EC2InstanceDetails': {
                                'Family': 'm5',
                                'InstanceType': 'm5.large',
                            }
                        },
                        'UpfrontCost': '8000.0',
                        'EstimatedROI': '20.0',
                        'EstimatedSavingsAmount': '2000.0',
                        'EstimatedSavingsPercentage': '20.0',
                        'EstimatedMonthlySavingsAmount': '166.67',
                        'EstimatedOnDemandCost': '10000.0',
                        'EstimatedBreakEvenInMonths': '10.0',
                    }
                ],
            }
        ]
    }

    return mock_client


@pytest.fixture
def mock_compute_optimizer_client():
    """Create a mock Compute Optimizer boto3 client."""
    mock_client = MagicMock()

    # Set up mock response for get_ec2_instance_recommendations
    mock_client.get_ec2_instance_recommendations.return_value = {
        'instanceRecommendations': [
            {
                'instanceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
                'accountId': '123456789012',
                'instanceName': 'test-instance',
                'currentInstanceType': 't3.large',
                'finding': 'OVER_PROVISIONED',
                'utilizationMetrics': [
                    {
                        'name': 'CPU',
                        'statistic': 'MAXIMUM',
                        'value': 25.0,
                    },
                    {
                        'name': 'MEMORY',
                        'statistic': 'MAXIMUM',
                        'value': 40.0,
                    },
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    # Set up mock response for get_ebs_volume_recommendations
    mock_client.get_ebs_volume_recommendations.return_value = {
        'volumeRecommendations': [
            {
                'volumeArn': 'arn:aws:ec2:us-east-1:123456789012:volume/vol-0abc123def456',
                'accountId': '123456789012',
                'currentConfiguration': {
                    'volumeType': 'gp2',
                    'volumeSize': 100,
                },
                'finding': 'OVER_PROVISIONED',
                'utilizationMetrics': [
                    {
                        'name': 'VolumeReadOpsPerSecond',
                        'statistic': 'MAXIMUM',
                        'value': 100.0,
                    }
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    # Set up mock response for get_auto_scaling_group_recommendations
    mock_client.get_auto_scaling_group_recommendations.return_value = {
        'autoScalingGroupRecommendations': [
            {
                'autoScalingGroupArn': 'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:123:autoScalingGroupName/asg-test',
                'accountId': '123456789012',
                'autoScalingGroupName': 'asg-test',
                'currentConfiguration': {
                    'instanceType': 't3.large',
                },
                'finding': 'OVER_PROVISIONED',
                'utilizationMetrics': [
                    {
                        'name': 'CPU',
                        'statistic': 'MAXIMUM',
                        'value': 25.0,
                    }
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    # Set up mock response for get_lambda_function_recommendations
    mock_client.get_lambda_function_recommendations.return_value = {
        'lambdaFunctionRecommendations': [
            {
                'functionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
                'accountId': '123456789012',
                'functionName': 'test-function',
                'currentConfiguration': {
                    'memorySize': 1024,
                },
                'finding': 'OVER_PROVISIONED',
                'utilizationMetrics': [
                    {
                        'name': 'Memory',
                        'statistic': 'MAXIMUM',
                        'value': 512.0,
                    }
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    # Set up mock response for get_ecs_service_recommendations
    mock_client.get_ecs_service_recommendations.return_value = {
        'ecsServiceRecommendations': [
            {
                'serviceArn': 'arn:aws:ecs:us-east-1:123456789012:service/cluster/service',
                'accountId': '123456789012',
                'serviceName': 'test-service',
                'currentConfiguration': {
                    'memory': 1024,
                    'cpu': 512,
                },
                'finding': 'OVER_PROVISIONED',
                'utilizationMetrics': [
                    {
                        'name': 'Memory',
                        'statistic': 'MAXIMUM',
                        'value': 512.0,
                    }
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    # Set up mock response for get_rds_instance_recommendations
    mock_client.get_rds_instance_recommendations.return_value = {
        'instanceRecommendations': [
            {
                'instanceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                'accountId': '123456789012',
                'instanceName': 'test-db',
                'currentInstanceType': 'db.m5.large',
                'finding': 'OVER_PROVISIONED',
                'utilizationMetrics': [
                    {
                        'name': 'CPU',
                        'statistic': 'MAXIMUM',
                        'value': 25.0,
                    }
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    # Set up mock response for get_idle_recommendations
    mock_client.get_idle_recommendations.return_value = {
        'idleResourceRecommendations': [
            {
                'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
                'accountId': '123456789012',
                'resourceType': 'Ec2Instance',
                'finding': 'IDLE',
                'idleReasonCodes': ['LOW_CPU_UTILIZATION'],
                'utilizationMetrics': [
                    {
                        'name': 'CPU',
                        'statistic': 'MAXIMUM',
                        'value': 1.0,
                    }
                ],
                'lookbackPeriodInDays': 14.0,
            }
        ]
    }

    return mock_client


def test_format_timestamp():
    """Test format_timestamp function."""
    # Test with a valid timestamp
    timestamp = 1632825600000
    result = format_timestamp(timestamp)
    assert result and '2021-09-28' in result

    # Test with None
    result = format_timestamp(None)
    assert result is None

    # Test with invalid timestamp
    result = format_timestamp(None)
    assert result is None


def test_format_base_recommendation():
    """Test format_base_recommendation function."""
    # Setup
    recommendation = {
        'recommendationId': 'rec-12345',
        'accountId': '123456789012',
        'region': 'us-east-1',
        'resourceId': 'i-0abc123def456',
        'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
        'actionType': 'Modify',
        'currentResourceType': 'Ec2Instance',
        'recommendedResourceType': 'Ec2Instance',
        'estimatedMonthlySavings': 25.0,
        'estimatedSavingsPercentage': 30.0,
        'estimatedMonthlyCost': 75.0,
        'currencyCode': 'USD',
        'implementationEffort': 'MEDIUM',
        'lastRefreshTimestamp': 1632825600000,
        'recommendationLookbackPeriodInDays': 14,
        'costCalculationLookbackPeriodInDays': 14,
        'estimatedSavingsOverCostCalculationLookbackPeriod': 12.5,
        'currentResourceDetails': {
            'ec2ResourceDetails': {
                'instanceType': 't3.large',
            }
        },
        'recommendedResourceDetails': {
            'ec2ResourceDetails': {
                'instanceType': 't3.medium',
            }
        },
    }

    # Execute
    result = format_base_recommendation(recommendation)

    # Assert
    assert result['recommendation_id'] == 'rec-12345'
    assert result['account_id'] == '123456789012'
    assert result['region'] == 'us-east-1'
    assert result['resource_id'] == 'i-0abc123def456'
    assert result['estimated_monthly_savings'] == 25.0
    assert result['estimated_savings_percentage'] == 30.0
    assert result['estimated_monthly_cost'] == 75.0
    assert result['implementation_effort'] == 'MEDIUM'
    assert '2021-09-28' in result['last_refresh_timestamp']
    assert 'current_resource_details' in result
    assert 'recommended_resource_details' in result


@pytest.mark.asyncio
class TestGetSavingsPlansRecommendation:
    """Tests for get_savings_plans_recommendation function."""

    async def test_get_savings_plans_recommendation_success(self, mock_context, mock_ce_client):
        """Test get_savings_plans_recommendation successfully retrieves savings plans recommendations."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'accountId': '123456789012',
            'region': 'us-east-1',
            'actionType': 'PurchaseSavingsPlans',
            'recommendationLookbackPeriodInDays': 30,
            'recommendedResourceDetails': {
                'computeSavingsPlans': {
                    'configuration': {
                        'term': 'OneYear',
                        'paymentOption': 'AllUpfront',
                        'accountScope': 'Payer',
                    }
                }
            },
        }

        # Execute
        result = await get_savings_plans_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        mock_ce_client.get_savings_plans_purchase_recommendation.assert_called_once()
        call_kwargs = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]

        assert call_kwargs['SavingsPlansType'] == 'COMPUTE_SP'
        assert call_kwargs['TermInYears'] == 'ONE_YEAR'
        assert call_kwargs['PaymentOption'] == 'ALL_UPFRONT'
        assert call_kwargs['AccountScope'] == 'PAYER'

        assert 'SavingsPlansRecommendationSummary' in result
        assert result['SavingsPlansRecommendationSummary']['EstimatedSavingsAmount'] == '2000.0'

    async def test_get_savings_plans_recommendation_missing_key(
        self, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_recommendation when savings plans key is missing."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {
                'otherDetails': {}  # No SavingsPlans key
            },
        }

        # Execute
        result = await get_savings_plans_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        assert 'error' in result
        assert 'No Savings Plans details found' in result['error']

    async def test_get_savings_plans_recommendation_missing_params(
        self, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_recommendation when required parameters are missing."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {
                'computeSavingsPlans': {
                    'configuration': {
                        # Missing term, paymentOption, accountScope
                    }
                }
            },
        }

        # Execute
        result = await get_savings_plans_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        assert 'error' in result
        assert 'Missing required parameters' in result['error']

    async def test_get_savings_plans_recommendation_api_error(self, mock_context, mock_ce_client):
        """Test get_savings_plans_recommendation handles API errors."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'accountId': '123456789012',
            'region': 'us-east-1',
            'actionType': 'PurchaseSavingsPlans',
            'recommendationLookbackPeriodInDays': 30,
            'recommendedResourceDetails': {
                'computeSavingsPlans': {
                    'configuration': {
                        'term': 'OneYear',
                        'paymentOption': 'AllUpfront',
                        'accountScope': 'Payer',
                    }
                }
            },
        }

        # Simulate API error
        error = Exception('API error')
        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = error

        # Execute
        result = await get_savings_plans_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        assert 'error' in result
        assert 'Error getting Savings Plans recommendation' in result['error']
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestGetReservedInstancesRecommendation:
    """Tests for get_reserved_instances_recommendation function."""

    async def test_get_reserved_instances_recommendation_success(
        self, mock_context, mock_ce_client
    ):
        """Test get_reserved_instances_recommendation successfully retrieves RI recommendations."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'accountId': '123456789012',
            'region': 'us-east-1',
            'actionType': 'PurchaseReservedInstances',
            'recommendationLookbackPeriodInDays': 30,
            'recommendedResourceDetails': {
                'ec2ReservedInstances': {
                    'configuration': {
                        'term': 'OneYear',
                        'paymentOption': 'AllUpfront',
                    }
                }
            },
        }

        # Execute
        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        mock_ce_client.get_reservation_purchase_recommendation.assert_called_once()
        call_kwargs = mock_ce_client.get_reservation_purchase_recommendation.call_args[1]

        assert call_kwargs['Service'] == 'Amazon Elastic Compute Cloud - Compute'
        assert call_kwargs['TermInYears'] == 'ONE_YEAR'
        assert call_kwargs['PaymentOption'] == 'ALL_UPFRONT'

        assert 'Recommendations' in result
        assert (
            result['Recommendations'][0]['RecommendationSummary']['EstimatedSavingsAmount']
            == '2000.0'
        )

    async def test_get_reserved_instances_recommendation_missing_key(
        self, mock_context, mock_ce_client
    ):
        """Test get_reserved_instances_recommendation when RI key is missing."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {
                'otherDetails': {}  # No RI key
            },
        }

        # Execute
        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        assert 'error' in result
        assert 'No Reserved Instances details found' in result['error']

    async def test_get_reserved_instances_recommendation_missing_params(
        self, mock_context, mock_ce_client
    ):
        """Test get_reserved_instances_recommendation when required parameters are missing."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {
                'ec2ReservedInstances': {
                    'configuration': {
                        # Missing term, paymentOption
                    }
                }
            },
        }

        # Execute
        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        assert 'error' in result
        assert 'Missing required parameters' in result['error']

    async def test_get_reserved_instances_recommendation_api_error(
        self, mock_context, mock_ce_client
    ):
        """Test get_reserved_instances_recommendation handles API errors."""
        # Setup
        recommendation = {
            'recommendationId': 'rec-12345',
            'accountId': '123456789012',
            'region': 'us-east-1',
            'actionType': 'PurchaseReservedInstances',
            'recommendationLookbackPeriodInDays': 30,
            'recommendedResourceDetails': {
                'ec2ReservedInstances': {
                    'configuration': {
                        'term': 'OneYear',
                        'paymentOption': 'AllUpfront',
                    }
                }
            },
        }

        # Simulate API error
        error = Exception('API error')
        mock_ce_client.get_reservation_purchase_recommendation.side_effect = error

        # Execute
        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        # Assert
        assert 'error' in result
        assert 'Error getting Reserved Instance recommendation' in result['error']
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestGetCostExplorerData:
    """Tests for get_cost_explorer_data function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_savings_plans_recommendation'
    )
    async def test_get_cost_explorer_data_savings_plans(
        self, mock_get_savings_plans, mock_context, mock_ce_client
    ):
        """Test get_cost_explorer_data with savings plans recommendation."""
        # Setup
        recommendation = {
            'actionType': 'PurchaseSavingsPlans',
        }
        mock_get_savings_plans.return_value = {'test': 'data'}

        # Execute
        result = await get_cost_explorer_data(mock_context, recommendation)

        # Assert
        mock_get_savings_plans.assert_called_once()
        assert result == {'test': 'data'}

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_reserved_instances_recommendation'
    )
    async def test_get_cost_explorer_data_reserved_instances(
        self, mock_get_ri_rec, mock_context, mock_ce_client
    ):
        """Test get_cost_explorer_data with reserved instances recommendation."""
        # Setup
        recommendation = {
            'actionType': 'PurchaseReservedInstances',
        }
        mock_get_ri_rec.return_value = {'test': 'data'}

        # Execute
        result = await get_cost_explorer_data(mock_context, recommendation)

        # Assert
        mock_get_ri_rec.assert_called_once()
        assert result == {'test': 'data'}

    async def test_get_cost_explorer_data_unsupported_type(self, mock_context):
        """Test get_cost_explorer_data with unsupported action type."""
        # Setup
        recommendation = {
            'actionType': 'UnsupportedType',
        }

        # Execute
        result = await get_cost_explorer_data(mock_context, recommendation)

        # Assert
        assert 'error' in result
        assert 'Unsupported action type' in result['error']


@pytest.mark.asyncio
class TestGetComputeOptimizerData:
    """Tests for get_compute_optimizer_data function."""

    async def test_get_compute_optimizer_data_missing_arn(self, mock_context):
        """Test get_compute_optimizer_data when resource ARN is missing."""
        # Setup
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'Ec2Instance',
            # No resourceArn
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        assert 'error' in result
        assert 'No resource ARN found' in result['error']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_idle_resource(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with idle resource recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Stop',
            'currentResourceType': 'Ec2Instance',
            'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_create_aws_client.assert_called_once_with(
            'compute-optimizer', region_name='us-east-1'
        )
        mock_compute_optimizer_client.get_idle_recommendations.assert_called_once_with(
            resourceArns=['arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456']
        )
        assert 'idleResourceRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_ec2_instance(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with EC2 instance recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'Ec2Instance',
            'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_compute_optimizer_client.get_ec2_instance_recommendations.assert_called_once_with(
            instanceArns=['arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456']
        )
        assert 'instanceRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_ebs_volume(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with EBS volume recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'EbsVolume',
            'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:volume/vol-0abc123def456',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_compute_optimizer_client.get_ebs_volume_recommendations.assert_called_once_with(
            volumeArns=['arn:aws:ec2:us-east-1:123456789012:volume/vol-0abc123def456']
        )
        assert 'volumeRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_ec2_asg(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with EC2 ASG recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'Ec2AutoScalingGroup',
            'resourceArn': 'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:123:autoScalingGroupName/asg-test',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_compute_optimizer_client.get_auto_scaling_group_recommendations.assert_called_once_with(
            autoScalingGroupArns=[
                'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:123:autoScalingGroupName/asg-test'
            ]
        )
        assert 'autoScalingGroupRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_lambda_function(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with Lambda function recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'LambdaFunction',
            'resourceArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_compute_optimizer_client.get_lambda_function_recommendations.assert_called_once_with(
            functionArns=['arn:aws:lambda:us-east-1:123456789012:function:test-function']
        )
        assert 'lambdaFunctionRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_ecs_service(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with ECS service recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'EcsService',
            'resourceArn': 'arn:aws:ecs:us-east-1:123456789012:service/cluster/service',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_compute_optimizer_client.get_ecs_service_recommendations.assert_called_once_with(
            serviceArns=['arn:aws:ecs:us-east-1:123456789012:service/cluster/service']
        )
        assert 'ecsServiceRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_rds_instance(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with RDS instance recommendation."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'RdsDbInstance',
            'resourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        mock_compute_optimizer_client.get_rds_instance_recommendations.assert_called_once_with(
            instanceArns=['arn:aws:rds:us-east-1:123456789012:db:test-db']
        )
        assert 'instanceRecommendations' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_unsupported_type(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """Test get_compute_optimizer_data with unsupported resource type."""
        # Setup
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'UnsupportedType',
            'resourceArn': 'arn:aws:unsupported:us-east-1:123456789012:resource/test',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        assert 'error' in result
        assert 'Unsupported resource type' in result['error']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_api_error(
        self, mock_create_aws_client, mock_context
    ):
        """Test get_compute_optimizer_data handles API errors."""
        # Setup
        error = Exception('API error')
        mock_create_aws_client.side_effect = error
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'Ec2Instance',
            'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456',
            'region': 'us-east-1',
        }

        # Execute
        result = await get_compute_optimizer_data(mock_context, recommendation)

        # Assert
        assert 'error' in result
        assert 'Error getting Compute Optimizer data' in result['error']
        mock_context.error.assert_called_once()


class TestGetTemplateForRecommendation:
    """Tests for get_template_for_recommendation function."""

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='Test template content')
    def test_get_template_for_recommendation_by_action_type(self, mock_file, mock_exists):
        """Test get_template_for_recommendation with action type mapping."""
        # Setup
        mock_exists.return_value = True
        recommendation = {
            'actionType': 'PurchaseSavingsPlans',
        }
        additional_details = {}

        # Execute
        result = get_template_for_recommendation(recommendation, additional_details)

        # Assert
        assert result == 'Test template content'
        assert mock_file.call_count == 1
        assert 'savings_plans.template' in mock_file.call_args[0][0]

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='Test template content')
    def test_get_template_for_recommendation_by_resource_type(self, mock_file, mock_exists):
        """Test get_template_for_recommendation with resource type mapping."""
        # Setup
        mock_exists.return_value = True
        recommendation = {
            'actionType': 'Modify',  # Not in template map
            'currentResourceType': 'Ec2Instance',  # In template map
        }
        additional_details = {}

        # Execute
        result = get_template_for_recommendation(recommendation, additional_details)

        # Assert
        assert result == 'Test template content'
        assert mock_file.call_count == 1
        assert 'ec2_instance.template' in mock_file.call_args[0][0]

    @patch('os.path.exists')
    def test_get_template_for_recommendation_no_template_file(self, mock_exists):
        """Test get_template_for_recommendation when template file doesn't exist."""
        # Setup
        mock_exists.return_value = False
        recommendation = {
            'actionType': 'PurchaseSavingsPlans',
        }
        additional_details = {}

        # Execute
        result = get_template_for_recommendation(recommendation, additional_details)

        # Assert
        assert result is None

    def test_get_template_for_recommendation_unsupported_type(self):
        """Test get_template_for_recommendation with unsupported types."""
        # Setup
        recommendation = {
            'actionType': 'UnsupportedAction',
            'currentResourceType': 'UnsupportedResource',
        }
        additional_details = {}

        # Execute
        result = get_template_for_recommendation(recommendation, additional_details)

        # Assert
        assert result is None


@pytest.mark.asyncio
class TestProcessRecommendation:
    """Tests for process_recommendation function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_compute_optimizer_data'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.format_base_recommendation'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_template_for_recommendation'
    )
    async def test_process_recommendation_compute_resource(
        self, mock_get_template, mock_format_base, mock_get_compute_optimizer, mock_context
    ):
        """Test process_recommendation with compute resource recommendation."""
        # Setup
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'Ec2Instance',
        }
        mock_format_base.return_value = {'formatted': 'base_data'}
        mock_get_compute_optimizer.return_value = {'optimizer': 'data'}
        mock_get_template.return_value = 'Template content'

        # Execute
        result = await process_recommendation(mock_context, recommendation)

        # Assert
        mock_format_base.assert_called_once_with(recommendation)
        mock_get_compute_optimizer.assert_called_once_with(mock_context, recommendation)
        mock_get_template.assert_called_once_with(recommendation, {'optimizer': 'data'})

        assert result['base_recommendation'] == {'formatted': 'base_data'}
        assert result['additional_details'] == {'optimizer': 'data'}
        assert result['template'] == 'Template content'
        assert 'formatting_instructions' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_cost_explorer_data'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.format_base_recommendation'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_template_for_recommendation'
    )
    async def test_process_recommendation_savings_plans(
        self, mock_get_template, mock_format_base, mock_get_cost_explorer, mock_context
    ):
        """Test process_recommendation with savings plans recommendation."""
        # Setup
        recommendation = {
            'actionType': 'PurchaseSavingsPlans',
        }
        mock_format_base.return_value = {'formatted': 'base_data'}
        mock_get_cost_explorer.return_value = {'cost_explorer': 'data'}
        mock_get_template.return_value = 'Template content'

        # Execute
        result = await process_recommendation(mock_context, recommendation)

        # Assert
        mock_format_base.assert_called_once_with(recommendation)
        mock_get_cost_explorer.assert_called_once_with(mock_context, recommendation)
        mock_get_template.assert_called_once_with(recommendation, {'cost_explorer': 'data'})

        assert result['base_recommendation'] == {'formatted': 'base_data'}
        assert result['additional_details'] == {'cost_explorer': 'data'}
        assert result['template'] == 'Template content'
        assert 'formatting_instructions' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_cost_explorer_data'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.format_base_recommendation'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_template_for_recommendation'
    )
    async def test_process_recommendation_reserved_instances(
        self, mock_get_template, mock_format_base, mock_get_cost_explorer, mock_context
    ):
        """Test process_recommendation with reserved instances recommendation."""
        # Setup
        recommendation = {
            'actionType': 'PurchaseReservedInstances',
        }
        mock_format_base.return_value = {'formatted': 'base_data'}
        mock_get_cost_explorer.return_value = {'cost_explorer': 'data'}
        mock_get_template.return_value = 'Template content'

        # Execute
        result = await process_recommendation(mock_context, recommendation)

        # Assert
        mock_format_base.assert_called_once_with(recommendation)
        mock_get_cost_explorer.assert_called_once_with(mock_context, recommendation)
        mock_get_template.assert_called_once_with(recommendation, {'cost_explorer': 'data'})

        assert result['base_recommendation'] == {'formatted': 'base_data'}
        assert result['additional_details'] == {'cost_explorer': 'data'}
        assert result['template'] == 'Template content'
        assert 'formatting_instructions' in result

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_compute_optimizer_data'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.format_base_recommendation'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.get_template_for_recommendation'
    )
    async def test_process_recommendation_no_template(
        self, mock_get_template, mock_format_base, mock_get_compute_optimizer, mock_context
    ):
        """Test process_recommendation when no template is available."""
        # Setup
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'Ec2Instance',
        }
        mock_format_base.return_value = {'formatted': 'base_data'}
        mock_get_compute_optimizer.return_value = {'optimizer': 'data'}
        mock_get_template.return_value = None  # No template found

        # Execute
        result = await process_recommendation(mock_context, recommendation)

        # Assert
        assert result['base_recommendation'] == {'formatted': 'base_data'}
        assert result['additional_details'] == {'optimizer': 'data'}
        assert 'template' not in result
        assert 'formatting_instructions' not in result


def test_recommendation_details_server_initialization():
    """Test that the recommendation_details_server is properly initialized."""
    # Verify the server name
    assert recommendation_details_server.name == 'recommendation-details-tools'

    # Verify the server instructions
    assert recommendation_details_server.instructions and (
        'Tools for working with AWS Cost Optimization Hub enhanced recommendation details'
        in recommendation_details_server.instructions
    )
