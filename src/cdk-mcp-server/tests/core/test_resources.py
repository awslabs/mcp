import pytest
from awslabs.cdk_mcp_server.core.resources import (
    RulePack,
    get_all_cdk_nag_rules,
    get_available_sections_resource,
    get_cdk_nag_errors,
    get_cdk_nag_warnings,
    get_genai_cdk_construct_nested_section_resource,
    get_genai_cdk_construct_resource,
    get_genai_cdk_construct_section_resource,
    get_genai_cdk_overview_resource,
    get_lambda_powertools_guidance,
    get_lambda_powertools_index,
    get_solutions_construct_pattern_resource,
)
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_all_cdk_nag_rules():
    """Test getting all CDK Nag rules for a rule pack."""
    with patch('awslabs.cdk_mcp_server.core.resources.get_rule_pack') as mock_get_rule_pack:
        mock_get_rule_pack.return_value = 'Test rule pack content'

        # Test with valid rule pack
        result = await get_all_cdk_nag_rules(RulePack.AWS_SOLUTIONS.value)
        assert result == 'Test rule pack content'
        mock_get_rule_pack.assert_called_once_with(RulePack.AWS_SOLUTIONS)

        # Test with invalid rule pack
        result = await get_all_cdk_nag_rules('Invalid Pack')
        assert 'Invalid rule pack' in result
        assert RulePack.AWS_SOLUTIONS.value in result


@pytest.mark.asyncio
async def test_get_cdk_nag_warnings():
    """Test getting CDK Nag warnings for a rule pack."""
    with patch('awslabs.cdk_mcp_server.core.resources.get_warnings') as mock_get_warnings:
        mock_get_warnings.return_value = 'Test warnings content'

        # Test with valid rule pack
        result = await get_cdk_nag_warnings(RulePack.AWS_SOLUTIONS.value)
        assert result == 'Test warnings content'
        mock_get_warnings.assert_called_once_with(RulePack.AWS_SOLUTIONS)

        # Test with invalid rule pack
        result = await get_cdk_nag_warnings('Invalid Pack')
        assert 'Invalid rule pack' in result
        assert RulePack.AWS_SOLUTIONS.value in result


@pytest.mark.asyncio
async def test_get_cdk_nag_errors():
    """Test getting CDK Nag errors for a rule pack."""
    with patch('awslabs.cdk_mcp_server.core.resources.get_errors') as mock_get_errors:
        mock_get_errors.return_value = 'Test errors content'

        # Test with valid rule pack
        result = await get_cdk_nag_errors(RulePack.AWS_SOLUTIONS.value)
        assert result == 'Test errors content'
        mock_get_errors.assert_called_once_with(RulePack.AWS_SOLUTIONS)

        # Test with invalid rule pack
        result = await get_cdk_nag_errors('Invalid Pack')
        assert 'Invalid rule pack' in result
        assert RulePack.AWS_SOLUTIONS.value in result


@pytest.mark.asyncio
async def test_get_lambda_powertools_guidance():
    """Test getting Lambda Powertools guidance."""
    with patch(
        'awslabs.cdk_mcp_server.core.resources.get_lambda_powertools_section'
    ) as mock_get_section:
        mock_get_section.return_value = 'Test guidance content'

        # Test with specific topic
        result = await get_lambda_powertools_guidance('logging')
        assert result == 'Test guidance content'
        mock_get_section.assert_called_once_with('logging')

        # Test with empty topic
        result = await get_lambda_powertools_guidance()
        assert result == 'Test guidance content'
        mock_get_section.assert_called_with('')


@pytest.mark.asyncio
async def test_get_lambda_powertools_index():
    """Test getting Lambda Powertools index."""
    with patch(
        'awslabs.cdk_mcp_server.core.resources.get_lambda_powertools_section'
    ) as mock_get_section:
        mock_get_section.return_value = 'Test index content'

        result = await get_lambda_powertools_index()
        assert result == 'Test index content'
        mock_get_section.assert_called_once_with('index')


@pytest.mark.asyncio
async def test_get_solutions_construct_pattern_resource():
    """Test getting Solutions Construct pattern resource."""
    with patch('awslabs.cdk_mcp_server.core.resources.get_pattern_raw') as mock_get_pattern:
        # Test with valid pattern
        mock_get_pattern.return_value = {'content': 'Test pattern content'}
        result = await get_solutions_construct_pattern_resource('aws-lambda-dynamodb')
        assert result == 'Test pattern content'
        mock_get_pattern.assert_called_once_with('aws-lambda-dynamodb')

        # Test with invalid pattern
        mock_get_pattern.return_value = {'error': 'Pattern not found'}
        with patch('awslabs.cdk_mcp_server.data.solutions_constructs_parser') as mock_fetch_list:
            mock_fetch_list.return_value = ['pattern1', 'pattern2']
            result = await get_solutions_construct_pattern_resource('invalid-pattern')
            assert "Pattern 'invalid-pattern' not found" in result


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_section_resource():
    """Test getting GenAI CDK construct section resource."""
    # Create a mock result
    mock_result = {'content': 'Test section content', 'status': 'success'}

    # Import the module directly where the function is defined
    with patch(
        'awslabs.cdk_mcp_server.core.resources.get_section', return_value=mock_result
    ) as mock_get_section:
        # Call the function we're testing
        result = await get_genai_cdk_construct_section_resource('bedrock', 'agent', 'actiongroups')

        # Verify the result matches the mocked content
        assert result == 'Test section content'

        # Verify correct parameters were passed
        mock_get_section.assert_called_once_with('bedrock', 'agent', 'actiongroups')


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_nested_section_resource():
    """Test getting GenAI CDK construct nested section resource."""
    # Create mock results for the first and second attempts
    mock_result_error = {'error': 'Section not found', 'status': 'not_found'}

    mock_result_success = {'content': 'Test nested section content', 'status': 'success'}

    # Use MagicMock to create a side_effect function for get_section
    mock_get_section = AsyncMock()
    # First call returns error, second call returns success
    mock_get_section.side_effect = [mock_result_error, mock_result_success]

    # Patch at the resources module level
    with patch('awslabs.cdk_mcp_server.core.resources.get_section', mock_get_section):
        # Call the function we're testing
        result = await get_genai_cdk_construct_nested_section_resource(
            'bedrock', 'knowledgebases', 'vector', 'opensearch'
        )

        # Verify the result matches the mocked content
        assert result == 'Test nested section content'

        # Verify both parameters were tried
        assert mock_get_section.call_count == 2
        mock_get_section.assert_any_call('bedrock', 'knowledgebases', 'vector/opensearch')
        mock_get_section.assert_any_call('bedrock', 'knowledgebases', 'vector opensearch')


@pytest.mark.asyncio
async def test_get_available_sections_resource():
    """Test getting available sections resource."""
    # Create mock result data
    mock_sections_result = {
        'sections': ['section1', 'section2'],
        'path': 'bedrock/agents',  # Note: implementation converts agent -> agents
        'status': 'success',
    }

    # Apply the mock at the local module level
    with patch(
        'awslabs.cdk_mcp_server.core.resources.list_sections', return_value=mock_sections_result
    ) as mock_list_sections:
        # Call the function
        result = await get_available_sections_resource('bedrock', 'agent')

        # Verify "Agents" appears in the result (capitalized plural form)
        assert 'Available Sections for Agents in Bedrock' in result
        assert 'section1' in result
        assert 'section2' in result

        # Test with no sections
        mock_list_sections.return_value = {
            'sections': [],
            'path': 'bedrock/agents',
            'status': 'success',
        }
        result = await get_available_sections_resource('bedrock', 'agent')
        assert 'No sections found' in result


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_resource():
    """Test getting GenAI CDK construct resource."""
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme') as mock_fetch_readme:
        mock_fetch_readme.return_value = {'content': 'Test construct content', 'status': 'success'}

        result = await get_genai_cdk_construct_resource('bedrock', 'Agent')
        assert result == 'Test construct content'
        mock_fetch_readme.assert_called_once()


@pytest.mark.asyncio
async def test_get_genai_cdk_overview_resource():
    """Test getting GenAI CDK overview resource."""
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme') as mock_fetch_readme:
        mock_fetch_readme.return_value = {'content': 'Test overview content', 'status': 'success'}

        result = await get_genai_cdk_overview_resource('bedrock')
        assert result == 'Test overview content'
        mock_fetch_readme.assert_called_once_with('bedrock')
