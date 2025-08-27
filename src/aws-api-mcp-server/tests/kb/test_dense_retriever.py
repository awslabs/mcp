import json
import numpy as np
import pytest
import tempfile
from awscli.clidriver import __version__ as awscli_version
from awslabs.aws_api_mcp_server.core.kb import knowledge_base
from awslabs.aws_api_mcp_server.core.kb.dense_retriever import (
    DEFAULT_CACHE_DIR,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    KNOWLEDGE_BASE_SUFFIX,
    DenseRetriever,
)
from pathlib import Path
from sentence_transformers import SentenceTransformer
from unittest.mock import MagicMock, PropertyMock, patch


def test_simple_initialization():
    """Tests if DenseRetriver is instantiated properly."""
    # Check if embeddings file exists
    cache_file = DEFAULT_CACHE_DIR / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'
    if not cache_file.exists():
        pytest.skip(f'Embeddings file not found: {cache_file}')
    rag = DenseRetriever(cache_dir=Path(DEFAULT_CACHE_DIR))

    assert rag.top_k == DEFAULT_TOP_K
    assert rag.cache_dir == Path(DEFAULT_CACHE_DIR)
    assert rag.get_cache_file_with_version() is not None
    assert rag.model_name == DEFAULT_EMBEDDING_MODEL
    assert isinstance(rag.model, SentenceTransformer)
    assert rag._model is not None
    assert rag._index is None
    assert rag._documents is None
    assert rag._embeddings is None

    try:
        rag.load_from_cache_with_version()
    except ValueError:
        assert False, 'Cached file is provided but not found.'

    assert rag._documents is not None
    assert rag._embeddings is not None


@patch.object(knowledge_base, '_load_model_in_background', MagicMock(return_value=None))
@patch.object(DenseRetriever, 'is_model_ready', PropertyMock(return_value=True))
def test_dense_retriever():
    """Tests if knowledge base uses DenseRetriever by default and can retrieve documents."""
    # Check if embeddings file exists
    cache_file = DEFAULT_CACHE_DIR / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'
    if not cache_file.exists():
        pytest.skip(f'Embeddings file not found: {cache_file}')

    knowledge_base.setup()
    assert isinstance(knowledge_base.rag, DenseRetriever)

    suggestions = knowledge_base.get_suggestions('Describe my ec2 instances')
    suggested_commands = [s['command'] for s in suggestions['suggestions']]

    assert len(suggested_commands) == DEFAULT_TOP_K, (
        f'Expected {DEFAULT_TOP_K} commands, got {len(suggested_commands)}: {suggested_commands}'
    )
    assert 'aws ec2 describe-instances' in suggested_commands


@patch.object(DenseRetriever, 'embeddings', new_callable=PropertyMock, return_value=None)
def test_index_property_without_embeddings(mock_embeddings):
    """Test index property when embeddings are not loaded."""
    rag = DenseRetriever(cache_dir=Path(DEFAULT_CACHE_DIR))

    with pytest.raises(ValueError, match='Embeddings are not loaded.'):
        _ = rag.index


def test_documents_property_without_cache():
    """Test documents property when no cache file exists."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    with pytest.raises(FileNotFoundError, match='No embeddings found for current awscli version'):
        _ = rag.documents


def test_embeddings_property_without_cache():
    """Test embeddings property when no cache file exists."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    with pytest.raises(FileNotFoundError, match='No embeddings found for current awscli version'):
        _ = rag.embeddings


def test_get_cache_file_with_version_with_cache_dir():
    """Test get_cache_file_with_version when cache_dir is set."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))
    cache_file = rag.get_cache_file_with_version()
    expected_file = Path('/tmp') / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'
    assert cache_file == expected_file


def test_load_from_cache_with_version_file_not_found():
    """Test load_from_cache_with_version when cache file doesn't exist."""
    rag = DenseRetriever(cache_dir=Path('/nonexistent'))

    with pytest.raises(FileNotFoundError, match='Versioned cache file not found:'):
        rag.load_from_cache_with_version()


@patch.object(DenseRetriever, 'embeddings', new_callable=PropertyMock, return_value=None)
def test_save_to_cache_without_embeddings(mock_embeddings):
    """Test save_to_cache when embeddings are not set."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    with pytest.raises(ValueError, match='Embeddings are not set'):
        rag.save_to_cache()


def test_save_to_cache_success():
    """Test successful save_to_cache operation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        rag = DenseRetriever(cache_dir=Path(temp_dir))

        # Mock embeddings and documents
        rag.embeddings = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        rag.documents = [{'command': 'test1'}, {'command': 'test2'}]

        # Save to cache
        rag.save_to_cache()

        # Verify cache file was created
        cache_file = rag.get_cache_file_with_version()
        assert cache_file is not None
        assert cache_file.exists()

        # Verify cache file can be loaded
        data = np.load(cache_file, allow_pickle=False)
        assert 'embeddings' in data
        assert 'documents' in data
        assert data['embeddings'].shape == (2, 3)


def test_generate_index():
    """Test generate_index method."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    documents = [
        {'command': 'aws ec2 describe-instances', 'description': 'Describe EC2 instances'},
        {'command': 'aws s3 ls', 'description': 'List S3 buckets'},
    ]

    rag.generate_index(documents)

    assert rag.documents == documents
    assert rag.embeddings is not None
    assert rag.embeddings.shape[0] == 2
    assert rag.embeddings.shape[1] > 0


@patch.object(DenseRetriever, 'documents', new_callable=PropertyMock, return_value=None)
def test_get_suggestions_without_documents(mock_documents):
    """Test get_suggestions when documents are not loaded."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    # Mock the model and index properly
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]]).astype('float32')
    rag.model = mock_model

    mock_index = MagicMock()
    mock_index.search.return_value = (
        np.array([[0.9, 0.8, 0.7]]),  # distances
        np.array([[0, 1, 2]]),  # indices
    )
    rag.index = mock_index

    with pytest.raises(ValueError, match='Documents are not loaded.'):
        rag.get_suggestions('test query')


def test_get_suggestions_success():
    """Test successful get_suggestions operation."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    # Mock documents and embeddings
    rag.documents = [
        {'command': 'aws ec2 describe-instances', 'description': 'Describe EC2 instances'},
        {'command': 'aws s3 ls', 'description': 'List S3 buckets'},
        {'command': 'aws lambda list-functions', 'description': 'List Lambda functions'},
        {'command': 'aws logs describe-log-groups', 'description': 'List log groups'},
        {'command': 'aws sts get-caller-identity', 'description': 'Show current identity'},
    ]

    # Create mock embeddings (3 documents, 384 dimensions like BAAI/bge-base-en-v1.5)
    rag.embeddings = np.random.rand(5, 384).astype('float32')

    # Mock the model encode method
    with patch.object(rag, '_model') as mock_model:
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]]).astype('float32')

        # Mock the index directly
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7, 0.6, 0.5]]),  # distances
            np.array([[0, 1, 2, 3, 4]]),  # indices
        )
        rag.index = mock_index

        # Test search
        suggestions = rag.get_suggestions('describe instances')

        assert 'suggestions' in suggestions
        assert len(suggestions['suggestions']) == DEFAULT_TOP_K
        assert all('similarity' in doc for doc in suggestions['suggestions'])
        assert all('command' in doc for doc in suggestions['suggestions'])


def test_custom_initialization():
    """Test DenseRetriever initialization with custom parameters."""
    rag = DenseRetriever(
        top_k=5,
        model_name='sentence-transformers/all-MiniLM-L6-v2',
        cache_dir=Path('/custom/cache'),
    )

    assert rag.top_k == 5
    assert rag.model_name == 'sentence-transformers/all-MiniLM-L6-v2'
    assert rag.cache_dir == Path('/custom/cache')


def test_model_property_lazy_loading():
    """Test that model is loaded lazily."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    # Model should not be loaded initially
    assert rag._model is None
    assert not rag.is_model_ready

    # Accessing model property should load it
    model = rag.model
    assert rag._model is not None
    assert isinstance(model, SentenceTransformer)
    assert rag.is_model_ready

    # Second access should return the same instance
    model2 = rag.model
    assert model2 is model


def test_index_property_lazy_loading():
    """Test that index is created lazily."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    # Mock embeddings
    rag.embeddings = np.random.rand(3, 384).astype('float32')

    # Index should not be created initially
    assert rag._index is None

    # Accessing index property should create it
    index = rag.index
    assert rag._index is not None
    assert index is rag._index

    # Second access should return the same instance
    index2 = rag.index
    assert index2 is index


def test_load_from_cache_with_version_success():
    """Test successful load_from_cache_with_version operation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        rag = DenseRetriever(cache_dir=Path(temp_dir))

        # Create mock cache file
        cache_file = rag.get_cache_file_with_version()
        assert cache_file is not None
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Create mock data
        mock_embeddings = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        mock_documents = [{'command': 'test1'}, {'command': 'test2'}]

        # Save mock data
        np.savez_compressed(
            cache_file,
            embeddings=mock_embeddings,
            documents=np.array(json.dumps(mock_documents)),
        )

        # Load from cache
        rag.load_from_cache_with_version()

        assert rag.documents == mock_documents
        np.testing.assert_array_equal(rag.embeddings, mock_embeddings)


def test_get_suggestions_with_mock_model():
    """Test get_suggestions with mocked model to avoid loading real embeddings."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    # Mock documents and embeddings
    rag.documents = [
        {'command': 'aws ec2 describe-instances', 'description': 'Describe EC2 instances'},
        {'command': 'aws s3 ls', 'description': 'List S3 buckets'},
        {'command': 'aws lambda list-functions', 'description': 'List Lambda functions'},
        {'command': 'aws logs describe-log-groups', 'description': 'List log groups'},
        {'command': 'aws sts get-caller-identity', 'description': 'Show current identity'},
    ]

    # Create mock embeddings
    rag.embeddings = np.random.rand(5, 384).astype('float32')

    # Mock the model encode method
    with patch.object(rag, '_model') as mock_model:
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]]).astype('float32')

        # Mock the index directly
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7, 0.6, 0.5]]),  # distances
            np.array([[0, 1, 2, 3, 4]]),  # indices
        )
        rag.index = mock_index

        # Test search
        suggestions = rag.get_suggestions('describe instances')

        assert 'suggestions' in suggestions
        assert len(suggestions['suggestions']) == DEFAULT_TOP_K
        assert all('similarity' in doc for doc in suggestions['suggestions'])
        assert all('command' in doc for doc in suggestions['suggestions'])


def test_get_suggestions_uses_rag_model_and_index():
    """Test that get_suggestions properly uses the RAG model and index."""
    rag = DenseRetriever(cache_dir=Path('/tmp'))

    # Setup test data
    test_query = 'list ec2 instances'
    test_documents = [
        {'command': 'aws ec2 describe-instances', 'description': 'Describe EC2 instances'},
        {'command': 'aws ec2 list-images', 'description': 'List EC2 AMIs'},
    ]
    test_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]]).astype('float32')

    # Mock the model
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.5, 0.6]]).astype('float32')
    rag.model = mock_model

    # Mock the index
    mock_index = MagicMock()
    mock_index.search.return_value = (
        np.array([[0.95, 0.85]]),  # distances
        np.array([[0, 1]]),  # indices
    )
    rag.index = mock_index

    # Set documents and embeddings
    rag.documents = test_documents
    rag.embeddings = test_embeddings

    # Call get_suggestions
    result = rag.get_suggestions(test_query)

    # Verify model.encode was called with the query
    mock_model.encode.assert_called_once_with([test_query], normalize_embeddings=True)

    # Verify index.search was called with the encoded query and top_k
    mock_index.search.assert_called_once()
    args, _ = mock_index.search.call_args
    np.testing.assert_array_equal(args[0], np.array([[0.5, 0.6]]).astype('float32'))
    assert args[1] == DEFAULT_TOP_K

    # Verify the result structure
    assert 'suggestions' in result
    assert len(result['suggestions']) == 2

    # Verify the documents were returned with similarity scores
    assert result['suggestions'][0]['command'] == 'aws ec2 describe-instances'
    assert result['suggestions'][0]['similarity'] == 0.95
    assert result['suggestions'][1]['command'] == 'aws ec2 list-images'
    assert result['suggestions'][1]['similarity'] == 0.85
