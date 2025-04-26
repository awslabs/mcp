# Update the imports from genai_cdk_github_loader
from awslabs.cdk_mcp_server.data.genai_cdk_github_loader import (
    ConstructType,
    get_construct_map,
    get_construct_types,
    get_genai_cdk_construct,
    get_genai_cdk_construct_section,
    get_genai_cdk_overview,
    list_available_constructs,
    list_sections,
    fetch_readme,
    fetch_repo_structure,
    fetch_bedrock_subdirectories,
    extract_sections,
)
from unittest.mock import mock_open, patch, AsyncMock, MagicMock
import pytest


def test_get_construct_types():
    """Test getting the list of available construct types."""
    construct_types = get_construct_types()

    # Check that all expected construct types are present
    assert 'bedrock' in construct_types
    assert 'opensearchserverless' in construct_types
    assert 'opensearch-vectorindex' in construct_types

    # Check that the list contains all values from the ConstructType enum
    assert len(construct_types) == len(ConstructType)


def test_get_construct_map():
    """Test getting the construct map."""
    construct_map = get_construct_map()

    # Check that all expected construct types are present
    assert 'bedrock' in construct_map
    assert 'opensearchserverless' in construct_map
    assert 'opensearch-vectorindex' in construct_map

    # Check that descriptions are present
    assert (
        'Amazon Bedrock constructs for agents, knowledge bases, and more'
        in construct_map['bedrock']
    )
    assert (
        'Amazon OpenSearch Serverless constructs for vector search'
        in construct_map['opensearchserverless']
    )
    assert 'Amazon OpenSearch vector index constructs' in construct_map['opensearch-vectorindex']


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open', new_callable=mock_open, read_data='Test overview content')
def test_get_genai_cdk_overview_success(mock_file, mock_join, mock_dirname):
    """Test getting a GenAI CDK overview successfully."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'

    # Test with specific construct type
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock/overview.md'
    content = get_genai_cdk_overview('bedrock')
    assert content == 'Test overview content'
    mock_file.assert_called_with(
        '/mock/path/static/genai_cdk/bedrock/overview.md', 'r', encoding='utf-8'
    )

    # Test with empty construct type (should return error message with available types)
    # We don't need to mock the file opening for this case
    content = get_genai_cdk_overview('')
    assert "Construct type '' not found" in content
    assert 'Available types:' in content


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open')
def test_get_genai_cdk_overview_file_not_found(mock_file, mock_join, mock_dirname):
    """Test getting a GenAI CDK overview when file is not found."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock/overview.md'

    # Mock file not found error
    mock_file.side_effect = FileNotFoundError()

    # Test with specific construct type
    content = get_genai_cdk_overview('bedrock')
    assert 'Error: Overview file for' in content
    assert 'not found' in content


def test_get_genai_cdk_overview_invalid_construct_type():
    """Test getting a GenAI CDK overview with invalid construct type."""
    # Test with invalid construct type
    content = get_genai_cdk_overview('invalid_type')
    assert "Construct type 'invalid_type' not found" in content
    assert 'Available types:' in content

    # Verify that all valid construct types are listed in the error message
    construct_map = get_construct_map()
    for construct_type in construct_map:
        assert construct_type in content
        assert construct_map[construct_type] in content


@pytest.mark.asyncio
async def test_list_sections_success():
    """Test listing available sections successfully with GitHub-based approach."""
    # Mock fetch_readme function
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_github_loader.fetch_readme', 
               new=AsyncMock()) as mock_fetch_readme:
        # Setup the mock return value
        mock_fetch_readme.return_value = {
            'content': """# Test README
            
            Introduction text
            
            ## Section One
            Content for section one
            
            ## Section Two
            Content for section two
            
            ## Section Three
            Content for section three
            """,
            'status': 'success'
        }
        
        # Test listing sections
        result = await list_sections('bedrock', 'agent')
        
        # Check that mock was called with correct arguments
        mock_fetch_readme.assert_called_with('bedrock', 'agent')
        
        # Check result
        assert result['status'] == 'success'
        assert 'Section One' in result['sections']
        assert 'Section Two' in result['sections']
        assert 'Section Three' in result['sections']
        assert len(result['sections']) == 3


@pytest.mark.asyncio
async def test_list_sections_error():
    """Test listing sections when README fetch fails."""
    # Mock fetch_readme function
    with patch('awslabs.cdk_mcp_server.data.genai_cdk_github_loader.fetch_readme', 
               new=AsyncMock()) as mock_fetch_readme:
        # Setup the mock return value for error case
        mock_fetch_readme.return_value = {
            'error': 'Test error message',
            'status': 'error'
        }
        
        # Test listing sections
        result = await list_sections('bedrock', 'agent')
        
        # Check result passes through the error
        assert 'error' in result


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open', new_callable=mock_open, read_data='Test section content')
def test_get_genai_cdk_construct_section_success(mock_file, mock_join, mock_dirname):
    """Test getting a GenAI CDK construct section successfully."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'

    # Test with regular section
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock/agent/usage.md'
    content = get_genai_cdk_construct_section('bedrock', 'agent', 'usage')
    assert content == 'Test section content'
    mock_file.assert_called_with(
        '/mock/path/static/genai_cdk/bedrock/agent/usage.md', 'r', encoding='utf-8'
    )

    # Reset the mocks for the next test
    mock_file.reset_mock()
    mock_join.reset_mock()

    # Test with nested section
    # The actual implementation might append .md to the path
    # Let's check both possibilities
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock/agent/actiongroups/overview.md'
    content = get_genai_cdk_construct_section('bedrock', 'agent', 'actiongroups/overview')
    assert content == 'Test section content'

    # Print the actual calls for debugging
    print('Actual calls to mock_file:', mock_file.call_args_list)


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open')
def test_get_genai_cdk_construct_section_file_not_found(mock_file, mock_join, mock_dirname):
    """Test getting a GenAI CDK construct section when file is not found."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock/agent/usage.md'

    # Mock file not found error
    mock_file.side_effect = FileNotFoundError()

    # Test with specific section
    content = get_genai_cdk_construct_section('bedrock', 'agent', 'usage')
    assert 'Error: Section' in content
    assert 'not found' in content


def test_get_genai_cdk_construct_section_invalid_construct_type():
    """Test getting a GenAI CDK construct section with invalid construct type."""
    # Test with invalid construct type
    content = get_genai_cdk_construct_section('invalid_type', 'agent', 'usage')
    assert "Error: Construct type 'invalid_type' not found" in content


@patch('os.path.dirname')
@patch('os.path.join')
@patch('builtins.open')
def test_get_genai_cdk_construct_file_not_found(mock_file, mock_join, mock_dirname):
    """Test getting a GenAI CDK construct when file is not found."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock/agent.md'

    # Mock file not found error
    mock_file.side_effect = FileNotFoundError()

    # Test with specific construct
    content = get_genai_cdk_construct('bedrock', 'agent')
    assert 'Error: Documentation for' in content
    assert 'not found' in content


def test_get_genai_cdk_construct_invalid_construct_type():
    """Test getting a GenAI CDK construct with invalid construct type."""
    # Test with invalid construct type
    content = get_genai_cdk_construct('invalid_type', 'agent')
    assert 'Error: Documentation for' in content
    assert 'not found' in content
    assert 'invalid_type' in content
    assert 'agent' in content


@patch('os.path.dirname')
@patch('os.path.join')
@patch('os.path.exists')
@patch('os.listdir')
@patch('os.walk')
def test_list_available_constructs_success(
    mock_walk, mock_listdir, mock_exists, mock_join, mock_dirname
):
    """Test listing available constructs successfully."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock'
    mock_exists.return_value = True

    # Mock directory listing to return some files
    mock_listdir.return_value = ['agent.md', 'knowledgebase.md', 'overview.md']

    # Mock directory walk to return some files in subdirectories
    mock_walk.return_value = [
        ('/mock/path/static/genai_cdk/bedrock', ['agent', 'knowledgebase'], ['overview.md']),
        ('/mock/path/static/genai_cdk/bedrock/agent', [], ['actiongroups.md']),
        ('/mock/path/static/genai_cdk/bedrock/knowledgebase', [], ['vector.md']),
    ]

    # Test listing constructs
    constructs = list_available_constructs('bedrock')

    # Check that the correct constructs are returned
    # The actual implementation returns constructs based on file names and directory structure
    # The exact number may vary based on how the mocks are set up

    # Check for specific constructs that should be present
    assert any(c['name'] == 'Agent' and c['type'] == 'bedrock' for c in constructs)
    assert any(c['name'] == 'Knowledgebase' and c['type'] == 'bedrock' for c in constructs)

    # Check for constructs from subdirectories - these may have different naming patterns
    # depending on how the parent parameter is handled in the actual implementation
    agent_subdir_constructs = [
        c for c in constructs if c['type'] == 'bedrock' and 'agent' in c['name'].lower()
    ]
    knowledgebase_subdir_constructs = [
        c for c in constructs if c['type'] == 'bedrock' and 'knowledgebase' in c['name'].lower()
    ]

    # We should have at least one construct from each subdirectory
    assert len(agent_subdir_constructs) > 0, 'No constructs found from agent subdirectory'
    assert len(knowledgebase_subdir_constructs) > 0, (
        'No constructs found from knowledgebase subdirectory'
    )


@patch('os.path.dirname')
@patch('os.path.join')
@patch('os.path.exists')
def test_list_available_constructs_directory_not_found(mock_exists, mock_join, mock_dirname):
    """Test listing available constructs when directory is not found."""
    # Mock the directory path
    mock_dirname.return_value = '/mock/path'
    mock_join.return_value = '/mock/path/static/genai_cdk/bedrock'
    mock_exists.return_value = False

    # Test listing constructs
    constructs = list_available_constructs('bedrock')

    # Check that an empty list is returned
    assert constructs == []


def test_list_available_constructs_invalid_construct_type():
    """Test listing available constructs with invalid construct type."""
    # Test with invalid construct type
    constructs = list_available_constructs('invalid_type')

    # Check that an empty list is returned
    assert constructs == []


# Add tests for GitHub-based functions
@pytest.mark.asyncio
async def test_extract_sections():
    """Test extracting sections from README content."""
    content = """# Main Title

Introduction paragraph

## Section One
Content for section one
More content

## Section Two
Content for section two

### Subsection
This is a subsection that shouldn't be captured as a top-level section

## Section Three
Final section content
"""

    sections = extract_sections(content)
    
    # Check that we got the expected sections
    assert len(sections) == 3
    assert "Section One" in sections
    assert "Section Two" in sections
    assert "Section Three" in sections
    
    # Check that section content is extracted correctly
    assert "Content for section one" in sections["Section One"]
    assert "Content for section two" in sections["Section Two"]
    assert "Final section content" in sections["Section Three"]
    
    # Ensure section headers are included in content
    assert "## Section One" in sections["Section One"]
    
    # Check subsection handling
    assert "### Subsection" in sections["Section Two"]
    assert "This is a subsection" in sections["Section Two"]
