import tempfile
from awslabs.aws_mcp_server.core.kb.operations_index import KeyWordSearch, calculate_similarity
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_calculate_similarity_exact_match():
    """Test similarity calculation for exact matches."""
    query = 'launch ec2 instance'
    description = 'create ec2 instance'
    similarity = calculate_similarity(query, description)
    assert 0.5 < similarity <= 1.0  # Should be high similarity


def test_calculate_similarity_partial_match():
    """Test similarity calculation for partial matches."""
    query = 'create ec2 instance'
    description = 'create an ec2 instance with security groups'
    similarity = calculate_similarity(query, description)
    assert 0.5 < similarity <= 1.0  # Should be high similarity


def test_calculate_similarity_no_match():
    """Test similarity calculation for no matches."""
    query = 'create ec2 instance'
    description = 'delete s3 bucket'
    similarity = calculate_similarity(query, description)
    assert similarity < 0.3  # Should be low similarity


@patch('awslabs.aws_mcp_server.core.kb.operations_index._get_all_aws_operations')
def test_keyword_search_initialization(mock_get_operations):
    """Test KeyWordSearch initialization."""
    mock_get_operations.return_value = [
        {
            'service': 'ec2',
            'operation': 'describe-instances',
            'parameters': {},
            'full_description': 'Describes EC2 instances',
            'clean_description': 'Describes EC2 instances',
        }
    ]

    search = KeyWordSearch()
    assert search.aws_operations_index is not None
    assert len(search.aws_operations_index) == 1


@patch('awslabs.aws_mcp_server.core.kb.operations_index.driver._get_command_table')
def test_get_all_aws_operations_handles_exceptions(mock_get_command_table):
    """Test that exceptions during operation retrieval are handled gracefully."""
    # Mock service command instance with spec to pass isinstance check
    from awscli.clidriver import ServiceCommand

    mock_service_command = MagicMock(spec=ServiceCommand)
    mock_service_command._get_command_table.side_effect = Exception('Test exception')

    mock_get_command_table.return_value = {'failing-service': mock_service_command}

    search = KeyWordSearch()
    # Should not raise exception
    assert len(search.aws_operations_index) == 0


@patch('awslabs.aws_mcp_server.core.kb.operations_index.driver._get_command_table')
def test_get_all_aws_operations(mock_get_command_table):
    """Test get_all_aws_operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        model_name = 'BAAI/bge-base-en-v1.5'
        cache_file = cache_dir / f'{model_name.replace("/", "-")}.npz'

        # Create a dummy cache file
        cache_file.touch()

        # Mock input shape
        mock_member = MagicMock()
        mock_member.type_name = 'string'
        mock_member.documentation = 'Mock parameter documentation'

        mock_input_shape = MagicMock()
        mock_input_shape.members = {'MockParam': mock_member}

        # Mock operation
        mock_operation = MagicMock()
        mock_operation._operation_model.documentation = 'Mock operation documentation'
        mock_operation._operation_model.input_shape = mock_input_shape

        # Mock service command instance with spec to pass isinstance check
        from awscli.clidriver import ServiceCommand

        mock_service_command = MagicMock(spec=ServiceCommand)
        mock_service_command._get_command_table.return_value = {'mock-operation': mock_operation}

        mock_get_command_table.return_value = {'mock-service': mock_service_command}

        search = KeyWordSearch()
        assert len(search.aws_operations_index) == 1
        op = search.aws_operations_index[0]

        assert op['service'] == 'mock-service'
        assert 'mock-param (string)' in op['parameters']


@patch('awslabs.aws_mcp_server.core.kb.operations_index._get_all_aws_operations')
def test_get_suggestions_basic(mock_get_operations):
    """Test basic suggestion retrieval."""
    mock_get_operations.return_value = [
        {
            'service': 'ec2',
            'operation': 'describe-instances',
            'parameters': {'instance-ids': 'List of instance IDs'},
            'full_description': 'Describes EC2 instances in your account',
            'clean_description': 'Describes EC2 instances in your account',
        },
        {
            'service': 's3',
            'operation': 'list-buckets',
            'parameters': {},
            'full_description': 'Lists S3 buckets in your account',
            'clean_description': 'Lists S3 buckets in your account',
        },
    ]

    search = KeyWordSearch()
    results = search.get_suggestions('describe ec2 instances')

    assert 'suggestions' in results
    suggestions = results['suggestions']
    assert len(suggestions) > 0

    # Should find EC2 describe-instances as top result
    top_suggestion = suggestions[0]
    assert 'aws ec2 describe-instances' == top_suggestion['command']


@patch('awslabs.aws_mcp_server.core.kb.operations_index._get_all_aws_operations')
def test_get_suggestions_no_matches(mock_get_operations):
    """Test suggestion retrieval with no matches."""
    mock_get_operations.return_value = [
        {
            'service': 'ec2',
            'operation': 'describe-instances',
            'parameters': {},
            'full_description': 'Describes EC2 instances',
            'clean_description': 'Describes EC2 instances',
        }
    ]

    search = KeyWordSearch()
    results = search.get_suggestions('completely unrelated query xyz')

    assert 'suggestions' in results
    # Should return empty list or very low similarity matches
    suggestions = results['suggestions']
    if suggestions:
        assert all(s['similarity'] <= 0.2 for s in suggestions)


@patch('awslabs.aws_mcp_server.core.kb.operations_index._get_all_aws_operations')
def test_get_suggestions_returns_10_at_most(mock_get_operations):
    """Test that suggestions are limited to top 10 results."""
    # Create 15 mock operations
    mock_operations = []
    for i in range(15):
        mock_operations.append(
            {
                'service': f'service{i}',
                'operation': f'operation{i}',
                'parameters': {},
                'full_description': f'test operation {i} description',
                'clean_description': f'test operation {i} description',
            }
        )

    mock_get_operations.return_value = mock_operations

    search = KeyWordSearch()
    results = search.get_suggestions('test operation')

    assert 'suggestions' in results
    suggestions = results['suggestions']
    assert len(suggestions) == 10


@patch('awslabs.aws_mcp_server.core.kb.operations_index._get_all_aws_operations')
def test_get_suggestions_description_truncation(mock_get_operations):
    """Test that long descriptions are truncated."""
    long_description = 'A' * 1500  # Longer than 1000 characters

    mock_get_operations.return_value = [
        {
            'service': 'ec2',
            'operation': 'describe-instances',
            'parameters': {},
            'full_description': f'ec2 instances {long_description}',
            'clean_description': long_description,
        }
    ]

    search = KeyWordSearch()
    results = search.get_suggestions('ec2 instances')

    suggestions = results['suggestions']
    if suggestions:
        description = suggestions[0]['description']
        assert len(description) == 1003  # 1000 + '...'
        assert description.endswith('...')


@patch('awslabs.aws_mcp_server.core.kb.operations_index._get_all_aws_operations')
def test_get_suggestions_sorted_by_similarity(mock_get_operations):
    """Test that suggestions are sorted by similarity score."""
    mock_get_operations.return_value = [
        {
            'service': 'ec2',
            'operation': 'describe-instances',
            'parameters': {},
            'full_description': 'Describes EC2 instances exactly',
            'clean_description': 'Describes EC2 instances exactly',
        },
        {
            'service': 'ec2',
            'operation': 'run-instances',
            'parameters': {},
            'full_description': 'Launches EC2 instances',
            'clean_description': 'Launches EC2 instances',
        },
        {
            'service': 's3',
            'operation': 'list-buckets',
            'parameters': {},
            'full_description': 'Lists S3 buckets',
            'clean_description': 'Lists S3 buckets',
        },
    ]

    search = KeyWordSearch()
    results = search.get_suggestions('describe ec2 instances')

    suggestions = results['suggestions']
    if len(suggestions) > 1:
        # Should be sorted by similarity (descending)
        for i in range(len(suggestions) - 1):
            assert suggestions[i]['similarity'] >= suggestions[i + 1]['similarity']
