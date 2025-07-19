"""Integration tests for the Compute Optimizer tools."""

import pytest
from botocore.exceptions import ClientError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_auto_scaling_group_recommendations(
    tool_function_factory,
):
    """Test the compute_optimizer_get_auto_scaling_group_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_asg_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert 'autoScalingGroupRecommendations' in result
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['autoScalingGroupRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_ebs_volume_recommendations(tool_function_factory):
    """Test the compute_optimizer_get_ebs_volume_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_ebs_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert 'volumeRecommendations' in result
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['volumeRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_ec2_instance_recommendations(tool_function_factory):
    """Test the compute_optimizer_get_ec2_instance_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_ec2_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert 'instanceRecommendations' in result
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['instanceRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_ecs_service_recommendations(tool_function_factory):
    """Test the compute_optimizer_get_ecs_service_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_ecs_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert 'ecsServiceRecommendations' in result
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['ecsServiceRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_rds_database_recommendations(tool_function_factory):
    """Test the compute_optimizer_get_rds_database_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_rds_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert (
            'rdsDBRecommendations' in result
        )  # Note: API returns rdsDBRecommendations, not rdsDatabaseRecommendations
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['rdsDBRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_lambda_function_recommendations(
    tool_function_factory,
):
    """Test the compute_optimizer_get_lambda_function_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_lambda_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert 'lambdaFunctionRecommendations' in result
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['lambdaFunctionRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_idle_recommendations(tool_function_factory):
    """Test the compute_optimizer_get_idle_recommendations tool."""
    # Create the tool function
    tool_function = tool_function_factory('co_get_idle_recs')

    try:
        # Call the tool function with minimal parameters
        result = await tool_function({})

        # Verify the result structure
        assert (
            'idleRecommendations' in result
        )  # Note: API returns idleRecommendations, not idleResourceRecommendations
        # The recommendations list might be empty if there are no recommendations
        assert isinstance(result['idleRecommendations'], list)

    except ClientError as e:
        # If we get an access denied error, we'll skip the test
        if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
            pytest.skip(f"AWS credentials don't have permission: {str(e)}")
        else:
            raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compute_optimizer_get_effective_recommendation_preferences(
    tool_function_factory,
):
    """Test the compute_optimizer_get_effective_recommendation_preferences tool."""
    # Skip this test as it requires a valid resource ARN which we don't have in the test environment
    pytest.skip('This test requires a valid resource ARN to function properly')
