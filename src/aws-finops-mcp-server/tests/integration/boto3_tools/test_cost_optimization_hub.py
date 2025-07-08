"""Integration tests for the Cost Optimization Hub tools."""

import pytest
from botocore.exceptions import ClientError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_optimization_hub_get_recommendation(registry, tool_function_factory):
    """Test the cost_optimization_hub_get_recommendation tool."""
    # Create the tool functions
    tool_function = tool_function_factory('coh_get_rec')
    list_tool_function = tool_function_factory('coh_list_recs')

    try:
        # First, list recommendations to get a valid ID
        list_result = await list_tool_function({})

        # Check if we have any recommendations
        if 'recommendations' in list_result and len(list_result['recommendations']) > 0:
            # Get the first recommendation ID
            recommendation_id = list_result['recommendations'][0]['id']

            # Call the get_recommendation tool with the ID
            result = await tool_function({'recommendationId': recommendation_id})

            # Verify the result structure
            assert 'recommendation' in result
            assert 'id' in result['recommendation']
            assert result['recommendation']['id'] == recommendation_id
        else:
            pytest.skip('No recommendations available to test with')

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_optimization_hub_list_recommendations(registry, tool_function_factory):
    """Test the cost_optimization_hub_list_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('coh_list_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Check if there's an error about not being enrolled
        if 'error' in result and 'not enrolled for recommendations' in result['error']:
            pytest.skip('AWS account is not enrolled for Cost Optimization Hub recommendations')

        # Verify the result structure
        assert 'recommendations' in result
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['recommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_optimization_hub_list_recommendation_summaries(
    registry, tool_function_factory
):
    """Test the cost_optimization_hub_list_recommendation_summaries tool."""
    # Create the tool function
    tool_function = tool_function_factory('coh_list_rec_summaries')

    try:
        # Call the tool function with required parameters
        result = await tool_function({'groupBy': 'ResourceType'})

        # Check if there's an error about not being enrolled
        if 'error' in result and 'not enrolled for recommendations' in result['error']:
            pytest.skip('AWS account is not enrolled for Cost Optimization Hub recommendations')
            pytest.skip('AWS account is not enrolled for Cost Optimization Hub recommendations')
            pytest.skip('AWS account is not enrolled for Cost Optimization Hub recommendations')

        # Verify the result structure
        assert 'recommendationSummaries' in result
        # The summaries list might be empty if there are no recommendations
        assert isinstance(result['recommendationSummaries'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise
