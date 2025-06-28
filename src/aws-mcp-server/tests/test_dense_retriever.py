import pytest
from awslabs.aws_mcp_server.core.kb import knowledge_base
from awslabs.aws_mcp_server.core.kb.dense_retriever import DEFAULT_TOP_K, DenseRetriever


@pytest.mark.skip(reason='Test disabled')
def test_dense_retriever():
    """Tests if knowledge base uses DenseRetriever by default and can retrieve documents."""
    knowledge_base.setup(rag_type='DENSE_RETRIEVER')
    assert isinstance(knowledge_base.rag, DenseRetriever)

    suggestions = knowledge_base.get_suggestions('Describe my ec2 instances')
    suggested_commnads = [s['command'] for s in suggestions['suggestions']]

    assert len(suggested_commnads) == DEFAULT_TOP_K
    assert 'aws ec2 describe-instances' in suggested_commnads
