import pytest

from awslabs.valkey_mcp_server.embeddings import BedrockEmbeddings


async def acquire_bedrock_embeddings(*args, **kwargs) -> BedrockEmbeddings:
    """Assert Bedrock access is available."""
    # Create Bedrock embeddings provider - skip if no credentials
    try:
        return BedrockEmbeddings(*args, **kwargs)
    except ValueError as e:
        if 'AWS credentials not found' in str(e):
            pytest.skip('AWS credentials not configured - skipping Bedrock integration test')
        raise
