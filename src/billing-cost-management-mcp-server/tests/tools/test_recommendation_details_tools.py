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

import botocore.session
import builtins
import io
import pytest
from awslabs.billing_cost_management_mcp_server.tools import recommendation_details_tools
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
from awslabs.billing_cost_management_mcp_server.utilities.constants import (
    ACCOUNT_SCOPE_MAP,
    PAYMENT_OPTION_MAP,
    SAVINGS_PLANS_TYPE_MAP,
    SERVICE_MAP,
    TERM_MAP,
)
from datetime import datetime, timezone
from fastmcp import Context
from pathlib import Path
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
            'SavingsPlansPurchaseRecommendationSummary': {
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
                    'EstimatedSPCost': '10000.0',
                    'EstimatedSavingsAmount': '2000.0',
                    'EstimatedSavingsPercentage': '20.0',
                    'EstimatedMonthlySavingsAmount': '166.67',
                    'EstimatedOnDemandCost': '10000.0',
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
                    'TotalEstimatedMonthlySavingsAmount': '166.67',
                    'TotalEstimatedMonthlySavingsPercentage': '20.0',
                    'CurrencyCode': 'USD',
                },
                'RecommendationDetails': [
                    {
                        'AccountId': '123456789012',
                        'InstanceDetails': {
                            'EC2InstanceDetails': {
                                'Family': 'm5',
                                'InstanceType': 'm5.large',
                                'Region': 'US East (N. Virginia)',
                            }
                        },
                        'UpfrontCost': '8000.0',
                        'EstimatedMonthlySavingsAmount': '166.67',
                        'EstimatedMonthlySavingsPercentage': '20.0',
                        'EstimatedMonthlyOnDemandCost': '833.33',
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

    # Set up mock response for get_rds_database_recommendations
    mock_client.get_rds_database_recommendations.return_value = {
        'rdsDBRecommendations': [
            {
                'resourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
                'accountId': '123456789012',
                'engine': 'mysql',
                'currentDBInstanceClass': 'db.m5.large',
                'instanceFinding': 'Overprovisioned',
                'utilizationMetrics': [
                    {
                        'name': 'CPU',
                        'statistic': 'Maximum',
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
    # Epoch milliseconds
    assert format_timestamp(1632825600000) == '2021-09-28T10:40:00'

    # Test with None
    assert format_timestamp(None) is None


def test_format_timestamp_accepts_boto3_datetime():
    """boto3 returns datetime; it must format, not fail on datetime / int."""
    assert format_timestamp(datetime(2021, 9, 28, 10, 40)) == '2021-09-28T10:40:00'


def test_format_timestamp_accepts_epoch_seconds():
    """Epoch seconds (AWS JSON wire form) are not divided by 1000 into 1970."""
    assert format_timestamp(1632825600) == '2021-09-28T10:40:00'


def test_format_timestamp_never_returns_error_text():
    """An unconvertible value yields None rather than an 'Error: ...' string."""
    assert format_timestamp(object()) is None


def test_format_base_recommendation_with_boto3_datetime():
    """The rec-details last_refresh_timestamp is a real timestamp for boto3 input."""
    result = format_base_recommendation(
        {
            'recommendationId': 'rec-1',
            'lastRefreshTimestamp': datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        }
    )
    assert result['last_refresh_timestamp'] == '2026-09-01T12:00:00'


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

        summary = result['SavingsPlansPurchaseRecommendationSummary']
        assert summary['EstimatedSavingsAmount'] == '2000.0'
        assert summary['EstimatedROI'] == '20.0'
        detail = result['SavingsPlansPurchaseRecommendationDetails'][0]
        assert 'EstimatedBreakEvenInMonths' not in detail

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

    async def test_get_savings_plans_recommendation_database_savings_plans(
        self, mock_context, mock_ce_client
    ):
        """A databaseSavingsPlans recommendation maps to Cost Explorer's DATABASE_SP."""
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {
                'databaseSavingsPlans': {
                    'configuration': {
                        'term': 'OneYear',
                        'paymentOption': 'NoUpfront',
                        'accountScope': 'Payer',
                    }
                }
            },
        }

        await get_savings_plans_recommendation(mock_context, recommendation, mock_ce_client)

        call_kwargs = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
        assert call_kwargs['SavingsPlansType'] == 'DATABASE_SP'

    async def test_get_savings_plans_recommendation_sdk_unknown_member(
        self, mock_context, mock_ce_client
    ):
        """An SDK too old to parse databaseSavingsPlans gets a clear error, not the raw key."""
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {'SDK_UNKNOWN_MEMBER': {'name': 'databaseSavingsPlans'}},
        }

        result = await get_savings_plans_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        assert "'databaseSavingsPlans'" in result['error']
        assert 'Savings Plans purchase details are unavailable' in result['error']
        assert 'SDK_UNKNOWN_MEMBER' not in result['error']
        mock_ce_client.get_savings_plans_purchase_recommendation.assert_not_called()

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

    async def test_savings_plans_keep_partial_upfront(self, mock_context, mock_ce_client):
        """The DynamoDB reserved capacity remap does not reach Savings Plans lookups."""
        recommendation = {
            'recommendationId': 'rec-sp',
            'recommendedResourceDetails': {
                'computeSavingsPlans': {
                    'configuration': {
                        'term': 'OneYear',
                        'paymentOption': 'PartialUpfront',
                        'accountScope': 'Payer',
                    }
                }
            },
        }

        await get_savings_plans_recommendation(mock_context, recommendation, mock_ce_client)

        call_kwargs = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
        assert call_kwargs['PaymentOption'] == 'PARTIAL_UPFRONT'


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
        ri_rec = result['Recommendations'][0]
        assert ri_rec['RecommendationSummary']['TotalEstimatedMonthlySavingsAmount'] == '166.67'
        assert ri_rec['RecommendationDetails'][0]['EstimatedBreakEvenInMonths'] == '10.0'

    @pytest.mark.parametrize(
        'ri_key, service',
        [
            ('dynamoDbReservedCapacity', 'Amazon DynamoDB Service'),
            ('memoryDbReservedInstances', 'Amazon MemoryDB Service'),
        ],
    )
    async def test_get_reserved_instances_recommendation_service_names(
        self, mock_context, mock_ce_client, ri_key, service
    ):
        """DynamoDB reserved capacity and MemoryDB use Cost Explorer's '... Service' names."""
        recommendation = {
            'recommendationId': 'rec-12345',
            'actionType': 'PurchaseReservedInstances',
            'recommendedResourceDetails': {
                ri_key: {'configuration': {'term': 'OneYear', 'paymentOption': 'NoUpfront'}}
            },
        }

        await get_reserved_instances_recommendation(mock_context, recommendation, mock_ce_client)

        call_kwargs = mock_ce_client.get_reservation_purchase_recommendation.call_args[1]
        assert call_kwargs['Service'] == service
        assert call_kwargs['PaymentOption'] == 'NO_UPFRONT'

    async def test_get_reserved_instances_recommendation_sdk_unknown_member(
        self, mock_context, mock_ce_client
    ):
        """A COH type the SDK cannot parse yields a clear error and no Cost Explorer call."""
        recommendation = {
            'recommendationId': 'rec-12345',
            'recommendedResourceDetails': {'SDK_UNKNOWN_MEMBER': {'name': 'newReservedThing'}},
        }

        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        assert "'newReservedThing'" in result['error']
        assert 'cannot parse' in result['error']
        assert 'SDK_UNKNOWN_MEMBER' not in result['error']
        mock_ce_client.get_reservation_purchase_recommendation.assert_not_called()

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

    async def test_dynamodb_reserved_capacity_requests_heavy_utilization(
        self, mock_context, mock_ce_client
    ):
        """COH's PartialUpfront DynamoDB reserved capacity is HEAVY_UTILIZATION in Cost Explorer.

        Cost Explorer returns no DynamoDB recommendation for PARTIAL_UPFRONT.
        """
        # The configuration shape Cost Optimization Hub returns for DynamoDB reserved capacity
        recommendation = {
            'recommendationId': 'rec-ddb',
            'accountId': '123456789012',
            'actionType': 'PurchaseReservedInstances',
            'currentResourceType': 'DynamoDbReservedCapacity',
            'recommendationLookbackPeriodInDays': 30,
            'recommendedResourceDetails': {
                'dynamoDbReservedCapacity': {
                    'configuration': {
                        'accountScope': 'Payer',
                        'service': 'Amazon DynamoDB Service',
                        'term': 'OneYear',
                        'paymentOption': 'PartialUpfront',
                        'reservedInstancesRegion': 'us-west-2',
                        'upfrontCost': '150.0',
                        'monthlyRecurringCost': '9.49',
                        'numberOfCapacityUnitsToPurchase': '100',
                        'capacityUnits': 'Write',
                    },
                    'costCalculation': {},
                }
            },
        }
        mock_ce_client.get_reservation_purchase_recommendation.return_value = {
            'Recommendations': [
                {
                    'AccountScope': 'Payer',
                    'LookbackPeriodInDays': '30',
                    'TermInYears': '1',
                    'PaymentOption': 'Heavy_Utilization',
                    'RecommendationDetails': [
                        {
                            'AccountId': '123456789012',
                            'RecommendedNumberOfCapacityUnitsToPurchase': '100',
                            'ReservedCapacityDetails': {
                                'DynamoDBCapacityDetails': {
                                    'CapacityUnits': 'Write',
                                    'Region': 'us-west-2',
                                }
                            },
                        }
                    ],
                }
            ]
        }

        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, mock_ce_client
        )

        call_kwargs = mock_ce_client.get_reservation_purchase_recommendation.call_args[1]
        assert call_kwargs == {
            'Service': 'Amazon DynamoDB Service',
            'TermInYears': 'ONE_YEAR',
            'PaymentOption': 'HEAVY_UTILIZATION',
            'LookbackPeriodInDays': 'THIRTY_DAYS',
        }
        assert result['Recommendations'][0]['PaymentOption'] == 'Heavy_Utilization'
        output = _ce_model().operation_model('GetReservationPurchaseRecommendation').output_shape
        assert list(_keys_outside_shape(result, output)) == []

    @pytest.mark.parametrize('ri_key', sorted(set(SERVICE_MAP) - {'dynamoDbReservedCapacity'}))
    async def test_other_reserved_instances_keep_partial_upfront(
        self, mock_context, mock_ce_client, ri_key
    ):
        """Only DynamoDB reserved capacity is remapped; RIs send PARTIAL_UPFRONT as before."""
        recommendation = {
            'recommendationId': 'rec-12345',
            'actionType': 'PurchaseReservedInstances',
            'recommendedResourceDetails': {
                ri_key: {'configuration': {'term': 'OneYear', 'paymentOption': 'PartialUpfront'}}
            },
        }

        await get_reserved_instances_recommendation(mock_context, recommendation, mock_ce_client)

        call_kwargs = mock_ce_client.get_reservation_purchase_recommendation.call_args[1]
        assert call_kwargs['PaymentOption'] == 'PARTIAL_UPFRONT'

    @pytest.mark.parametrize('payment_option', ['AllUpfront', 'PartialUpfront', 'NoUpfront'])
    async def test_dynamodb_payment_options_are_cost_explorer_values(
        self, mock_context, mock_ce_client, payment_option
    ):
        """Every DynamoDB payment option the tool sends is in Cost Explorer's PaymentOption enum."""
        recommendation = {
            'recommendationId': 'rec-ddb',
            'actionType': 'PurchaseReservedInstances',
            'recommendedResourceDetails': {
                'dynamoDbReservedCapacity': {
                    'configuration': {'term': 'OneYear', 'paymentOption': payment_option}
                }
            },
        }

        await get_reserved_instances_recommendation(mock_context, recommendation, mock_ce_client)

        call_kwargs = mock_ce_client.get_reservation_purchase_recommendation.call_args[1]
        assert call_kwargs['PaymentOption'] in _ce_model().shape_for('PaymentOption').enum


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
        mock_compute_optimizer_client.get_rds_database_recommendations.assert_called_once_with(
            resourceArns=['arn:aws:rds:us-east-1:123456789012:db:test-db']
        )
        assert result['rdsDBRecommendations'][0]['currentDBInstanceClass'] == 'db.m5.large'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_rds_instance_real_client(
        self, mock_create_aws_client, mock_context
    ):
        """The RDS call matches the real boto3 compute-optimizer API (stubbed)."""
        import boto3
        from botocore.stub import Stubber

        client = boto3.client(
            'compute-optimizer',
            region_name='us-east-1',
            aws_access_key_id='a',
            aws_secret_access_key='b',
        )
        arn = 'arn:aws:rds:us-east-1:123456789012:db:test-db'
        expected = {
            'rdsDBRecommendations': [
                {
                    'resourceArn': arn,
                    'currentDBInstanceClass': 'db.r5.xlarge',
                    'instanceFinding': 'Overprovisioned',
                }
            ]
        }
        mock_create_aws_client.return_value = client
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'RdsDbInstance',
            'resourceArn': arn,
            'region': 'us-east-1',
        }

        with Stubber(client) as stubber:
            stubber.add_response(
                'get_rds_database_recommendations', expected, {'resourceArns': [arn]}
            )
            result = await get_compute_optimizer_data(mock_context, recommendation)
            stubber.assert_no_pending_responses()

        assert result['rdsDBRecommendations'] == expected['rdsDBRecommendations']
        assert not hasattr(client, 'get_rds_instance_recommendations')

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
    )
    async def test_get_compute_optimizer_data_rds_instance_error(
        self, mock_create_aws_client, mock_context, mock_compute_optimizer_client
    ):
        """An RDS API failure is reported as an error, not raised."""
        mock_create_aws_client.return_value = mock_compute_optimizer_client
        mock_compute_optimizer_client.get_rds_database_recommendations.side_effect = Exception(
            'boom'
        )
        recommendation = {
            'actionType': 'Modify',
            'currentResourceType': 'RdsDbInstance',
            'resourceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db',
            'region': 'us-east-1',
        }

        result = await get_compute_optimizer_data(mock_context, recommendation)

        assert 'Error getting Compute Optimizer data' in result['error']

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


TEMPLATES_DIR = (
    Path(recommendation_details_tools.__file__).parent.parent
    / 'templates'
    / 'recommendation_templates'
)

# Recommendation that selects each bundled template
TEMPLATE_CASES = {
    'savings_plans': {'actionType': 'PurchaseSavingsPlans'},
    'reserved_instances': {'actionType': 'PurchaseReservedInstances'},
    'idle': {'actionType': 'Stop'},
    'ec2_instance': {'currentResourceType': 'Ec2Instance'},
    'ec2_asg': {'currentResourceType': 'Ec2AutoScalingGroup'},
    'ebs_volume': {'currentResourceType': 'EbsVolume'},
    'ecs_service': {'currentResourceType': 'EcsService'},
    'lambda_function': {'currentResourceType': 'LambdaFunction'},
    'rds_database': {'currentResourceType': 'RdsDbInstance'},
}


@pytest.fixture
def legacy_default_encoding(monkeypatch):
    """Make text-mode file I/O behave like a Windows host whose default encoding is cp1252.

    ``open()`` called without an ``encoding`` uses cp1252 (and, on Python 3.11+,
    ``Path.read_text()`` too; on 3.10 ``pathlib`` binds ``io.open`` at import time, so only
    the builtin ``open()`` is affected, which is what the code under test uses). This
    reproduces such a host on any platform, including when the test run itself has
    UTF-8 mode enabled.
    """
    real_open = io.open

    def legacy_open(
        file,
        mode='r',
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
    ):
        if 'b' not in mode and encoding in (None, 'locale'):
            encoding = 'cp1252'
        return real_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def legacy_text_encoding(encoding, stacklevel=2):
        return 'locale' if encoding is None else encoding

    monkeypatch.setattr(builtins, 'open', legacy_open)
    monkeypatch.setattr(io, 'open', legacy_open)
    monkeypatch.setattr(io, 'text_encoding', legacy_text_encoding)


class TestGetTemplateForRecommendationEncoding:
    """The bundled templates are UTF-8 and must read the same whatever the host's default is."""

    def test_every_bundled_template_has_a_case(self):
        """Guard: a new template file must be added to TEMPLATE_CASES."""
        assert {path.stem for path in TEMPLATES_DIR.glob('*.template')} == set(TEMPLATE_CASES)

    @pytest.mark.parametrize('name', sorted(TEMPLATE_CASES))
    def test_template_is_read_as_utf8(self, name, legacy_default_encoding):
        """Each template is returned exactly as stored, not as None or mojibake."""
        expected = (TEMPLATES_DIR / f'{name}.template').read_text(encoding='utf-8')

        result = get_template_for_recommendation(TEMPLATE_CASES[name], {})

        assert result == expected
        # Every bundled template has non-ASCII characters; make sure the comparison above
        # is exercising a decoding difference.
        assert not expected.isascii()


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
        assert 'warning' not in result
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
        assert 'warning' not in result
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
        assert 'warning' not in result
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


async def test_rec_details_description_documents_commitment_metrics():
    """The schema the agent sees names break-even as RI-only and ROI as the SP metric."""
    tools = {t.name: t for t in await recommendation_details_server.list_tools()}
    description = tools['rec-details'].description or ''

    assert 'EstimatedBreakEvenInMonths is per RecommendationDetails row' in description
    assert 'Savings Plans recommendations carry no break-even' in description
    assert 'EstimatedROI' in description and 'not a payback period' in description


async def test_rec_details_description_names_dynamodb_payment_option():
    """The schema tells the agent why a DynamoDB rec's two payment options differ."""
    tools = {t.name: t for t in await recommendation_details_server.list_tools()}
    description = tools['rec-details'].description or ''

    assert 'DynamoDB reserved capacity' in description
    assert 'PartialUpfront' in description and 'Heavy_Utilization' in description
    assert 'not a mismatch' in description


def _ce_model():
    return botocore.session.get_session().get_service_model('ce')


def test_break_even_is_ri_only_in_botocore_model():
    """Pin the Cost Explorer shape asymmetry the tool description relies on."""
    ce = _ce_model()
    ri_detail = ce.shape_for('ReservationPurchaseRecommendationDetail').members
    sp_detail = ce.shape_for('SavingsPlansPurchaseRecommendationDetail').members

    assert 'EstimatedBreakEvenInMonths' in ri_detail
    assert 'EstimatedBreakEvenInMonths' not in sp_detail
    assert 'EstimatedROI' in sp_detail and 'EstimatedROI' not in ri_detail


def _keys_outside_shape(value, shape, path=''):
    """Yield every dict key in value that the botocore shape does not declare."""
    if shape.type_name == 'structure':
        for key, child in value.items():
            if key not in shape.members:
                yield f'{path}{key}'
            else:
                yield from _keys_outside_shape(child, shape.members[key], f'{path}{key}.')
    elif shape.type_name == 'list':
        for item in value:
            yield from _keys_outside_shape(item, shape.member, f'{path}[].')


@pytest.mark.parametrize(
    'method, operation',
    [
        ('get_savings_plans_purchase_recommendation', 'GetSavingsPlansPurchaseRecommendation'),
        ('get_reservation_purchase_recommendation', 'GetReservationPurchaseRecommendation'),
    ],
)
def test_ce_mocks_match_botocore_output_shapes(mock_ce_client, method, operation):
    """The Cost Explorer mocks use only keys the real API can return."""
    response = getattr(mock_ce_client, method).return_value
    output_shape = _ce_model().operation_model(operation).output_shape

    assert list(_keys_outside_shape(response, output_shape)) == []


def test_every_coh_commitment_type_is_mapped():
    """Every COH commitment ResourceDetails member reaches a Cost Explorer lookup."""
    coh = botocore.session.get_session().get_service_model('cost-optimization-hub')
    members = coh.shape_for('ResourceDetails').members
    commitment_suffixes = ('ReservedInstances', 'ReservedCapacity', 'SavingsPlans')
    commitment_members = {m for m in members if m.endswith(commitment_suffixes)}

    unmapped = commitment_members - set(SERVICE_MAP) - set(SAVINGS_PLANS_TYPE_MAP)
    assert unmapped == set()


def test_every_ce_savings_plans_type_is_mapped():
    """Every Savings Plans type Cost Explorer supports has a COH key mapped to it."""
    supported = set(_ce_model().shape_for('SupportedSavingsPlansType').enum)

    assert supported - set(SAVINGS_PLANS_TYPE_MAP.values()) == set()


# Commitment configurations in the shape Cost Optimization Hub returns them (field names and
# enum spellings from live responses; amounts are synthetic, sizing fields trimmed).
# COH spells the three-year term 'ThreeYears'.
COH_SP_THREE_YEAR = {
    'actionType': 'PurchaseSavingsPlans',
    'recommendationLookbackPeriodInDays': 30,
    'recommendedResourceDetails': {
        'computeSavingsPlans': {
            'configuration': {
                'accountScope': 'Linked',
                'term': 'ThreeYears',
                'paymentOption': 'AllUpfront',
                'hourlyCommitment': '0.50',
            }
        }
    },
}
COH_RDS_RI_THREE_YEAR = {
    'actionType': 'PurchaseReservedInstances',
    'recommendationLookbackPeriodInDays': 30,
    'recommendedResourceDetails': {
        'rdsReservedInstances': {
            'configuration': {
                'accountScope': 'Linked',
                'service': 'Amazon Relational Database Service',
                'term': 'ThreeYears',
                'paymentOption': 'AllUpfront',
                'instanceType': 'db.r6g.large',
                'databaseEngine': 'Aurora PostgreSQL',
            }
        }
    },
}
COH_DYNAMODB_RC_THREE_YEAR = {
    'actionType': 'PurchaseReservedInstances',
    'recommendationLookbackPeriodInDays': 30,
    'recommendedResourceDetails': {
        'dynamoDbReservedCapacity': {
            'configuration': {
                'accountScope': 'Linked',
                'service': 'Amazon DynamoDB Service',
                'term': 'ThreeYears',
                'paymentOption': 'PartialUpfront',
                'capacityUnits': 'Write',
            }
        }
    },
}
COH_EC2_RI_ONE_YEAR = {
    'actionType': 'PurchaseReservedInstances',
    'recommendationLookbackPeriodInDays': 30,
    'recommendedResourceDetails': {
        'ec2ReservedInstances': {
            'configuration': {
                'accountScope': 'Linked',
                'service': 'Amazon Elastic Compute Cloud - Compute',
                'term': 'OneYear',
                'paymentOption': 'AllUpfront',
                'offeringClass': 'Standard',
                'instanceType': 'm5.large',
            }
        }
    },
}
COH_SP_ONE_YEAR = {
    'actionType': 'PurchaseSavingsPlans',
    'recommendationLookbackPeriodInDays': 30,
    'recommendedResourceDetails': {
        'computeSavingsPlans': {
            'configuration': {
                'accountScope': 'Linked',
                'term': 'OneYear',
                'paymentOption': 'AllUpfront',
                'hourlyCommitment': '1.00',
            }
        }
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'recommendation, term, payment_option',
    [
        (COH_SP_THREE_YEAR, 'THREE_YEARS', 'ALL_UPFRONT'),
        (COH_SP_ONE_YEAR, 'ONE_YEAR', 'ALL_UPFRONT'),
    ],
)
async def test_savings_plans_coh_terms_reach_cost_explorer(
    mock_context, mock_ce_client, recommendation, term, payment_option
):
    """A Savings Plans recommendation of either COH term is looked up in Cost Explorer."""
    result = await get_savings_plans_recommendation(mock_context, recommendation, mock_ce_client)

    assert 'error' not in result
    call_kwargs = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
    assert call_kwargs['SavingsPlansType'] == 'COMPUTE_SP'
    assert call_kwargs['TermInYears'] == term
    assert call_kwargs['PaymentOption'] == payment_option
    assert call_kwargs['AccountScope'] == 'LINKED'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'recommendation, service, term, payment_option',
    [
        (
            COH_RDS_RI_THREE_YEAR,
            'Amazon Relational Database Service',
            'THREE_YEARS',
            'ALL_UPFRONT',
        ),
        (
            COH_DYNAMODB_RC_THREE_YEAR,
            'Amazon DynamoDB Service',
            'THREE_YEARS',
            'HEAVY_UTILIZATION',
        ),
        (COH_EC2_RI_ONE_YEAR, 'Amazon Elastic Compute Cloud - Compute', 'ONE_YEAR', 'ALL_UPFRONT'),
    ],
)
async def test_reserved_instances_coh_terms_reach_cost_explorer(
    mock_context, mock_ce_client, recommendation, service, term, payment_option
):
    """A reservation recommendation of either COH term is looked up in Cost Explorer."""
    result = await get_reserved_instances_recommendation(
        mock_context, recommendation, mock_ce_client
    )

    assert 'error' not in result
    call_kwargs = mock_ce_client.get_reservation_purchase_recommendation.call_args[1]
    assert call_kwargs['Service'] == service
    assert call_kwargs['TermInYears'] == term
    assert call_kwargs['PaymentOption'] == payment_option


def test_term_map_accepts_legacy_three_year_spelling():
    """The singular 'ThreeYear' spelling still maps, in case a payload uses it."""
    assert TERM_MAP['ThreeYear'] == 'THREE_YEARS'


@pytest.mark.parametrize(
    'coh_map, coh_enum, ce_enum',
    [
        (TERM_MAP, 'Term', 'TermInYears'),
        (PAYMENT_OPTION_MAP, 'PaymentOption', 'PaymentOption'),
    ],
)
def test_coh_commitment_enums_map_to_cost_explorer_values(coh_map, coh_enum, ce_enum):
    """Every COH term and payment option value maps to a value Cost Explorer accepts."""
    coh = botocore.session.get_session().get_service_model('cost-optimization-hub')

    assert set(coh.shape_for(coh_enum).enum) - set(coh_map) == set()
    assert set(coh_map.values()) - set(_ce_model().shape_for(ce_enum).enum) == set()


def test_account_scope_map_values_are_cost_explorer_values():
    """The account scope map only produces values Cost Explorer accepts."""
    assert set(ACCOUNT_SCOPE_MAP.values()) <= set(_ce_model().shape_for('AccountScope').enum)


@pytest.mark.asyncio
@patch(
    'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
)
async def test_process_recommendation_warns_when_purchase_details_are_missing(
    mock_create_aws_client, mock_context, mock_ce_client
):
    """A skipped Cost Explorer lookup leads the response with a warning, not a buried error."""
    mock_create_aws_client.return_value = mock_ce_client
    recommendation = {
        'actionType': 'PurchaseSavingsPlans',
        'recommendedResourceDetails': {
            'computeSavingsPlans': {'configuration': {'term': 'TenYears'}}
        },
    }

    result = await process_recommendation(mock_context, recommendation)

    assert list(result)[0] == 'warning'
    assert 'has no Cost Explorer purchase recommendation;' in result['warning']
    assert 'additional_details.error says why' in result['warning']
    assert 'base_recommendation' in result
    assert 'Missing required parameters' in result['additional_details']['error']
    mock_ce_client.get_savings_plans_purchase_recommendation.assert_not_called()


@pytest.mark.asyncio
@patch(
    'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
)
async def test_process_recommendation_three_year_has_no_warning(
    mock_create_aws_client, mock_context, mock_ce_client
):
    """A three-year recommendation returns Cost Explorer purchase details and no warning."""
    mock_create_aws_client.return_value = mock_ce_client

    result = await process_recommendation(mock_context, COH_SP_THREE_YEAR)

    assert 'warning' not in result
    assert 'SavingsPlansPurchaseRecommendationSummary' in result['additional_details']


@pytest.mark.asyncio
@patch(
    'awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools.create_aws_client'
)
async def test_process_recommendation_warns_when_compute_optimizer_fails(
    mock_create_aws_client, mock_context
):
    """Missing Compute Optimizer details also lead the response with a warning."""
    recommendation = {'actionType': 'Rightsize', 'currentResourceType': 'Ec2Instance'}

    result = await process_recommendation(mock_context, recommendation)

    assert list(result)[0] == 'warning'
    assert 'has no Compute Optimizer details;' in result['warning']
    assert 'No resource ARN found' in result['additional_details']['error']
    mock_create_aws_client.assert_not_called()


@pytest.mark.asyncio
async def test_process_recommendation_warns_on_unsupported_resource_type(mock_context):
    """A skipped Compute Optimizer lookup (unsupported resource type) also leads with a warning."""
    recommendation = {
        'actionType': 'Rightsize',
        'currentResourceType': 'SomeNewResource',
        'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc',
    }

    with patch.object(recommendation_details_tools, 'create_aws_client', return_value=MagicMock()):
        result = await process_recommendation(mock_context, recommendation)

    assert list(result)[0] == 'warning'
    assert 'has no Compute Optimizer details;' in result['warning']
    assert result['additional_details'] == {'error': 'Unsupported resource type: SomeNewResource'}


@pytest.mark.asyncio
async def test_process_recommendation_empty_lookup_has_no_warning(mock_context):
    """A lookup that runs but finds nothing returns its empty result and no warning."""
    client = MagicMock()
    # Compute Optimizer's shape for an ARN it has no recommendation for.
    client.get_ec2_instance_recommendations.return_value = {
        'instanceRecommendations': [],
        'errors': [],
    }
    recommendation = {
        'actionType': 'Rightsize',
        'currentResourceType': 'Ec2Instance',
        'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc',
    }

    with patch.object(recommendation_details_tools, 'create_aws_client', return_value=client):
        result = await process_recommendation(mock_context, recommendation)

    assert 'warning' not in result
    assert result['additional_details'] == {'instanceRecommendations': [], 'errors': []}


@pytest.mark.asyncio
async def test_rec_details_description_documents_lookup_warning():
    """The served description says missing details lead with a warning."""
    tools = {t.name: t for t in await recommendation_details_server.list_tools()}
    description = tools['rec-details'].description or ''

    assert 'lookup fails or is skipped' in description
    assert 'the response leads with a warning' in description
    assert 'base_recommendation is still valid' in description
    assert 'returns empty results and no warning' in description
    assert 'details are unavailable' not in description


_RESPONSE_METADATA = {'RequestId': 'req-1', 'HTTPStatusCode': 200, 'HTTPHeaders': {}}


@pytest.mark.asyncio
class TestResponseMetadataIsDropped:
    """The detail helpers return the API payload without botocore's ResponseMetadata."""

    async def test_reserved_instances_recommendation(self, mock_context):
        """The Cost Explorer RI response loses ResponseMetadata and keeps its payload."""
        ce_client = MagicMock()
        ce_client.get_reservation_purchase_recommendation.return_value = {
            'Recommendations': [],
            'ResponseMetadata': dict(_RESPONSE_METADATA),
        }
        recommendation = {
            'recommendedResourceDetails': {
                'ec2ReservedInstances': {
                    'configuration': {'term': 'OneYear', 'paymentOption': 'AllUpfront'}
                }
            },
        }

        result = await get_reserved_instances_recommendation(
            mock_context, recommendation, ce_client
        )

        assert result == {'Recommendations': []}

    @pytest.mark.parametrize(
        'action_type, resource_type, method, payload_key',
        [
            ('Stop', 'Ec2Instance', 'get_idle_recommendations', 'idleRecommendations'),
            (
                'Rightsize',
                'EcsService',
                'get_ecs_service_recommendations',
                'ecsServiceRecommendations',
            ),
            (
                'Rightsize',
                'LambdaFunction',
                'get_lambda_function_recommendations',
                'lambdaFunctionRecommendations',
            ),
            ('Rightsize', 'EbsVolume', 'get_ebs_volume_recommendations', 'volumeRecommendations'),
            (
                'Rightsize',
                'Ec2Instance',
                'get_ec2_instance_recommendations',
                'instanceRecommendations',
            ),
            (
                'Rightsize',
                'Ec2AutoScalingGroup',
                'get_auto_scaling_group_recommendations',
                'autoScalingGroupRecommendations',
            ),
            (
                'Rightsize',
                'RdsDbInstance',
                'get_rds_database_recommendations',
                'rdsDBRecommendations',
            ),
        ],
    )
    async def test_compute_optimizer_data(
        self, mock_context, action_type, resource_type, method, payload_key
    ):
        """Every Compute Optimizer branch drops ResponseMetadata and keeps its payload."""
        client = MagicMock()
        getattr(client, method).return_value = {
            payload_key: [],
            'ResponseMetadata': dict(_RESPONSE_METADATA),
        }
        recommendation = {
            'actionType': action_type,
            'currentResourceType': resource_type,
            'resourceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abc',
            'region': 'us-east-1',
        }

        with patch.object(recommendation_details_tools, 'create_aws_client', return_value=client):
            result = await get_compute_optimizer_data(mock_context, recommendation)

        getattr(client, method).assert_called_once()
        assert result == {payload_key: []}
