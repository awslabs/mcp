"""Integration tests for the Cost Explorer tools."""

import pytest
from botocore.exceptions import ClientError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_explorer_get_cost_and_usage(tool_function_factory):
    """Test the cost_explorer_get_cost_and_usage tool."""
    # Create the tool function
    tool_function = tool_function_factory('cost_explorer_get_cost_and_usage')

    # Call the tool function with real parameters
    # Using a small date range to minimize data transfer
    params = {
        'timePeriod': {'Start': '2025-01-01', 'End': '2025-01-02'},
        'granularity': 'DAILY',
        'metrics': ['BlendedCost'],
    }

    try:
        # Execute the function
        result = await tool_function(params)

        # Verify the result structure
        assert 'ResultsByTime' in result
        assert isinstance(result['ResultsByTime'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_explorer_get_reservation_purchase_recommendation(tool_function_factory):
    """Test the cost_explorer_get_reservation_purchase_recommendation tool."""
    # Create the tool function
    tool_function = tool_function_factory('cost_explorer_get_reservation_purchase_recommendation')

    # Call the tool function with real parameters
    params = {
        'service': 'Amazon Redshift',
        'lookbackPeriodInDays': 'SEVEN_DAYS',
    }

    try:
        # Execute the function
        result = await tool_function(params)

        # Verify the result structure
        assert 'Recommendations' in result
        assert isinstance(result['Recommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_explorer_get_savings_plans_purchase_recommendation(
    tool_function_factory,
):
    """Test the cost_explorer_get_savings_plans_purchase_recommendation tool."""
    # Create the tool function
    tool_function = tool_function_factory(
        'cost_explorer_get_savings_plans_purchase_recommendation'
    )

    # Call the tool function with real parameters
    params = {
        'savingsPlansType': 'COMPUTE_SP',
        'termInYears': 'ONE_YEAR',
        'paymentOption': 'NO_UPFRONT',
        'lookbackPeriodInDays': 'SEVEN_DAYS',
    }

    try:
        # Execute the function
        result = await tool_function(params)

        # Verify the result structure
        assert 'SavingsPlansPurchaseRecommendation' in result

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise
