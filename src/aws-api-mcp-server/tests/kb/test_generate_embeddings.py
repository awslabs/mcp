import argparse
import re
import sys
import tempfile
from awscli.clidriver import __version__ as awscli_version
from awslabs.aws_api_mcp_server.core.aws.services import driver
from awslabs.aws_api_mcp_server.core.kb.dense_retriever import (
    DEFAULT_CACHE_DIR,
    KNOWLEDGE_BASE_SUFFIX,
)
from awslabs.aws_api_mcp_server.scripts.generate_embeddings import (
    _generate_operation_document,
    _get_aws_api_documents,
    generate_embeddings,
    main,
)
from pathlib import Path
from unittest.mock import MagicMock, patch


@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.driver._get_command_table')
@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.logger')
def test_generate_embeddings_handles_exceptions(mock_logger, mock_get_command_table):
    """Test that exceptions during document retrieval are handled gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        model_name = 'BAAI/bge-base-en-v1.5'
        cache_file = cache_dir / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'

        # Create a dummy cache file
        cache_file.touch()

        # Mock service command instance with spec to pass isinstance check
        from awscli.clidriver import ServiceCommand

        mock_service_command = MagicMock(spec=ServiceCommand)
        mock_service_command._get_command_table.side_effect = Exception('Test exception')

        mock_get_command_table.return_value = {'failing-service': mock_service_command}

        generate_embeddings(model_name, cache_dir, overwrite=True)

        # Should not raise exception and log 0 documents retrieved
        mock_logger.info.assert_any_call('Collected 0 documents.')


def test_generate_embeddings_cache_exists_no_overwrite():
    """Test generate_embeddings when cache exists and overwrite is False."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        model_name = 'BAAI/bge-base-en-v1.5'
        cache_file = cache_dir / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'

        # Create a dummy cache file
        cache_file.touch()

        with patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.logger') as mock_logger:
            generate_embeddings(model_name, cache_dir, overwrite=False)

            # Should log that embeddings already exist
            mock_logger.info.assert_called_with(
                f'Embeddings are already generated and cached: {cache_file}. Use --overwrite to regenerate.'
            )


@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings._get_aws_api_documents')
@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.DenseRetriever')
@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.logger')
def test_generate_embeddings_overwrite_existing(
    mock_logger, mock_dense_retriever, mock_get_aws_api_documents
):
    """Test generate_embeddings with overwrite=True."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        model_name = 'BAAI/bge-base-en-v1.5'
        cache_file = cache_dir / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'

        # Create a dummy cache file
        cache_file.touch()

        # Mock documents
        mock_documents = [
            {'command': 'aws ec2 describe-instances', 'description': 'Test', 'parameters': {}}
        ]
        mock_get_aws_api_documents.return_value = mock_documents

        # Mock retriever
        mock_retriever_instance = MagicMock()
        mock_dense_retriever.return_value = mock_retriever_instance

        generate_embeddings(model_name, cache_dir, overwrite=True)

        # Should log overwrite message
        mock_logger.info.assert_any_call(f'Overwriting existing cached embeddings: {cache_file}')

        # Should create retriever and generate index
        mock_dense_retriever.assert_called_once_with(model_name=model_name, cache_dir=cache_dir)
        mock_retriever_instance.generate_index.assert_called_once_with(mock_documents)
        mock_retriever_instance.save_to_cache.assert_called_once()


@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.driver._get_command_table')
@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.logger')
@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.DenseRetriever')
def test_generate_embeddings_with_document_details(
    mock_dense_retriever, mock_logger, mock_get_command_table
):
    """Test generate_embeddings() processes document correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        model_name = 'BAAI/bge-base-en-v1.5'
        cache_file = cache_dir / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'

        # Create a dummy cache file
        cache_file.touch()

        # Mock input shape
        mock_member = MagicMock()
        mock_member.type_name = 'string'
        mock_member.documentation = '<p>Mock inner documentation</p>'

        mock_input_shape = MagicMock()
        mock_input_shape.members = {'MockParam': mock_member}

        # Mock operation
        mock_operation = MagicMock()
        mock_operation._operation_model.documentation = (
            '<p>Deletes the specified alternate contact.</p>'
        )
        mock_operation._operation_model.input_shape = mock_input_shape

        # Mock service command instance with spec to pass isinstance check
        from awscli.clidriver import ServiceCommand

        mock_service_command = MagicMock(spec=ServiceCommand)
        mock_service_command._get_command_table.return_value = {'mock-operation': mock_operation}

        mock_get_command_table.return_value = {'mock-service': mock_service_command}

        # Mock DenseRetriever
        mock_retriever_instance = MagicMock()
        mock_dense_retriever.return_value = mock_retriever_instance

        generate_embeddings(model_name, cache_dir, overwrite=True)

        mock_logger.info('Collected 1 documents.')

        mock_dense_retriever.assert_called_once_with(model_name=model_name, cache_dir=cache_dir)

        mock_retriever_instance.generate_index.assert_called_once()
        mock_retriever_instance.save_to_cache.assert_called_once()


def test_argument_parser_defaults():
    """Test that argument parser has correct defaults."""
    parser = argparse.ArgumentParser(description='Argument parser for model loading')
    parser.add_argument(
        '--model-name',
        type=str,
        default='BAAI/bge-base-en-v1.5',
        help='Name or path of the model to load',
    )
    parser.add_argument(
        '--cache-dir',
        type=str,
        default=str(Path(__file__).resolve().parent.parent / 'data' / 'embeddings'),
        help='Directory to use for caching models',
    )
    parser.add_argument(
        '--overwrite', action='store_true', help='Overwrite existing cached files (default: False)'
    )

    args = parser.parse_args([])

    assert args.model_name == 'BAAI/bge-base-en-v1.5'
    assert args.overwrite is False
    assert 'embeddings' in args.cache_dir


def test_generate_operation_document_happy_path():
    """A happy path test for _generate_operation_document."""
    # Get actual lambda service and list-aliases operation
    lambda_command = driver._get_command_table()['lambda']
    lambda_operations = lambda_command._get_command_table()
    list_aliases_operation = lambda_operations['list-aliases']

    result = _generate_operation_document('lambda', 'list-aliases', list_aliases_operation)

    assert result is not None
    assert result['command'] == 'aws lambda list-aliases'
    assert re.match(r'Returns a list of.+aliases.+for a Lambda function', result['description'])
    assert 'The name or ARN of the Lambda function.' in result['parameters']['function-name']
    assert (
        'Specify a function version to only list aliases that invoke that version.'
        in result['parameters']['function-version']
    )
    assert (
        "The total number of items to return in the command's output."
        in result['parameters']['max-items']
    )
    assert all(desc.strip() for desc in result['parameters'].values())


def test_generate_operation_document_for_custom_service():
    """Test that _generate_operation_document handles custom services."""
    s3_command = driver._get_command_table()['s3']
    s3_operations = s3_command.subcommand_table
    sync_operation = s3_operations['sync']

    result = _generate_operation_document('s3', 'sync', sync_operation)

    assert result is not None
    assert result['command'] == 'aws s3 sync'
    assert 'sync' in result['description'].lower()
    assert len(result['parameters']) > 0
    assert all(desc.strip() for desc in result['parameters'].values())


def test_generate_operation_document_for_custom_operation():
    """Test that _generate_operation_document handles custom operations."""
    cf_command = driver._get_command_table()['cloudformation']
    cf_operations = cf_command._get_command_table()
    package_operation = cf_operations['deploy']

    result = _generate_operation_document('cloudformation', 'deploy', package_operation)

    assert result is not None
    assert result['command'] == 'aws cloudformation deploy'
    assert 'deploys the specified aws cloudformation template' in result['description'].lower()
    assert len(result['parameters']) > 0
    assert all(desc.strip() for desc in result['parameters'].values())

    assert 'disable-rollback' in result['parameters']
    assert 'no-disable-rollback' not in result['parameters']
    assert 'fail-on-empty-changeset' in result['parameters']
    assert 'no-fail-on-empty-changeset' not in result['parameters']


def test_generate_operation_document_for_custom_subcommand():
    """Test that _generate_operation_document handles custom subcommands."""
    lambda_command = driver._get_command_table()['lambda']
    lambda_operations = lambda_command._get_command_table()
    wait_operation = lambda_operations['wait']

    result = _generate_operation_document('lambda', 'wait', wait_operation)

    assert result is not None
    assert result['command'] == 'aws lambda wait'
    assert 'wait' in result['description'].lower()
    assert len(result['parameters']) == 0


def test_generate_operation_document_for_custom_argument():
    """Test that _generate_operation_document handles custom arguments."""
    lambda_command = driver._get_command_table()['lambda']
    lambda_operations = lambda_command._get_command_table()
    create_function_operation = lambda_operations['create-function']

    result = _generate_operation_document('lambda', 'create-function', create_function_operation)

    assert result is not None
    assert result['command'] == 'aws lambda create-function'
    assert 'zip-file' in result['parameters']
    assert all(desc.strip() for desc in result['parameters'].values())


def test_get_aws_api_documents():
    """Test _get_aws_api_documents."""
    # Get original command table and filter to only s3, cloudformation, lambda, configure, history
    original_table = driver._get_command_table()
    filtered_table = {
        k: v
        for k, v in original_table.items()
        if k in ['s3', 'cloudformation', 'lambda', 'configure', 'history']
    }

    with patch.object(driver, '_get_command_table', return_value=filtered_table):
        documents = _get_aws_api_documents()

    # Group documents by service name
    service_counts = {}
    for doc in documents:
        service = doc['command'].split()[1]
        service_counts[service] = service_counts.get(service, 0) + 1

    # configure and history should not be included
    assert set(service_counts.keys()) == {'s3', 'cloudformation', 'lambda'}
    assert service_counts['cloudformation'] == len(
        original_table['cloudformation']._get_command_table()
    )
    assert service_counts['lambda'] == len(original_table['lambda']._get_command_table())
    assert service_counts['s3'] == len(original_table['s3'].subcommand_table)


def test_get_aws_api_documents_ignores_denied_custom_operations():
    """Test _get_aws_api_documents."""
    # Get original command table and filter to only emr
    original_table = driver._get_command_table()
    filtered_table = {k: v for k, v in original_table.items() if k in ['emr']}

    with patch.object(driver, '_get_command_table', return_value=filtered_table):
        documents = _get_aws_api_documents()

    for doc in documents:
        assert 'aws emr ssh' not in doc['command']


@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.driver._get_command_table')
def test_get_aws_api_documents_unknown_command_type(mock_get_command_table):
    """Test handling of unknown command types."""
    # Mock unknown command type
    mock_unknown_command = MagicMock()

    # Mock driver command table
    mock_get_command_table.return_value = {'test-service': mock_unknown_command}

    with patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.logger') as mock_logger:
        documents = _get_aws_api_documents()

        assert len(documents) == 0
        mock_logger.warning.assert_called_once()


@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.generate_embeddings')
def test_main_default_args(mock_generate):
    """Test main function with default arguments."""
    with patch.object(sys, 'argv', ['generate_embeddings.py']):
        main()
        mock_generate.assert_called_once_with(
            'BAAI/bge-base-en-v1.5', Path(DEFAULT_CACHE_DIR), False
        )


@patch('awslabs.aws_api_mcp_server.scripts.generate_embeddings.generate_embeddings')
def test_main_custom_args(mock_generate):
    """Test main function with custom arguments."""
    with patch.object(
        sys,
        'argv',
        [
            'generate_embeddings.py',
            '--model-name',
            'custom-model',
            '--cache-dir',
            '/custom/cache',
            '--overwrite',
        ],
    ):
        main()
        mock_generate.assert_called_once_with('custom-model', Path('/custom/cache'), True)
