import pytest
from awscli.clidriver import __version__ as awscli_version
from awslabs.aws_mcp_server.core.kb import knowledge_base
from awslabs.aws_mcp_server.core.kb.dense_retriever import (
    DEFAULT_CACHE_DIR,
    DEFAULT_EMBEDDINGS_MODEL,
    DEFAULT_TOP_K,
    KNOWLEDGE_BASE_SUFFIX,
    DenseRetriever,
)
from pathlib import Path
from sentence_transformers import SentenceTransformer


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
    assert rag.model_name == DEFAULT_EMBEDDINGS_MODEL
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


def test_dense_retriever():
    """Tests if knowledge base uses DenseRetriever by default and can retrieve documents."""
    # Check if embeddings file exists
    cache_file = DEFAULT_CACHE_DIR / f'{DEFAULT_EMBEDDINGS_MODEL.replace("/", "-")}.npz'
    if not cache_file.exists():
        pytest.skip(f'Embeddings file not found: {cache_file}')

    knowledge_base.setup(rag_type='DENSE_RETRIEVER')
    assert isinstance(knowledge_base.rag, DenseRetriever)

    suggestions = knowledge_base.get_suggestions('Describe my ec2 instances')
    suggested_commands = [s['command'] for s in suggestions['suggestions']]

    assert len(suggested_commands) == DEFAULT_TOP_K
    assert 'aws ec2 describe-instances' in suggested_commands
