# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for specific edge cases in resources.py to improve coverage."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from awslabs.cdk_mcp_server.core.resources import (
    get_solutions_construct_pattern_resource,
    get_genai_cdk_construct_section_resource,
    get_genai_cdk_construct_nested_section_resource,
    get_available_sections_resource,
    get_genai_cdk_construct_resource,
    get_genai_cdk_overview_resource,
)


@pytest.mark.asyncio
async def test_get_solutions_construct_pattern_resource_error():
    """Test error handling in get_solutions_construct_pattern_resource."""
    # Mock error response from get_pattern_raw
    mock_error = {'error': 'Pattern not found'}
    available_patterns = ['pattern1', 'pattern2']

    with patch('awslabs.cdk_mcp_server.core.resources.get_pattern_raw', 
              return_value=mock_error) as mock_get_pattern, \
         patch('awslabs.cdk_mcp_server.data.solutions_constructs_parser.fetch_pattern_list',
              return_value=available_patterns) as mock_fetch_list:
        
        result = await get_solutions_construct_pattern_resource('invalid-pattern')
        
        # Verify error message is constructed correctly
        assert "Pattern 'invalid-pattern' not found" in result
        assert "pattern1" in result
        assert "pattern2" in result
        
        # Verify correct functions were called
        mock_get_pattern.assert_called_once_with('invalid-pattern')
        mock_fetch_list.assert_called_once()


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_resource_knowledge_bases_with_section():
    """Test knowledge base special case handling with section in get_genai_cdk_construct_resource."""
    # Mock for section result
    section_result = {
        'content': 'Test KB section content',
        'status': 'success'
    }
    
    # Mock for readme result (should not be returned if section is found)
    readme_result = {
        'content': 'Test README content',
        'status': 'success'
    }
    
    with patch('awslabs.cdk_mcp_server.core.resources.get_section', 
              return_value=section_result) as mock_get_section, \
         patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme',
              return_value=readme_result) as mock_get_readme:
        
        result = await get_genai_cdk_construct_resource('bedrock', 'Amazon Bedrock Knowledge BasesVectorKB')
        
        # Should return section content, not readme content
        assert result == 'Test KB section content'
        
        # Verify get_section was called with correct parameters
        mock_get_section.assert_called_with('bedrock', 'knowledge-bases', 'VectorKB')
        
        # get_readme should not have been called at all
        mock_get_readme.assert_not_called()


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_resource_knowledge_bases_without_section():
    """Test knowledge base special case handling without section in get_genai_cdk_construct_resource."""
    # For Knowledge Bases without section, we directly get the README without calling get_section
    readme_result = {
        'content': 'Test knowledge-bases README content',
        'status': 'success'
    }
    
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme',
              return_value=readme_result) as mock_get_readme:
        
        result = await get_genai_cdk_construct_resource('bedrock', 'Amazon Bedrock Knowledge Bases')
        
        # Should directly use readme content
        assert result == 'Test knowledge-bases README content'
        
        # get_readme should have been called with knowledge-bases
        mock_get_readme.assert_called_once_with('bedrock', 'knowledge-bases')


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_resource_agent_normalization():
    """Test agent normalization in get_genai_cdk_construct_resource."""
    # Mock for readme result
    readme_success = {
        'content': 'Test agent README content', 
        'status': 'success'
    }
    
    # First attempt fails, second succeeds
    readme_error = {
        'error': 'Not found',
        'status': 'error'
    }
    
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', 
              side_effect=[readme_error, readme_success]) as mock_get_readme:
        
        result = await get_genai_cdk_construct_resource('bedrock', 'Agent')
        
        # Should return successful README content
        assert result == 'Test agent README content'
        
        # Verify first call was with 'bedrock'
        mock_get_readme.assert_any_call('bedrock')
        
        # Verify second call used 'agents' (plural)
        mock_get_readme.assert_any_call('bedrock', 'agents')


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_resource_knowledge_base_keyword():
    """Test knowledge base keyword detection in get_genai_cdk_construct_resource."""
    # Mock for readme result
    readme_success = {
        'content': 'Test knowledge-bases README content', 
        'status': 'success'
    }
    
    # First attempt fails
    readme_error = {
        'error': 'Not found',
        'status': 'error'
    }
    
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', 
              side_effect=[readme_error, readme_success]) as mock_get_readme:
        
        result = await get_genai_cdk_construct_resource('bedrock', 'KnowledgeBase')
        
        # Should return successful README content
        assert result == 'Test knowledge-bases README content'
        
        # Verify first call was with 'bedrock'
        mock_get_readme.assert_any_call('bedrock')
        
        # Verify second call was with 'knowledge-bases'
        mock_get_readme.assert_any_call('bedrock', 'knowledge-bases')


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_resource_all_errors():
    """Test complete error path in get_genai_cdk_construct_resource."""
    # Mock all readme attempts to fail
    readme_error = {
        'error': 'Not found',
        'status': 'error'
    }
    
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', 
              return_value=readme_error) as mock_get_readme:
        
        result = await get_genai_cdk_construct_resource('bedrock', 'unknown')
        
        # Should return error message
        assert "Error fetching construct from GitHub" in result
        assert "Not found" in result


@pytest.mark.asyncio
async def test_get_genai_cdk_overview_resource_error():
    """Test error handling in get_genai_cdk_overview_resource."""
    # Mock readme to fail
    readme_error = {
        'error': 'Failed to fetch',
        'status': 'error'
    }
    
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', 
              return_value=readme_error) as mock_get_readme:
        
        result = await get_genai_cdk_overview_resource('unknown-type')
        
        # Should return error message
        assert "Error fetching overview from GitHub" in result
        assert "Failed to fetch" in result
        
        # Verify correct call was made
        mock_get_readme.assert_called_once_with('unknown-type')


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_section_resource_not_found():
    """Test not found error in get_genai_cdk_construct_section_resource."""
    # Mock section to return not_found
    section_not_found = {
        'status': 'not_found',
    }
    
    with patch('awslabs.cdk_mcp_server.core.resources.get_section', 
              return_value=section_not_found) as mock_get_section:
        
        result = await get_genai_cdk_construct_section_resource('bedrock', 'agents', 'nonexistent')
        
        # Should return error message
        assert "Error:" in result
        assert "not found" in result
        assert "bedrock/agents" in result
        
        # Verify correct call was made
        mock_get_section.assert_called_once_with('bedrock', 'agents', 'nonexistent')


@pytest.mark.asyncio
async def test_get_genai_cdk_construct_nested_section_resource_all_errors():
    """Test complete error path in get_genai_cdk_construct_nested_section_resource."""
    # Mock both section attempts to return not_found
    section_not_found = {
        'status': 'not_found',
    }
    
    with patch('awslabs.cdk_mcp_server.core.resources.get_section', 
              return_value=section_not_found) as mock_get_section:
        
        result = await get_genai_cdk_construct_nested_section_resource(
            'bedrock', 'knowledgebases', 'vector', 'unknown'
        )
        
        # Should return error message
        assert "Error:" in result
        assert "vector/unknown" in result
        assert "not found" in result
        
        # Verify both formats were tried
        assert mock_get_section.call_count == 2
        mock_get_section.assert_any_call('bedrock', 'knowledgebases', 'vector/unknown')
        mock_get_section.assert_any_call('bedrock', 'knowledgebases', 'vector unknown')


@pytest.mark.asyncio
async def test_get_available_sections_resource_error():
    """Test error handling in get_available_sections_resource."""
    # Mock list_sections to return error
    list_error = {
        'error': 'Failed to fetch sections',
        'status': 'error'
    }
    
    with patch('awslabs.cdk_mcp_server.core.resources.list_sections', 
              return_value=list_error) as mock_list_sections:
        
        result = await get_available_sections_resource('bedrock', 'unknown')
        
        # Should return error message
        assert "Error fetching sections from GitHub" in result
        assert "Failed to fetch sections" in result
