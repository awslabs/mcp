import pytest
from awslabs.aws_api_mcp_server.core.kb import KnowledgeBase
from awslabs.aws_api_mcp_server.core.kb.dense_retriever import DenseRetriever
from unittest.mock import MagicMock, PropertyMock, patch


def test_load_model_in_background_with_rag():
    """Test _load_model_in_background starts thread when rag is not None."""
    kb = KnowledgeBase()
    mock_rag = MagicMock()
    kb.rag = mock_rag

    with patch('threading.Thread') as mock_thread:
        kb._load_model_in_background()

        # Verify thread was created and started
        mock_thread.assert_called_once()
        call_args = mock_thread.call_args
        assert call_args[1]['daemon'] is True

        # Verify the thread was started
        mock_thread.return_value.start.assert_called_once()

        # Verify the target function accesses the model property
        target_func = call_args[1]['target']
        target_func()
        # The lambda function should access the model property
        assert hasattr(mock_rag, 'model')


def test_load_model_in_background_without_rag():
    """Test _load_model_in_background does nothing when rag is None."""
    kb = KnowledgeBase()
    kb.rag = None

    with patch('threading.Thread') as mock_thread:
        kb._load_model_in_background()

        # Verify no thread was created
        mock_thread.assert_not_called()


def test_get_suggestions_model_not_ready():
    """Test get_suggestions raises RuntimeError when model is not ready."""
    kb = KnowledgeBase()

    # Create a mock RAG with is_model_ready=False
    mock_rag = MagicMock(spec=DenseRetriever)
    type(mock_rag).is_model_ready = PropertyMock(return_value=False)
    kb.rag = mock_rag

    with pytest.raises(RuntimeError, match='The model is still initializing, try again later.'):
        kb.get_suggestions('test query')

    # Verify get_suggestions was not called on the RAG object
    mock_rag.get_suggestions.assert_not_called()


def test_trim_text():
    """Test trim_text method properly truncates text."""
    kb = KnowledgeBase()

    # Test with text shorter than max_length
    short_text = 'This is a short text'
    assert kb.trim_text(short_text, 30) == short_text

    # Test with text longer than max_length
    long_text = 'This is a very long text that should be truncated'
    max_length = 20
    expected = 'This is a very long ...'
    assert kb.trim_text(long_text, max_length) == expected
    assert len(kb.trim_text(long_text, max_length)) == max_length + 3  # +3 for the ellipsis


def test_get_suggestions_rag_not_initialized():
    """Test get_suggestions raises RuntimeError when RAG is not initialized."""
    kb = KnowledgeBase()
    kb.rag = None  # Ensure RAG is not initialized

    with pytest.raises(RuntimeError, match='RAG is not initialized. Call setup first.'):
        kb.get_suggestions('test query')


def test_get_suggestions_trims_text():
    """Test get_suggestions trims long descriptions and parameter values."""
    kb = KnowledgeBase()

    # Create a mock RAG with is_model_ready=True
    mock_rag = MagicMock(spec=DenseRetriever)
    type(mock_rag).is_model_ready = PropertyMock(return_value=True)

    # Create a mock response with long description and parameter values
    long_description = 'x' * 1500  # Longer than 1000 chars
    long_param_value = 'y' * 600  # Longer than 500 chars

    mock_response = {
        'suggestions': [
            {
                'command': 'aws test command',
                'description': long_description,
                'parameters': {
                    'param1': long_param_value,
                    'param2': 'short value',
                    'param3': 123,  # Non-string value
                },
                'similarity': 0.95,
            }
        ]
    }

    mock_rag.get_suggestions.return_value = mock_response
    kb.rag = mock_rag

    # Call get_suggestions
    result = kb.get_suggestions('test query')

    # Verify the description was trimmed
    assert len(result['suggestions'][0]['description']) == 1003  # 1000 + 3 for ellipsis
    assert result['suggestions'][0]['description'].endswith('...')

    # Verify the parameter values were trimmed
    assert len(result['suggestions'][0]['parameters']['param1']) == 503  # 500 + 3 for ellipsis
    assert result['suggestions'][0]['parameters']['param1'].endswith('...')

    # Verify short values were not trimmed
    assert result['suggestions'][0]['parameters']['param2'] == 'short value'

    # Verify non-string values were not modified
    assert result['suggestions'][0]['parameters']['param3'] == 123
